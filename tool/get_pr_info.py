import requests
import sqlite3
import os
import json
import time
import copy
import logging


GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
# if not GITHUB_TOKEN:
#     raise ValueError("GitHub API token is not set in the environment variables.")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v4+json",
}

url = "https://api.github.com/graphql"


conn = sqlite3.connect("database/github_pr_data.db")
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS pr_info_sample
             (package TEXT, commit_sha TEXT, commit_node_id TEXT, pr_data TEXT)"""
)

conn.commit()


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

    body = json.dumps({"query": query, "variables": variables})

    response = requests.post(url, data=body, headers=headers)

    if response.status_code != 200:
        # retry 10 sec later and try 5 times
        for i in range(5):
            print(f"Retrying in 10 seconds...")
            time.sleep(10)
            response = requests.post(url, data=body, headers=headers)
            if response.status_code == 200:
                break
        else:
            raise Exception(response.status_code, response.text)

    pr_info = response.json()

    return pr_info


def get_pr_info(data):
    logging.info("Getting PR info for commits...")

    pr_infos = []

    commits_data = copy.deepcopy(data)

    for package, info in commits_data.items():
        repo_name = info.get("repo_name")
        print(f"Checking PR info in {package}'s repository: ", repo_name)
        authors = info.get("authors", [])

        for author in authors:
            commit_sha = author.get("sha")
            commit_node_id = author.get("node_id")
            commit_url = author.get("commit_url")

            c.execute(
                "SELECT pr_data FROM pr_info_sample WHERE commit_node_id=?",
                (commit_node_id,),
            )
            result = c.fetchone()

            if result:
                pr_info = json.loads(result[0])
            else:
                if commit_node_id:
                    pr_info = fetch_pull_requests(commit_node_id)

                    c.execute(
                        "INSERT INTO pr_info_sample (package, commit_sha, commit_node_id, pr_data) VALUES (?, ?, ?, ?)",
                        (package, commit_sha, commit_node_id, json.dumps(pr_info)),
                    )
                    conn.commit()

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
