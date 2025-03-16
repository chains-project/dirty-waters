import os
import subprocess
import re
import json
import sqlite3
import logging
from pathlib import Path
from tqdm import tqdm
from tool.tool_config import get_cache_manager
from typing import List

TIMEOUT = 60

cache_manager = get_cache_manager()
GITHUB_URL_PATTERN = re.compile(r"(github.*)", re.IGNORECASE)


def write_output(folder_path, filename, data):
    folder_path = os.path.join(folder_path, "dep_lists")
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    # check if the folder exists

    with open(file_path, "w", encoding="utf-8") as f:
        if isinstance(data, list):
            f.write("\n".join(data))
            f.write(f"\nTotal: {len(data)}\n")
        else:
            json.dump(data, f, indent=2)


def extract_repo_url(repo_info: str) -> str:
    """Extract GitHub repository URL from repository information."""
    url = repo_info
    if "https" not in repo_info:
        # cases such as git@github:apache/maven-scm, we just remove the :
        url = url.replace(":/", "/")
    url = url.replace(":", "/")
    match = GITHUB_URL_PATTERN.search(url)
    if not match:
        return repo_info, "Not a GitHub repository"

    # if there is a match, there's still the possibility of the scm url having been
    # put in a different form, e.g.,
    # github.com/apache/maven-scm/tree/maven-scm-2.1.0/maven-scm-providers/maven-scm-providers-standard
    # from here, we only want the URL up until the second-most directory after github.com
    url = match.group(0)
    parts = url.split("/")
    joined = "/".join(parts[:3]) if len(parts) > 3 else url
    joined = joined if not joined.endswith(".git") else joined[:-4]
    return joined, "GitHub repository"


def get_scm_commands(pm: str, package: str) -> List[str]:
    """Get the appropriate command to find a package's source code locations for the package manager."""
    if pm == "yarn-berry" or pm == "yarn-classic":
        return [["yarn", "info", package.replace("@npm:", "@"), "repository.url", "--silent"]]
    elif pm == "pnpm":
        return [["pnpm", "info", package.replace("@npm:", "@"), "repository.url"]]
    elif pm == "npm":
        return [["npm", "info", package.replace("@npm:", "@"), "repository.url"]]
    elif pm == "maven":
        name, version = package.split("@")
        group_id, artifact_id = name.split(":")
        return [
            [
                "mvn",
                "org.apache.maven.plugins:maven-help-plugin:3.5.1:evaluate",
                f"-Dexpression={source_code_location}",
                f"-Dartifact={group_id}:{artifact_id}:{version}",
                "-q",
                "-DforceStdout",
            ]
            for source_code_location in [
                "project.scm.url",
                "project.scm.connection",
                "project.scm.developerConnection",
                "project.url",
            ]
        ]
    raise ValueError(f"Unsupported package manager: {pm}")


def process_package(
    package,
    command,
    pm,
    repos_output,
    undefined,
    same_repos_deps,
    some_errors,
    repos_output_json,
):
    def check_if_valid_repo_info(repo_info):
        if repo_info is None or "Undefined" in repo_info or "undefined" in repo_info or "ERR!" in repo_info:
            repos_output_json[package] = {
                "url": "Could not find",
                "message": "Could not find repository",
                "command": command,
            }
            undefined.append(f"Undefined for {package}, {repo_info}")
            return False

        url, message = extract_repo_url(repo_info)
        repos_output_json[package] = {"url": url, "message": message, "command": command}
        if url:
            repos_output.append(url)
            same_repos_deps.get("url", []).append(package)
            return True
        else:
            some_errors.append(f"No GitHub URL for {package}\n{repo_info}")
            return False

    repo_info = cache_manager.github_cache.get_github_url(package)
    valid_repo_info = False
    if not repo_info:
        for scm_command in get_scm_commands(pm, package):
            try:
                result = subprocess.run(
                    scm_command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT,
                )
                if result.stdout:
                    repo_info = result.stdout
                    valid_repo_info = check_if_valid_repo_info(repo_info)
                    if valid_repo_info:
                        break
                    repo_info = None
                else:
                    repo_info = result.stderr
            except subprocess.TimeoutExpired:
                logging.warning(
                    f"Command {scm_command} timed out after {TIMEOUT} seconds for package {package}",
                )
                repo_info = None
            except subprocess.CalledProcessError as e:
                logging.warning(f"Command {scm_command} failed for package {package}: {e}")
                repo_info = "ERR!"

        if repo_info:
            # Must still run the check if all cases were errors
            check_if_valid_repo_info(repo_info)
        logging.info(f"Package {package} repository info: {repo_info}")
        cache_manager.github_cache.cache_github_url(package, repo_info)
    else:
        check_if_valid_repo_info(repo_info)


def get_github_repo_url(folder, dep_list, pm):
    repos_output = []  # List to store GitHub URLs
    some_errors = []  # List to store packages without a GitHub URL
    undefined = []  # List to store packages with undefined repository URLs
    same_repos_deps = {}  # Dict to store packages with same GitHub URL
    repos_output_json = {}  # Dict to store packages with GitHub URL

    logging.info("Getting GitHub URLs of packages...")
    total_packages_to_process = len(dep_list.get("resolutions", []))
    # have not process patches
    with tqdm(total=total_packages_to_process, desc="Getting GitHub URLs") as pbar:
        for pkg_res in dep_list.get("resolutions"):
            package = pkg_res["info"]
            command = pkg_res.get("command", None)
            process_package(
                package,
                command,
                pm,
                repos_output,
                undefined,
                same_repos_deps,
                some_errors,
                repos_output_json,
            )
            pbar.update(1)

    # Write collected data to files
    unique_repos_output = sorted(set(repos_output))
    outputs = {
        # "github_repo_all.txt": repos_output,
        # "github_repo_unique.txt": unique_repos_output,
        "github_repo_undefined.log": undefined,
        # "github_repo_some_error.log": some_errors,
        "github_repos_depsnsamerepo.json": same_repos_deps,
        "github_repos_output.json": repos_output_json,
    }

    for filename, data in outputs.items():
        write_output(folder, filename, data)

    return repos_output_json
