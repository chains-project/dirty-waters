import requests
import copy
import os
import sqlite3
import time
from pathlib import Path
from tool_config import setup_cache

script_dir = Path(__file__).parent.absolute()
database_file = script_dir / "database" / "github_commit.db"
# print("Database file: ", database_file)


conn = sqlite3.connect(database_file)
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS commit_data (
             api_url TEXT PRIMARY KEY,
             earliest_commit_sha TEXT,
             repo_name TEXT,
             package TEXT,
             author_login TEXT,
             author_commit_sha TEXT,
             author_login_in_1st_commit TEXT,
             author_id_in_1st_commit TEXT)"""
)

conn.commit()


# logging.info("Cache [github_cache_cache] setup complete")


github_token = os.getenv("GITHUB_API_TOKEN")
# if not github_token:
#     raise ValueError("GitHub API token is not set in the environment variables.")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}


def get_user_first_commit_info(data):
    """
    Get the first commit information for each author in the given data.

    Args:
        data (dict): A dictionary containing package information with authors.

    Returns:
        dict: A dictionary with updated package information including first commit details.
    """
    setup_cache("github_commits_info")

    failed_api_urls = set()

    earliest_commit_sha = None
    author_login_in_commit = None
    author_id_in_commit = None
    first_time_commit = None

    packages_data = copy.deepcopy(data)

    for package, info in packages_data.items():
        print(f"Processing {package}")
        repo_name = info["repo_name"]

        if info.get("authors"):
            for author in info.get("authors"):
                author_login = author.get("login", "No_author_login")
                commit_sha = author.get("sha", "No_commit_sha")
                author_type = author.get("a_type", "No_author_type")

                commit_result = {
                    "api_url": None,
                    "earliest_commit_sha": None,
                    "author_login_in_1st_commit": None,
                    "author_id_in_1st_commit": None,
                    "is_first_commit": None,
                    "commit_notice": None,
                }

                if author_login is None:
                    commit_result["commit_notice"] = "Author login is None"

                if "[bot]" in author_login or author_type == "Bot":
                    commit_result["earliest_commit_sha"] = "It might be a bot"
                    commit_result["commit_notice"] = "Bot author detected"

                else:
                    api_url = f"https://api.github.com/search/commits?q=repo:{repo_name}+author:{author_login}+sort:author-date-asc"

                    c.execute(
                        "SELECT earliest_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit FROM commit_data WHERE api_url = ?",
                        (api_url,),
                    )
                    data = c.fetchone()

                    if data:
                        (
                            earliest_commit_sha,
                            author_login_in_commit,
                            author_id_in_commit,
                        ) = data
                        first_time_commit = True if earliest_commit_sha == commit_sha else False

                        commit_result.update(
                            {
                                "api_url": api_url,
                                "earliest_commit_sha": earliest_commit_sha,
                                "author_login_in_1st_commit": author_login_in_commit,
                                "author_id_in_1st_commit": author_id_in_commit,
                                "is_first_commit": first_time_commit,
                                "commit_notice": "Data retrieved from cache",
                            }
                        )

                    else:
                        max_retries = 2
                        base_wait_time = 2
                        retries = 0
                        success = False

                        while retries < max_retries and not success and api_url not in failed_api_urls:
                            response = requests.get(api_url, headers=headers)
                            time.sleep(2)

                            if response.status_code == 200:
                                success = True
                                commits_data = response.json()
                                earliest_commit_sha = (
                                    commits_data["items"][0]["sha"] if commits_data["items"] else None
                                )

                                author_login_in_commit = (
                                    commits_data["items"][0]["author"]["login"] if commits_data["items"] else None
                                )
                                # author_type = commits_data['items'][0]['author']['__typename'] if commits_data['items'] else None

                                author_id_in_commit = (
                                    commits_data["items"][0]["author"]["id"] if commits_data["items"] else None
                                )
                                # api_url_cache[api_url] = earliest_commit_sha

                                first_time_commit = True if earliest_commit_sha == commit_sha else False

                                c.execute(
                                    "INSERT INTO commit_data (api_url, earliest_commit_sha, repo_name, package, author_login, author_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (
                                        api_url,
                                        earliest_commit_sha,
                                        repo_name,
                                        package,
                                        author_login,
                                        commit_sha,
                                        author_login_in_commit,
                                        author_id_in_commit,
                                    ),
                                )
                                conn.commit()

                                commit_result.update(
                                    {
                                        "api_url": api_url,  # "https://api.github.com/search/commits?q=repo:{repo_name}+author:{author_login}+sort:author-date-asc
                                        "earliest_commit_sha": earliest_commit_sha,
                                        "author_login_in_1st_commit": author_login_in_commit,
                                        "author_id_in_1st_commit": author_id_in_commit,
                                        "is_first_commit": first_time_commit,
                                        "commit_notice": "Data retrieved from API",
                                    }
                                )

                            else:
                                print(f"Error: {response.status_code}")
                                remaining = response.headers.get("X-RateLimit-Remaining")
                                reset_time = response.headers.get("X-RateLimit-Reset")
                                wait_time = max(int(reset_time) - int(time.time()), 0)
                                print(f"Rate limit remaining: {remaining}")

                                if remaining == "0":
                                    time.sleep(wait_time)

                                else:
                                    time.sleep(base_wait_time)

                                retries += 1
                                print(f"Retrying...{retries}/{max_retries} for {api_url}")

                        if not success:
                            commit_result["commit_notice"] = f"Failed to retrieve data from API({api_url})"
                            failed_api_urls.add(api_url)

                author["commit_result"] = commit_result

        else:
            info["commit_result"] = None

    conn.close()

    return packages_data
