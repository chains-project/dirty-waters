import os
import subprocess
import re
import json
import sqlite3
import logging
import requests
import xmltodict
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
    else:
        # could be a redirect, so we'll make a request to the URL to get the final URL
        match = GITHUB_URL_PATTERN.search(url)
        if not match:
            try:
                url = requests.head(url, allow_redirects=True).url
            except requests.exceptions.RequestException:
                logging.warning(f"Could not check for redirections, was using {url}")
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


def get_scm_command(pm: str, package: str) -> List[str]:
    """Get the appropriate command to find a package's source code locations for the package manager."""
    if pm == "yarn-berry" or pm == "yarn-classic":
        return ["yarn", "info", package.replace("@npm:", "@"), "repository.url", "--silent"]
    elif pm == "pnpm":
        # for cases like @babel/helper-create-class-features-plugin@7.25.9(@babel/core@7.26.10),
        # we look for the repository of the package inside parentheses
        if "(" in package:
            package = package.split("(")[1].split(")")[0]
        return ["pnpm", "info", package.replace("@npm:", "@"), "repository.url"]
    elif pm == "npm":
        return ["npm", "info", package.replace("@npm:", "@"), "repository.url"]
    elif pm == "maven":
        name, version = package.split("@")
        group_id, artifact_id = name.split(":")
        return [
            "mvn",
            "org.apache.maven.plugins:maven-help-plugin:3.5.1:evaluate",
            f"-Dexpression=project",
            f"-Dartifact={group_id}:{artifact_id}:{version}",
            "-q",
            "-DforceStdout",
        ]
    raise ValueError(f"Unsupported package manager: {pm}")


def run_scm_command(pm, command):
    def run_npm_command(command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logging.warning(
                f"Command {command} timed out after {TIMEOUT} seconds",
            )
            return None
        except subprocess.CalledProcessError as e:
            logging.warning(f"Command {command} failed: {e}")
            return None

    def run_maven_command(command):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT,
            )
            output = result.stdout
            if output:
                parsed_content = xmltodict.parse(output)
                locations = [
                    parsed_content.get("project", {}).get("scm", {}).get("url", ""),
                    parsed_content.get("project", {}).get("scm", {}).get("connection", ""),
                    parsed_content.get("project", {}).get("scm", {}).get("developerConnection", ""),
                    parsed_content.get("project", {}).get("url", ""),
                ]
                return next((loc for loc in locations if loc), None)

        except subprocess.TimeoutExpired:
            logging.warning(
                f"Command {command} timed out after {TIMEOUT} seconds",
            )
            return None
        except subprocess.CalledProcessError as e:
            logging.warning(f"Command {command} failed: {e}")
            return None

    if pm == "npm" or pm == "yarn-berry" or pm == "yarn-classic" or pm == "pnpm":
        return run_npm_command(command)
    elif pm == "maven":
        return run_maven_command(command)
    raise ValueError(f"Unsupported package manager: {pm}")


def process_package(
    package,
    parent,
    command,
    pm,
    repos_output,
    undefined,
    same_repos_deps,
    some_errors,
    repos_output_json,
):
    def check_if_valid_repo_info(repo_info):
        retrieved_info = {
            "url": "",
            "parent": "",
            "message": "",
            "command": "",
        }
        if (
            repo_info is None
            or "Undefined" in repo_info
            or "undefined" in repo_info
            or "ERR!" in repo_info
            or "null object" in repo_info
        ):
            logging.warning(f"Could not find repository for {package}")
            retrieved_info.update(
                {
                    "url": "Could not find",
                    "parent": parent,
                    "message": "Could not find repository",
                    "command": command,
                }
            )
            repos_output_json[package] = retrieved_info
            undefined.append(f"Undefined for {package}, {repo_info}")
            return False, retrieved_info

        url, message = extract_repo_url(repo_info)
        retrieved_info.update(
            {
                "url": url,
                "parent": parent,
                "message": message,
                "command": command,
            }
        )
        repos_output_json[package] = retrieved_info
        if message == "GitHub repository":
            logging.info(f"Found GitHub URL for {package}: {url}")
            repos_output.append(url)
            same_repos_deps.get("url", []).append(package)
            return True, retrieved_info
        else:
            logging.info(f"Found non-GitHub URL for {package}: {url}")
            some_errors.append(f"No GitHub URL for {package}\n{repo_info}")
            return False, retrieved_info

    retrieved_info = cache_manager.github_cache.get_github_url(package)
    if not retrieved_info:
        result = run_scm_command(pm, get_scm_command(pm, package))
        if result:
            valid_repo_info, retrieved_info = check_if_valid_repo_info(result)
        else:
            logging.warning(f"SCM command failed for {package}")
            retrieved_info = {
                "url": "Could not find",
                "parent": parent,
                "message": "Could not find repository",
                "command": command,
            }
            repos_output_json[package] = retrieved_info
            undefined.append(f"Undefined for {package}, {result}")

        cache_manager.github_cache.cache_github_url(package, retrieved_info)
    else:
        logging.info(f"Found cached URL for {package}: {retrieved_info.get('url', '-')}")
        valid_repo_info = "GitHub repository" == retrieved_info["message"]
        if parent != retrieved_info.get("parent", None):
            # tackles scenarios where parent was cached and then removed; incoming parent should take precedence
            retrieved_info.update({"parent": parent})
            cache_manager.github_cache.cache_github_url(package, retrieved_info)
        repos_output_json[package] = retrieved_info
        if valid_repo_info:
            repos_output.append(retrieved_info["url"])
            same_repos_deps.get("url", []).append(package)
        else:
            some_errors.append(f"No GitHub URL for {package}\n{retrieved_info['url']}")


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
            parent = pkg_res.get("parent", None)
            command = pkg_res.get("command", None)
            process_package(
                package,
                parent,
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
