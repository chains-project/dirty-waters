import requests
import copy
import os
import sqlite3
import time
from pathlib import Path
from tool.tool_config import get_cache_manager, make_github_request, clone_repo, get_last_page_info
import git
import logging

cache_manager = get_cache_manager()


def get_repo_author_commits(api_url):
    # Since we can't return the commits in ascending date order, we'll just return the latest commit
    # This response also holds the number of pages, so the last page will have the first commit
    search_url = f"{api_url}&per_page=1"
    last_page = get_last_page_info(search_url, max_retries=2, retry_delay=2, sleep_between_requests=2)
    if not last_page:
        return None

    last_page_url = f"{search_url}&page={last_page}"
    return make_github_request(last_page_url, max_retries=2, retry_delay=2, sleep_between_requests=2)


def get_user_first_commit_info(data):
    """
    Get the first commit information for each author in the given data.

    Args:
        data (dict): A dictionary containing package information with authors.

    Returns:
        dict: A dictionary with updated package information including first commit details.
    """
    cache_manager._setup_requests_cache("get_user_commit_info")
    logging.info("Getting user commit information")

    packages_data = copy.deepcopy(data)
    for package, info in packages_data.items():
        repo_name = info["repo_name"]
        authors = info.get("authors")
        if authors:
            for author in authors:
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
                    api_url = f"https://api.github.com/repos/{repo_name}/commits?author={author_login}"
                    data = cache_manager.user_commit_cache.get_user_commit(api_url)
                    if data:
                        # Retrieved data from cache
                        (
                            earliest_commit_sha,
                            author_login_in_commit,
                            author_id_in_commit,
                        ) = data
                        first_time_commit = earliest_commit_sha == commit_sha

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
                        # Data not found in cache, need to make API request
                        result = get_repo_author_commits(api_url)
                        if result:
                            earliest_commit = result[0]
                            earliest_commit_sha = earliest_commit["sha"]
                            author_login_in_commit = earliest_commit["author"]["login"]
                            author_id_in_commit = earliest_commit["author"]["id"]
                            first_time_commit = earliest_commit_sha == commit_sha
                            cache_manager.user_commit_cache.cache_user_commit(
                                api_url,
                                earliest_commit_sha,
                                repo_name,
                                package,
                                author_login,
                                commit_sha,
                                author_login_in_commit,
                                author_id_in_commit,
                            )
                            commit_result.update(
                                {
                                    "api_url": api_url,
                                    "earliest_commit_sha": earliest_commit_sha,
                                    "author_login_in_1st_commit": author_login_in_commit,
                                    "author_id_in_1st_commit": author_id_in_commit,
                                    "is_first_commit": first_time_commit,
                                    "commit_notice": "Data retrieved from API",
                                }
                            )
                        else:
                            commit_result["commit_notice"] = f"Failed to retrieve data from API({api_url})"
                author["commit_result"] = commit_result
        else:
            info["commit_result"] = None

    return packages_data
