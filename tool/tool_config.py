"""
This file contains the configuration for the tool.
"""

import pathlib
import logging
import os
import requests_cache
import requests
import sqlite3
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional
import time
from git import Repo

# change this to the install command for your project
PNPM_LIST_COMMAND = [
    "pnpm",
    "list",
    "--filter",
    "ledger-live-desktop",
    "--depth",
    "Infinity",
]

github_token = os.getenv("GITHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}


class PathManager:
    """
    Manage the paths for the results.
    """

    def __init__(self, base_dir="results"):
        self.base_dir = pathlib.Path(base_dir)

    def create_folders(self, version_tag):
        """
        Create the folders for the results.
        """

        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        folder_name = f"results_{current_time}"
        result_folder_path = self.base_dir / folder_name
        result_folder_path.mkdir(parents=True, exist_ok=True)

        json_directory = result_folder_path / "sscs" / version_tag
        json_directory.mkdir(parents=True, exist_ok=True)
        diff_directory = result_folder_path / "diff"
        diff_directory.mkdir(parents=True, exist_ok=True)

        return result_folder_path, json_directory, diff_directory


class CacheManager:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all cache instances
        self.github_cache = GitHubCache(cache_dir)
        self.package_cache = PackageAnalysisCache(cache_dir)
        self.commit_comparison_cache = CommitComparisonCache(cache_dir)
        self.user_commit_cache = UserCommitCache(cache_dir)
        self.maven_cache = MavenDependencyCache(cache_dir)

    def _setup_requests_cache(self, cache_name="http_cache"):
        requests_cache.install_cache(
            cache_name=str(self.cache_dir / f"{cache_name}_cache"),
            backend="sqlite",
            expire_after=7776000,  # 90 days
            allowable_codes=(200, 301, 302, 404),
        )

    def clear_all_caches(self, older_than_days=None):
        """Clear all caches"""
        self.github_cache.clear_cache(older_than_days)
        self.package_cache.clear_cache(older_than_days)
        self.commit_comparison_cache.clear_cache(older_than_days)
        self.user_commit_cache.clear_cache(older_than_days)
        self.maven_cache.clear_cache(older_than_days)


class Cache:
    def __init__(self, cache_dir="cache", db_name="cache.db"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / db_name
        self.setup_db()

    def setup_db(self):
        """Initialize SQLite database - should be implemented by subclasses"""
        raise NotImplementedError

    def _execute_query(self, query, params=None):
        """Execute SQLite query with proper connection handling"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            if params:
                c.execute(query, params)
            else:
                c.execute(query)
            conn.commit()
            return c.fetchall()
        finally:
            conn.close()

    def clear_cache(self, older_than_days=None):
        """Clear cached data older than specified days"""
        if older_than_days:
            cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            self._execute_query("DELETE FROM cache_entries WHERE cached_at < ?", (cutoff,))
        else:
            self._execute_query("DELETE FROM cache_entries")


class GitHubCache(Cache):
    def __init__(self, cache_dir="cache/github"):
        super().__init__(cache_dir, "github_cache.db")
        self.repo_cache = {}  # In-memory LRU cache

    def setup_db(self):
        """Initialize GitHub-specific cache tables"""
        queries = [
            """CREATE TABLE IF NOT EXISTS github_urls (
                package TEXT PRIMARY KEY,
                repo_url TEXT,
                cached_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pr_info (
                package TEXT,
                commit_sha TEXT,
                commit_node_id TEXT PRIMARY KEY,
                pr_info TEXT,
                cached_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pr_reviews (
                package TEXT,
                repo_name TEXT,
                author TEXT,
                first_review_data TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (repo_name, author)
            )""",
            """CREATE TABLE IF NOT EXISTS tag_to_sha (
                repo_name TEXT,
                tag TEXT,
                sha TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (repo_name, tag)
            )""",
        ]

        for query in queries:
            self._execute_query(query)

    def cache_pr_review(self, package, repo_name, author, first_review_data):
        """Cache PR review information"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT OR REPLACE INTO pr_reviews
                (package, repo_name, author, first_review_data, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (package, repo_name, author, json.dumps(first_review_data), datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_pr_review(self, repo_name=None, author=None):
        """Get PR review information from cache"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute("SELECT first_review_data, cached_at FROM pr_reviews WHERE repo_name = ? AND author = ?", (repo_name, author))
            result = c.fetchone()
            if result:
                review_data, cached_at = result
                cached_at = datetime.fromisoformat(cached_at)

                # Return cached data if it's less than 7 days old
                if datetime.now() - cached_at < timedelta(days=7):
                    return json.loads(review_data)
            return None
        finally:
            conn.close()

    def cache_github_url(self, package, repo_url):
        """Cache GitHub URL for a package"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT OR REPLACE INTO github_urls 
                (package, repo_url, cached_at)
                VALUES (?, ?, ?)
            """,
                (package, repo_url, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_github_url(self, package):
        """Get cached GitHub URL for a package"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute("SELECT repo_url, cached_at FROM github_urls WHERE package = ?", (package,))
            result = c.fetchone()

            if result:
                repo_url, cached_at = result
                cached_at = datetime.fromisoformat(cached_at)

                # URLs don't change often, so we can cache them for longer (30 days)
                if datetime.now() - cached_at < timedelta(days=30):
                    return repo_url

            return None
        finally:
            conn.close()

    def cache_pr_info(self, pr_data: Dict):
        """Cache PR info with current timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pr_info
                (package, commit_sha, commit_node_id, pr_info, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    pr_data["package"],
                    pr_data["commit_sha"],
                    pr_data["commit_node_id"],
                    json.dumps(pr_data["pr_info"]),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_pr_info(self, commit_node_id: str) -> Optional[Dict]:
        """Get PR info from cache if available and not expired"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        with sqlite3.connect(self.db_path) as conn:
            c.execute("SELECT package, commit_sha, commit_node_id, pr_info, cached_at FROM pr_info WHERE commit_node_id = ?", (commit_node_id,))
            result = c.fetchone()

            if result:
                package, commit_sha, commit_node_id, pr_info, cached_at = result
                cached_at = datetime.fromisoformat(cached_at)
                if datetime.now() - cached_at < timedelta(hours=24):
                    return {
                        "package": package,
                        "commit_sha": commit_sha,
                        "commit_node_id": commit_node_id,
                        "pr_info": json.loads(pr_info),
                    }
        return None

    def cache_tag_to_sha(self, repo_name, tag, sha):
        """Cache tag to SHA mapping"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tag_to_sha
                (repo_name, tag, sha, cached_at)
                VALUES (?, ?, ?, ?)
            """,
                (repo_name, tag, sha, datetime.now().isoformat()),
            )
            conn.commit()

    def get_tag_to_sha(self, repo_name, tag):
        """Get SHA for a tag from cache"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT sha, cached_at FROM tag_to_sha WHERE repo_name = ? AND tag = ?", (repo_name, tag))
            result = c.fetchone()

            if result:
                sha, cached_at = result
                cached_at = datetime.fromisoformat(cached_at)
                if datetime.now() - cached_at < timedelta(days=30):
                    return sha
        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM pr_reviews WHERE cached_at < ?", (cutoff,))
                c.execute("DELETE FROM repo_info WHERE cached_at < ?", (cutoff,))
                c.execute("DELETE FROM github_urls WHERE cached_at < ?", (cutoff,))
                c.execute("DELETE FROM pr_info WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM pr_reviews")
                c.execute("DELETE FROM repo_info")
                c.execute("DELETE FROM github_urls")
                c.execute("DELETE FROM pr_info")
            conn.commit()

        finally:
            conn.close()


class PackageAnalysisCache(Cache):
    def __init__(self, cache_dir="cache/packages"):
        super().__init__(cache_dir, "package_analysis.db")

    def setup_db(self):
        """Initialize package analysis cache tables"""
        self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS package_analysis (
                package_name TEXT,
                version TEXT,
                package_manager TEXT,
                analysis_data TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (package_name, version, package_manager)
            )
        """
        )

    def cache_package_analysis(self, package_name, version, package_manager, analysis_data):
        """Cache package analysis results"""
        self._execute_query(
            """
            INSERT OR REPLACE INTO package_analysis 
            (package_name, version, package_manager, analysis_data, cached_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (package_name, version, package_manager, json.dumps(analysis_data), datetime.now().isoformat()),
        )

    def get_package_analysis(self, package_name, version, package_manager, max_age_days=30):
        """Get cached package analysis results"""
        results = self._execute_query(
            """SELECT analysis_data, cached_at 
               FROM package_analysis 
               WHERE package_name = ? AND version = ? AND package_manager = ?""",
            (package_name, version, package_manager),
        )

        if results:
            analysis_data, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)

            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return json.loads(analysis_data)

        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM package_analysis WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM package_analysis")

            conn.commit()

        finally:
            conn.close()


class CommitComparisonCache(Cache):
    def __init__(self, cache_dir="cache/commits"):
        super().__init__(cache_dir, "commit_comparison_cache.db")

    def setup_db(self):
        """Initialize commit comparison cache tables"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS commit_authors_from_tags (
                package TEXT,
                tag1 TEXT,
                tag2 TEXT,
                data TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (package, tag1, tag2)
            )
        """,
            """
            CREATE TABLE IF NOT EXISTS commit_authors_from_url (
                commit_url TEXT PRIMARY KEY,
                data TEXT,
                cached_at TIMESTAMP
            )
        """,
            """
            CREATE TABLE IF NOT EXISTS patch_authors_from_sha (
                repo_name TEXT,
                patch_path TEXT,
                sha TEXT,
                data TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (repo_name, patch_path, sha)
            )
        """
        ]

        for query in queries:
            self._execute_query(query)

    def cache_authors_from_tags(self, package, tag1, tag2, data):
        self._execute_query(
            """
            INSERT OR REPLACE INTO commit_authors_from_tags 
            (package, tag1, tag2, data, cached_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (package, tag1, tag2, json.dumps(data), datetime.now().isoformat()),
        )

    def get_authors_from_tags(self, package, tag1, tag2, max_age_days=30):
        results = self._execute_query(
            "SELECT data, cached_at FROM commit_authors_from_tags WHERE package = ? AND tag1 = ? AND tag2 = ?",
            (package, tag1, tag2),
        )
        if results:
            data, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return json.loads(data)
        return None

    def cache_authors_from_url(self, commit_url, data):
        self._execute_query(
            """
            INSERT OR REPLACE INTO commit_authors_from_url 
            (commit_url, data, cached_at)
            VALUES (?, ?, ?)
        """,
            (commit_url, json.dumps(data), datetime.now().isoformat()),
        )

    def get_authors_from_url(self, commit_url, max_age_days=30):
        results = self._execute_query(
            "SELECT data, cached_at FROM commit_authors_from_url WHERE commit_url = ?", (commit_url,)
        )
        if results:
            data, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return json.loads(data)
        return None

    def cache_patch_authors(self, repo_name, patch_path, sha, data):
        self._execute_query(
            """
            INSERT OR REPLACE INTO patch_authors_from_sha 
            (repo_name, patch_path, sha, data, cached_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (repo_name, patch_path, sha, json.dumps(data), datetime.now().isoformat()),
        )

    def get_patch_authors(self, repo_name, patch_path, sha, max_age_days=30):
        results = self._execute_query(
            "SELECT data, cached_at FROM patch_authors_from_sha WHERE repo_name = ? AND patch_path = ? AND sha = ?", (repo_name, patch_path, sha)
        )
        if results:
            data, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return json.loads(data)
        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM commit_authors_from_tags WHERE cached_at < ?", (cutoff,))
                c.execute("DELETE FROM commit_authors_from_url WHERE cached_at < ?", (cutoff,))
                c.execute("DELETE FROM patch_authors_from_sha WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM commit_authors_from_tags")
                c.execute("DELETE FROM commit_authors_from_url")
                c.execute("DELETE FROM patch_authors_from_sha")

            conn.commit()

        finally:
            conn.close()


class UserCommitCache(Cache):
    def __init__(self, cache_dir="cache/user_commits"):
        super().__init__(cache_dir, "user_commits.db")

    def setup_db(self):
        self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS user_commit (
                api_url TEXT PRIMARY KEY,
                earliest_commit_sha TEXT,
                repo_name TEXT,
                package TEXT,
                author_login TEXT,
                author_commit_sha TEXT,
                author_login_in_1st_commit TEXT,
                author_id_in_1st_commit TEXT,
                cached_at TIMESTAMP
            )
        """
        )

    def cache_user_commit(self, api_url, earliest_commit_sha, repo_name, package, author_login, author_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit):
        self._execute_query(
            """
            INSERT OR REPLACE INTO user_commit 
            (api_url, earliest_commit_sha, repo_name, package, author_login, author_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (api_url, earliest_commit_sha, repo_name, package, author_login, author_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit, datetime.now().isoformat()),
        )

    def get_user_commit(self, api_url, max_age_days=30):
        results = self._execute_query(
            "SELECT earliest_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit, cached_at FROM user_commit WHERE api_url = ?",
            (api_url,),
        )
        if results:
            earliest_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return earliest_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit
        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM user_commit WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM user_commit")

            conn.commit()

        finally:
            conn.close()


class MavenDependencyCache(Cache):
    def __init__(self, cache_dir="cache/maven_deps"):
        super().__init__(cache_dir, "maven_deps.db")

    def setup_db(self):
        self._execute_query(
            """
            CREATE TABLE IF NOT EXISTS maven_dependencies (
                repo_path TEXT,
                pom_hash TEXT,
                dependencies TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (repo_path, pom_hash)
            )
        """
        )

    def cache_dependencies(self, repo_path, pom_hash, dependencies):
        self._execute_query(
            """
            INSERT OR REPLACE INTO maven_dependencies 
            (repo_path, pom_hash, dependencies, cached_at)
            VALUES (?, ?, ?, ?)
        """,
            (repo_path, pom_hash, json.dumps(dependencies), datetime.now().isoformat()),
        )

    def get_dependencies(self, repo_path, pom_hash, max_age_days=30):
        results = self._execute_query(
            "SELECT dependencies, cached_at FROM maven_dependencies WHERE repo_path = ? AND pom_hash = ?",
            (repo_path, pom_hash),
        )
        if results:
            deps_json, cached_at = results[0]
            cached_at = datetime.fromisoformat(cached_at)
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return json.loads(deps_json)
        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM maven_dependencies WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM maven_dependencies")

            conn.commit()

        finally:
            conn.close()


cache_manager = CacheManager()


def get_cache_manager():
    return cache_manager

def setup_logger(log_file_path, debug=False):
    """
    Setup the logger for the analysis.
    """
    class CustomFormatter(logging.Formatter):
        """Custom formatter, includes color coding for log levels."""
        grey = "\x1b[38;20m"
        green = "\x1b[38;2;0;200;0m"
        yellow = "\x1b[38;2;255;255;0m"
        red = "\x1b[38;2;255;0;0m"
        bold_red = "\x1b[1;31m"
        reset = "\x1b[0m"
        fmt = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"

        FORMATS = {
            logging.DEBUG: grey + fmt + reset,
            logging.INFO: green + fmt + reset,
            logging.WARNING: yellow + fmt + reset,
            logging.ERROR: red + fmt + reset,
            logging.CRITICAL: bold_red + fmt + reset,
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    # Set up the logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING if not debug else logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)

    # Create a formatter and set it for both handlers
    formatter = CustomFormatter()
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
