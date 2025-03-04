import os
import logging
from typing import List, Dict, Tuple
from tool.tool_config import get_cache_manager, make_github_request

cache_manager = get_cache_manager()

GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
BATCH_SIZE = 100  # Configurable batch size

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v4+json",
}

url = "https://api.github.com/graphql"


def fetch_and_cache_batch(commit_batch: List[Tuple[str, str, str, str]]) -> List[Dict]:
    """
    Fetch and cache PR information for a batch of commits.

    Args:
        commit_batch: List of tuples (node_id, commit_sha, package, repo_name)

    Returns:
        List of processed PR information dictionaries
    """
    if not commit_batch:
        return []

    # Build the GraphQL query for this batch
    query_parts = []
    variables = {"first": 5}  # Number of PRs to fetch per commit

    for i, (node_id, _, _, _) in enumerate(commit_batch):
        variables[f"nodeId{i}"] = node_id
        query_parts.append(
            f"""
        node{i}: node(id: $nodeId{i}) {{
            ... on Commit {{
                associatedPullRequests(first: $first) {{
                    edges {{
                        node {{
                            author {{
                                login
                                __typename
                            }}
                            authorAssociation
                            autoMergeRequest {{
                                mergeMethod
                                enabledBy {{
                                    login
                                }}
                                authorEmail
                            }}
                            checksUrl
                            createdAt
                            mergeCommit {{
                                author {{
                                    name
                                    email
                                }}
                            }}
                            id
                            merged
                            mergedAt
                            mergedBy {{
                                login
                                __typename
                            }}
                            number
                            state
                            url
                            reviews(first: $first, states: APPROVED) {{
                                edges {{
                                    node {{
                                        author {{
                                            login
                                            __typename
                                        }}
                                        id
                                        state
                                        createdAt
                                        publishedAt
                                        submittedAt
                                        updatedAt
                                    }}
                                }}
                            }}
                            repository {{
                                name
                                owner {{
                                    login
                                    id
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        )

    # Construct the full query
    query = (
        "query("
        + ", ".join([f"$nodeId{i}: ID!" for i in range(len(commit_batch))])
        + ", $first: Int) {"
        + "\n".join(query_parts)
        + "}"
    )

    # Execute the query
    body = {"query": query, "variables": variables}
    response = make_github_request(url, method="POST", json_data=body, headers=headers, max_retries=3)

    batch_results = []
    if response and "data" in response:
        # Process and cache each result immediately
        for i, (node_id, commit_sha, package, repo_name) in enumerate(commit_batch):
            node_key = f"node{i}"
            pr_info = {}
            if (
                node_key in response["data"]
                and response["data"][node_key] is not None
                and "associatedPullRequests" in response["data"][node_key]
            ):
                pr_info = {"data": {"node": response["data"][node_key]}}

            # Cache immediately after processing each item
            cache_manager.github_cache.cache_pr_info(
                {
                    "package": package,
                    "commit_sha": commit_sha,
                    "commit_node_id": node_id,
                    "pr_info": pr_info,
                }
            )

            # Add to batch results
            batch_results.append(
                {
                    "package": package,
                    "commit_sha": commit_sha,
                    "commit_node_id": node_id,
                    "pr_info": pr_info,
                    "repo_name": repo_name,
                }
            )

            logging.info(f"Processed and cached PR info for commit {commit_sha} in {package}")
    else:
        # Handle error case
        logging.error(f"Failed to fetch PR information for batch of size {len(commit_batch)}")
        logging.error(f"Response: {response}")
        # Cache empty results for failed requests to prevent repeated failures
        for node_id, commit_sha, package, repo_name in commit_batch:
            cache_manager.github_cache.cache_pr_info(
                {
                    "package": package,
                    "commit_sha": commit_sha,
                    "commit_node_id": node_id,
                    "pr_info": {},
                }
            )
            batch_results.append(
                {
                    "package": package,
                    "commit_sha": commit_sha,
                    "commit_node_id": node_id,
                    "pr_info": {},
                    "repo_name": repo_name,
                }
            )

    return batch_results


def get_pr_info(data: Dict) -> List[Dict]:
    """
    Get PR information for all commits, processing in batches and caching gradually.

    Args:
        data: Dictionary containing commit information by package

    Returns:
        List of PR information dictionaries
    """
    logging.info("Getting PR info for commits...")

    pr_infos = []
    commits_to_process = []

    # First pass: collect commits that need processing
    for package, info in data.items():
        repo_name = info.get("repo_name")
        authors = info.get("authors", [])

        for author in authors:
            commit_sha = author.get("sha")
            commit_node_id = author.get("node_id")

            if not commit_node_id:
                continue

            # Check cache first
            pr_data = cache_manager.github_cache.get_pr_info(commit_node_id)
            if pr_data:
                # Use cached data
                pr_infos.append(
                    {
                        "package": package,
                        "commit_sha": commit_sha,
                        "commit_node_id": commit_node_id,
                        "pr_info": pr_data["pr_info"],
                        "repo_name": repo_name,
                    }
                )
            else:
                # Add to list for batch processing
                commits_to_process.append((commit_node_id, commit_sha, package, repo_name))

    # Process commits in batches
    total_commits = len(commits_to_process)
    if total_commits > 0:
        logging.info(f"Processing {total_commits} commits in batches of {BATCH_SIZE}")

        for i in range(0, total_commits, BATCH_SIZE):
            batch = commits_to_process[i : i + BATCH_SIZE]
            logging.info(f"Processing batch {i//BATCH_SIZE + 1}/{(total_commits + BATCH_SIZE - 1)//BATCH_SIZE}")

            try:
                batch_results = fetch_and_cache_batch(batch)
                pr_infos.extend(batch_results)

                # Log progress
                processed = min(i + BATCH_SIZE, total_commits)
                logging.info(f"Processed {processed}/{total_commits} commits ({processed/total_commits*100:.1f}%)")

            except Exception as e:
                logging.error(f"Error processing batch: {e}")
                # Continue with next batch instead of failing completely
                continue

    return pr_infos


def get_useful_pr_info(commits_data):
    pr_infos = get_pr_info(commits_data)

    for pr_info in pr_infos:
        if pr_info:
            package = pr_info.get("package")
            commit_sha = pr_info.get("commit_sha")
            commit_node_id = pr_info.get("commit_node_id")
            repo_name = pr_info.get("repo_name")
            associated_prs = (
                pr_info.get("pr_info", {})
                .get("data", {})
                .get("node", {})
                .get("associatedPullRequests", {})
                .get("edges", [])
            )
            for author in commits_data[package].get("authors", []):
                if author.get("node_id") == commit_node_id:
                    author["commit_merged_info"] = []
                    if len(associated_prs) == 0:
                        author["commit_merged_info"].append({"merge_info": "no associated PRs"})
                    else:
                        for associated_pr in associated_prs:
                            merge_node_info = associated_pr.get("node", {})
                            author_association = merge_node_info.get("authorAssociation")
                            auto_merge_request = merge_node_info.get("autoMergeRequest", {})
                            created_at = merge_node_info.get("createdAt")
                            pr_id = merge_node_info.get("id")
                            state = merge_node_info.get("state")
                            merge_at = merge_node_info.get("mergedAt")
                            pull_url = merge_node_info.get("url")
                            reviews = merge_node_info.get("reviews", {}).get("edges", [])

                            merged_info = {
                                "repo": repo_name,
                                "commit_sha": commit_sha,
                                "commit_node_id": commit_node_id,
                                "author_association": author_association,
                                "auto_merge_request": auto_merge_request,
                                "created_at": created_at,
                                "pr_id": pr_id,
                                "state": state,
                                "merge_at": merge_at,
                                "pull_url": pull_url,
                                "reviews": [],
                            }

                            if state == "MERGED":
                                if merge_node_info.get("mergedBy"):
                                    merged_info["merge_by"] = merge_node_info.get("mergedBy", {}).get("login")
                                    merged_info["merge_by_type"] = merge_node_info.get("mergedBy", {}).get(
                                        "__typename"
                                    )
                                else:
                                    merged_info["merge_by"] = merge_node_info.get("mergedBy")

                            else:
                                merged_info["merge_by"] = None
                                merged_info["merge_by_type"] = None

                            for review in reviews:
                                review_node = review.get("node", {})
                                if review_node:
                                    if review_node.get("author", {}):
                                        review_author = review_node.get("author", {}).get("login", None)
                                        review_author_type = review_node.get("author", {}).get("__typename", None)

                                        review_info = {
                                            "review_author": review_author,
                                            "review_author_type": review_author_type,
                                            "review_state": review_node.get("state", None),
                                            "review_id": review_node.get("id", None),
                                        }

                                        merged_info["reviews"].append(review_info)

                            author["commit_merged_info"].append(merged_info)

    return commits_data
