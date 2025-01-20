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
        self.commit_cache = CommitCache(cache_dir)
        self.repo_cache = PackageRepoCache(cache_dir)
        self.maven_cache = MavenDependencyCache(cache_dir)
        self.dep_cache = DependencyComparisonCache(cache_dir)
        
        # Setup requests cache
        self._setup_requests_cache()
    
    def _setup_requests_cache(self):
        requests_cache.install_cache(
            cache_name=str(self.cache_dir / "http_cache"),
            backend="sqlite",
            expire_after=7776000,  # 90 days
            allowable_codes=(200, 301, 302, 404)
        )
    
    def clear_all_caches(self, older_than_days=None):
        """Clear all caches"""
        self.github_cache.clear_cache(older_than_days)
        self.package_cache.clear_cache(older_than_days)
        self.commit_cache.clear_cache(older_than_days)
        self.repo_cache.clear_cache(older_than_days)
        self.maven_cache.clear_cache(older_than_days)
        self.dep_cache.clear_cache(older_than_days)
        
    @property
    def http(self):
        """Access to requests cache"""
        return requests_cache.CachedSession()


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
            """CREATE TABLE IF NOT EXISTS pr_reviews (
                review_id TEXT PRIMARY KEY,
                repo_name TEXT,
                author TEXT,
                review_data TEXT,
                cached_at TIMESTAMP,
                UNIQUE(repo_name, author)
            )""",
            """CREATE TABLE IF NOT EXISTS repo_info (
                repo_url TEXT PRIMARY KEY,
                api_data TEXT,
                cached_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS github_urls (
                package TEXT PRIMARY KEY,
                repo_url TEXT,
                cached_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pr_info (
                pr_number INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                state TEXT,
                cached_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pr_reviews (
                review_id TEXT PRIMARY KEY,
                repo_name TEXT,
                author TEXT,
                review_data TEXT,
                cached_at TIMESTAMP,
                UNIQUE(repo_name, author)
            )""",
        ]
        
        for query in queries:
            self._execute_query(query)
    
    @lru_cache(maxsize=1000)
    def get_repo_info(self, repo_url):
        """Get repository information with caching"""
        # Check in-memory cache first
        if repo_url in self.repo_cache:
            cached_data = self.repo_cache[repo_url]
            if datetime.now() - cached_data['cached_at'] < timedelta(hours=1):
                return cached_data['data']
        
        # Check SQLite cache
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT api_data, cached_at FROM repo_info WHERE repo_url = ?", (repo_url,))
        result = c.fetchone()
        
        if result:
            api_data, cached_at = result
            cached_at = datetime.fromisoformat(cached_at)
            
            # Return cached data if it's less than 1 day old
            if datetime.now() - cached_at < timedelta(days=1):
                data = json.loads(api_data)
                # Update in-memory cache
                self.repo_cache[repo_url] = {
                    'data': data,
                    'cached_at': datetime.now()
                }
                return data
        
        # If not in cache or expired, fetch from GitHub API
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo_url}",
                headers=headers, 
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            
            # Store in both caches
            c.execute(
                "INSERT OR REPLACE INTO repo_info (repo_url, api_data, cached_at) VALUES (?, ?, ?)",
                (repo_url, json.dumps(data), datetime.now().isoformat())
            )
            conn.commit()
            
            self.repo_cache[repo_url] = {
                'data': data,
                'cached_at': datetime.now()
            }
            
            return data
            
        except Exception as e:
            logging.error(f"Error fetching repo info for {repo_url}: {str(e)}")
            return None
        finally:
            conn.close()

    def cache_pr_review(self, review_id, repo_name, author, review_data):
        """Cache PR review information"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO pr_reviews 
                (review_id, repo_name, author, review_data, cached_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                review_id,
                repo_name,
                author,
                json.dumps(review_data),
                datetime.now().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_pr_review(self, review_id=None, repo_name=None, author=None):
        """Get PR review information from cache"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            if review_id:
                c.execute("SELECT review_data, cached_at FROM pr_reviews WHERE review_id = ?", (review_id,))
            else:
                c.execute(
                    "SELECT review_data, cached_at FROM pr_reviews WHERE repo_name = ? AND author = ?",
                    (repo_name, author)
                )
            
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
            c.execute("""
                INSERT OR REPLACE INTO github_urls 
                (package, repo_url, cached_at)
                VALUES (?, ?, ?)
            """, (
                package,
                repo_url,
                datetime.now().isoformat()
            ))
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
    
    # TODO: this aint right, it should be commit node ID instead of pr number
    def get_pr_info(self, pr_number: int) -> Optional[Dict]:
        """Get PR info from cache if available and not expired"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT * FROM pr_info WHERE pr_number = ?", 
                (pr_number,)
            ).fetchone()
            
            if result:
                cached_at = datetime.fromisoformat(result["cached_at"])
                if datetime.now() - cached_at < timedelta(hours=24):
                    return {
                        "number": result["pr_number"],
                        "title": result["title"],
                        "author": result["author"],
                        "created_at": result["created_at"],
                        "updated_at": result["updated_at"],
                        "state": result["state"]
                    }
        return None

    def cache_pr_info(self, pr_data: Dict):
        """Cache PR info with current timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pr_info
                (pr_number, title, author, created_at, updated_at, state, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pr_data["number"],
                pr_data["title"],
                pr_data["author"],
                pr_data["created_at"],
                pr_data["updated_at"], 
                pr_data["state"],
                datetime.now().isoformat()
            ))
            conn.commit()
    
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
            self.repo_cache.clear()  # Clear in-memory cache
            
        finally:
            conn.close()


class PackageAnalysisCache(Cache):
    def __init__(self, cache_dir="cache/packages"):
        super().__init__(cache_dir, "package_analysis.db")
        
    def setup_db(self):
        """Initialize package analysis cache tables"""
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS package_analysis (
                package_name TEXT,
                version TEXT,
                package_manager TEXT,
                analysis_data TEXT,
                analyzed_at TIMESTAMP,
                PRIMARY KEY (package_name, version, package_manager)
            )
        """)
    
    def cache_package_analysis(self, package_name, version, package_manager, analysis_data):
        """Cache package analysis results"""
        self._execute_query("""
            INSERT OR REPLACE INTO package_analysis 
            (package_name, version, package_manager, analysis_data, analyzed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            package_name,
            version,
            package_manager,
            json.dumps(analysis_data),
            datetime.now().isoformat()
        ))
    
    def get_package_analysis(self, package_name, version, package_manager, max_age_days=30):
        """Get cached package analysis results"""
        results = self._execute_query(
            """SELECT analysis_data, analyzed_at 
               FROM package_analysis 
               WHERE package_name = ? AND version = ? AND package_manager = ?""",
            (package_name, version, package_manager)
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
            self.repo_cache.clear()  # Clear in-memory cache
            
        finally:
            conn.close()


class CommitCache(Cache):
    def __init__(self, cache_dir="cache/commits"):
        super().__init__(cache_dir, "commit_cache.db")
        
    def setup_db(self):
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS commit_data (
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
        """)
    
    def cache_commit(self, api_url, commit_data):
        self._execute_query("""
            INSERT OR REPLACE INTO commit_data 
            (api_url, earliest_commit_sha, repo_name, package, author_login, 
             author_commit_sha, author_login_in_1st_commit, author_id_in_1st_commit, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api_url,
            commit_data['earliest_commit_sha'],
            commit_data['repo_name'],
            commit_data['package'],
            commit_data['author_login'],
            commit_data['author_commit_sha'],
            commit_data['author_login_in_1st_commit'],
            commit_data['author_id_in_1st_commit'],
            datetime.now().isoformat()
        ))

    def get_commit(self, api_url, max_age_days=30):
        results = self._execute_query(
            "SELECT * FROM commit_data WHERE api_url = ?",
            (api_url,)
        )
        if results:
            data = results[0]
            cached_at = datetime.fromisoformat(data[-1])
            if datetime.now() - cached_at < timedelta(days=max_age_days):
                return {
                    'earliest_commit_sha': data[1],
                    'repo_name': data[2],
                    'package': data[3],
                    'author_login': data[4],
                    'author_commit_sha': data[5],
                    'author_login_in_1st_commit': data[6],
                    'author_id_in_1st_commit': data[7]
                }
        return None

    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM commit_data WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM commit_data")
            
            conn.commit()
            
        finally:
            conn.close()


class MavenDependencyCache(Cache):
    def __init__(self, cache_dir="cache/maven_deps"):
        super().__init__(cache_dir, "maven_deps.db")
        
    def setup_db(self):
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS maven_dependencies (
                repo_path TEXT,
                pom_hash TEXT,
                dependencies TEXT,
                cached_at TIMESTAMP,
                PRIMARY KEY (repo_path, pom_hash)
            )
        """)
    
    def cache_dependencies(self, repo_path, pom_hash, dependencies):
        self._execute_query("""
            INSERT OR REPLACE INTO maven_dependencies 
            (repo_path, pom_hash, dependencies, cached_at)
            VALUES (?, ?, ?, ?)
        """, (
            repo_path,
            pom_hash,
            json.dumps(dependencies),
            datetime.now().isoformat()
        ))
    
    def get_dependencies(self, repo_path, pom_hash, max_age_days=30):
        results = self._execute_query(
            "SELECT dependencies, cached_at FROM maven_dependencies WHERE repo_path = ? AND pom_hash = ?",
            (repo_path, pom_hash)
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


class PackageRepoCache(Cache):
    def __init__(self, cache_dir="cache"):
        super().__init__(cache_dir, "github_repo_info.db")
        
    def setup_db(self):
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS pkg_github_repo_output (
                package TEXT PRIMARY KEY,
                github TEXT,
                cached_at TIMESTAMP
            )
        """)
    
    def get_repo_info(self, package):
        results = self._execute_query(
            "SELECT github FROM pkg_github_repo_output WHERE package = ?",
            (package,)
        )
        return results[0][0] if results else None
    
    def cache_repo_info(self, package, repo_info):
        self._execute_query(
            "INSERT OR REPLACE INTO pkg_github_repo_output (package, github, cached_at) VALUES (?, ?, ?)",
            (package, repo_info, datetime.now().isoformat())
        )
    
    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM pkg_github_repo_output WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM pkg_github_repo_output")
            
            conn.commit()
            
        finally:
            conn.close()


class DependencyComparisonCache(Cache):
    def __init__(self, cache_dir="cache/dependency_comparisons"):
        super().__init__(cache_dir, "dependency_comparisons.db")
        
    def setup_db(self):
        """Initialize dependency comparison cache tables"""
        self._execute_query("""
            CREATE TABLE IF NOT EXISTS dependency_comparisons (
                dep_hash TEXT PRIMARY KEY,
                comparison_data TEXT,
                cached_at TIMESTAMP
            )
        """)

    def cache_comparison(self, dep_hash, comparison_data):
        self._execute_query("""
            INSERT OR REPLACE INTO dependency_comparisons 
            (dep_hash, comparison_data, cached_at)
            VALUES (?, ?, ?)
        """, (dep_hash, json.dumps(comparison_data), datetime.now().isoformat()))

    def get_comparison(self, dep_hash):
        results = self._execute_query(
            "SELECT comparison_data FROM dependency_comparisons WHERE dep_hash = ?",
            (dep_hash,)
        )
        return json.loads(results[0][0]) if results else None
    
    def clear_cache(self, older_than_days=None):
        """Clear cached data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            if older_than_days:
                cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                c.execute("DELETE FROM dependency_comparisons WHERE cached_at < ?", (cutoff,))
            else:
                c.execute("DELETE FROM dependency_comparisons")
                
            conn.commit()
            
        finally:
            conn.close()


cache_manager = CacheManager()

def get_cache_manager():
    return cache_manager


def setup_logger(log_file_path):
    """
    Setup the logger for the analysis.
    """

    # Set up the logger
    logger = logging.getLogger("dw_analysis")
    logger.setLevel(logging.INFO)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
