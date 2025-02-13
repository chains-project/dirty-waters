import requests
import sqlite3
import os
import json
import time
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


def fetch_pull_requests(commit_node_id):
    query = """
    query Edges($nodeId: ID!, $first: Int) {
    node(id: $nodeId) {
        ... on Commit {
        associatedPullRequests(first: $first) {
            edges {
            node {
                author {
                login
                __typename
                }
                authorAssociation
                autoMergeRequest {
                mergeMethod
                enabledBy {
                    login
                }
                authorEmail
                }
                checksUrl
                createdAt
                mergeCommit {
                author {
                    name
                    email
                }
                }
                id
                merged
                mergedAt
                mergedBy {
                login
                __typename
                }
                number
                state
                url
                reviews(first: $first, states: APPROVED) {
                edges {
                    node {
                    author {
                        login
                        __typename
                    }
                    id
                    state
                    createdAt
                    publishedAt
                    submittedAt
                    updatedAt
                    }
                }
                }
                repository {
                name
                owner {
                    login
                    id
                }
                }
            }
            }
        }
        }
    }
    }
    """

    variables = {
        "nodeId": f"{commit_node_id}",
        "first": 5,
    }
    body = {"query": query, "variables": variables}
    return make_github_request(url, method="POST", json_data=body, headers=headers, max_retries=5)


def get_pr_info(data):
    logging.info("Getting PR info for commits...")

    pr_infos = []

    commits_data = copy.deepcopy(data)

    for package, info in commits_data.items():
        repo_name = info.get("repo_name")
        logging.info(f"Checking PR info in {package}'s repository: {repo_name}")
        authors = info.get("authors", [])

        for author in authors:
            commit_sha = author.get("sha")
            commit_node_id = author.get("node_id")
            commit_url = author.get("commit_url")

            pr_data = cache_manager.github_cache.get_pr_info(commit_node_id)
            if not pr_data:
                if commit_node_id:
                    pr_info = fetch_pull_requests(commit_node_id)
                    cache_manager.github_cache.cache_pr_info(
                        {
                            "package": package,
                            "commit_sha": commit_sha,
                            "commit_node_id": commit_node_id,
                            "pr_info": pr_info,
                        }
                    )
            else:
                pr_info = pr_data["pr_info"]

            all_info = {
                "package": package,
                "commit_sha": commit_sha,
                "commit_node_id": commit_node_id,
                "pr_info": pr_info,
                "repo_name": repo_name,
            }
            pr_infos.append(all_info)

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
