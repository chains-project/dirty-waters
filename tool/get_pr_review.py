import requests
import sqlite3
import os
from pathlib import Path
import json
import copy
import logging
from tool.tool_config import get_cache_manager, make_github_request

cache_manager = get_cache_manager()

GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v4+json",
}

url = "https://api.github.com/graphql"


def get_multiple_pr_info(repo_name, review_author_logins):
    # Build dynamic query with aliases
    query_fragments = []
    variables = {}

    for i, login in enumerate(review_author_logins):
        alias = f"search_{i}"
        query_fragments.append(
            f"""
        {alias}: search(query: $query_{i}, type: ISSUE, last: 1) {{
            nodes {{
                ... on PullRequest {{
                    mergedAt
                    merged
                    mergedBy {{
                        login
                    }}
                    authorAssociation
                    reviews(first:1, states:APPROVED) {{
                        edges {{
                            node {{
                                id
                                author {{
                                    login
                                    __typename
                                    url
                                }}
                                authorAssociation
                                createdAt
                                publishedAt
                                submittedAt
                                state
                                repository {{
                                    owner {{
                                        login
                                    }}
                                    name
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        )
        variables[f"query_{i}"] = f"repo:{repo_name} is:pr reviewed-by:{login} sort:author-date-asc"

    # Combine all query fragments
    complete_query = """
    query({}) {{
        {}
    }}
    """.format(
        ", ".join(f"$query_{i}: String!" for i in range(len(review_author_logins))), "\n".join(query_fragments)
    )

    body = {"query": complete_query, "variables": variables}
    response = make_github_request(url, method="POST", json_data=body, headers=headers)

    # Restructure response to match expected format
    if "data" in response:
        queries = []
        for i in range(len(review_author_logins)):
            search_data = response["data"].get(f"search_{i}")
            if search_data:
                queries.append(search_data)
        return {"data": {"queries": queries}}
    return response


def get_pr_review_info(data):
    logging.info("Getting PR review info...")
    pr_data = copy.deepcopy(data)

    # Collect all uncached reviewer lookups needed
    uncached_lookups = []
    for package, info in pr_data.items():
        for author in info.get("authors", []):
            for merge_info in author.get("commit_merged_info", []):
                if merge_info.get("state") != "MERGED":
                    continue

                repo_name = merge_info.get("repo")
                for reviewer in merge_info.get("reviews", []):
                    review_author_login = reviewer.get("review_author")
                    if not review_author_login:
                        continue

                    if not cache_manager.github_cache.get_pr_review(repo_name, review_author_login):
                        uncached_lookups.append((repo_name, review_author_login))

    # Batch fetch uncached reviewers by repository
    by_repo = {}
    for repo_name, login in uncached_lookups:
        by_repo.setdefault(repo_name, set()).add(login)

    for repo_name, logins in by_repo.items():
        response = get_multiple_pr_info(repo_name, list(logins))
        # Cache individual results
        for login, result in zip(logins, response.get("data", {}).get("queries", [])):
            cache_manager.github_cache.cache_pr_review(package, repo_name, login, {"data": {"search": result}})

    # Process the data using cached results
    for package, info in pr_data.items():
        authors = info.get("authors", [])
        if authors:
            for author in authors:
                merge_infos = author.get("commit_merged_info", [])
                merge_info = merge_infos[0]
                repo_name = merge_info.get("repo")
                commit_sha = merge_info.get("commit_sha")
                merge_state = merge_info.get("state")
                reviewer_info = merge_info.get("reviews", [])

                review_author_login = "no_reviewer"
                review_id = None
                first_pr_info = None

                if merge_state == "MERGED" and len(reviewer_info) >= 1:
                    for reviewer in reviewer_info:
                        review_author_login = reviewer.get("review_author")
                        review_id = reviewer.get("review_id")
                        first_pr_info = cache_manager.github_cache.get_pr_review(repo_name, review_author_login)
                        useful_info = first_pr_info.get("data", {}).get("search", {}).get("nodes", [])
                        first_review_info = useful_info[0] if useful_info else {}
                        all_useful_first_prr_info = first_review_info.get("reviews", {}).get("edges", [])

                        if len(all_useful_first_prr_info) >= 1:
                            first_review = (
                                all_useful_first_prr_info[0].get("node", {}) if all_useful_first_prr_info else {}
                            )
                            first_prr_node_id = first_review.get("id")
                            first_prr_author = first_review.get("author", {})
                            first_prr_author = first_prr_author.get("login") if first_prr_author else None
                            first_prr_state = first_review.get("state")
                            first_prr_author_association = first_review.get("authorAssociation")
                            is_first_prr = False

                            if review_id is not None:
                                if first_prr_node_id == review_id:
                                    is_first_prr = True
                            else:
                                is_first_prr = "No review info"

                            useful_pr_info = {
                                "package": package,
                                "repo": repo_name,
                                "author_from_review": review_author_login,
                                "commit_sha": commit_sha,
                                "merge_state": merge_state,
                                "review_id": review_id,
                                "first_prr_node_id": first_prr_node_id,
                                "first_prr_author": first_prr_author,
                                "first_prr_state": first_prr_state,
                                "first_prr_repo": repo_name,
                                "first_prr_review_author_association": first_prr_author_association,
                                "is_first_prr": is_first_prr,
                            }
                        else:
                            useful_pr_info = None

                        reviewer["prr_data"] = useful_pr_info

        else:
            logging.info(f"No authors for package:{package}")
            info["prr_data"] = None

    logging.info("PR review info processed.")
    return pr_data
