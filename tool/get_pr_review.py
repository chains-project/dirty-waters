import requests
import sqlite3
import os
from pathlib import Path
import json
import copy
import logging


GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")


headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v4+json",
}

url = "https://api.github.com/graphql"

script_dir = Path(__file__).parent.absolute()
database_file = script_dir / "database" / "github_prr_data_new.db"
# print(database_file)

conn = sqlite3.connect(database_file)
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS new_pr_reviewinfo_6
             (package TEXT, repo TEXT, author TEXT, first_prr_data TEXT, search_string TEXT)"""
)

conn.commit()


def get_first_pr_info(search_string):
    query = """
    query($query: String!, $type: SearchType!, $last: Int!)
    {search(query: $query, type: $type, last: $last)
        {
        nodes {
        ... on PullRequest {
            mergedAt
            merged
            mergedBy {
            login
            }
            authorAssociation
            reviews(first:1, states:APPROVED){
            edges{
                node{
                id
                author{
                    login
                    __typename
                    url
                }
                authorAssociation
                createdAt
                publishedAt
                submittedAt
                state
                repository{
                owner{
                  login
                }
                name
                }
            }
            }
            }
        }
        }
    }
    }
    

    """

    variables = {"query": f"{search_string}", "last": 1, "type": "ISSUE"}

    body = json.dumps({"query": query, "variables": variables})

    response = requests.post(url, data=body, headers=headers)

    if response.status_code != 200:
        raise Exception(response.status_code, response.text)

    first_prr_info = response.json()

    return first_prr_info


def get_pr_review_info(data):
    logging.info("Getting PR review info...")
    print("Processing PR info...")

    pr_data = copy.deepcopy(data)

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
                        # review_author_type = reviewer.get("review_author_type")
                        review_id = reviewer.get("review_id")
                        search_string = (
                            f"repo:{repo_name} is:pr reviewed-by:{review_author_login} sort:author-date-asc"
                        )

                        c.execute(
                            "SELECT first_prr_data FROM new_pr_reviewinfo_6 WHERE author=? AND repo=? and search_string=?",
                            (review_author_login, repo_name, search_string),
                        )
                        result = c.fetchone()

                        if result:
                            first_pr_info = json.loads(result[0])
                            print(f"get from db:{review_author_login}")
                        else:
                            if review_author_login:
                                first_pr_info = get_first_pr_info(search_string)

                                c.execute(
                                    "INSERT INTO new_pr_reviewinfo_6 (package, repo, author, first_prr_data, search_string) VALUES (?, ?, ?, ?, ?)",
                                    (
                                        package,
                                        repo_name,
                                        review_author_login,
                                        json.dumps(first_pr_info),
                                        search_string,
                                    ),
                                )
                                conn.commit()

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
            print(f"No authors for package:{package}")
            info["prr_data"] = None

    print("PR review info processed.")

    return pr_data
