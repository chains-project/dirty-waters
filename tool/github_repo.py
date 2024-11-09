import os
import subprocess
import re
import json
import sqlite3
import logging
from pathlib import Path
from tqdm import tqdm

# from datetime import datetime


TIMEOUT = 60

script_dir = Path(__file__).parent.absolute()
database_file = script_dir / "database" / "github_repo_info_all.db"

conn = sqlite3.connect(database_file)
c = conn.cursor()

c.execute(
    """CREATE TABLE IF NOT EXISTS pkg_github_repo_output (
                package TEXT PRIMARY KEY,
                github TEXT)"""
)

conn.commit()


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


def extract_repo_url(repo_info):
    pattern = r"(github.*)"
    match = re.search(pattern, repo_info, re.IGNORECASE)
    return match.group(1) if match else "not github"


def process_package(
    package,
    pm,
    repos_output,
    undefined,
    same_repos_deps,
    some_errors,
    repos_output_json,
):
    c.execute("SELECT github FROM pkg_github_repo_output WHERE package = ?", (package,))
    db_result = c.fetchone()

    if db_result:
        repo_info = db_result[0]

    else:
        try:
            if pm == "yarn-berry" or pm == "yarn-classic":
                command = ["yarn", "info", package, "repository.url"]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT,
                )

            elif pm == "pnpm":
                command = ["pnpm", "info", package, "repository.url"]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT,
                )

            elif pm == "npm":
                command = ["npm", "info", package, "repository.url"]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT,
                )

            elif pm == "maven":
                # package is in the form of group_id:artifact_id@version -- we need all 3
                name, version = package.split("@")
                group_id, artifact_id = name.split(":")
                command = [
                    "mvn",
                    "help:evaluate",
                    "-Dexpression=project.scm.url",
                    f"-Dartifact={group_id}:{artifact_id}:{version}",
                    "-q",
                    "-DforceStdout",
                ]
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=TIMEOUT,
                )

            else:
                raise ValueError(f"Unsupported package manager: {pm}")

            repo_info = result.stdout if result.stdout else result.stderr
            # print(f"Repo info for {package}: {repo_info}")
            c.execute(
                "INSERT OR IGNORE INTO pkg_github_repo_output (package, github) VALUES (?,?)",
                (package, repo_info),
            )
            conn.commit()

        except subprocess.TimeoutExpired:
            logging.error(
                f"Command {command} timed out after {TIMEOUT} seconds for package {package}",
            )
            repo_info = None

        except subprocess.CalledProcessError as e:
            logging.error(f"Command {command} failed for package {package}: {e}")
            repo_info = None

    # TODO: npm?
    package = package.replace("@npm:", "@")

    if (
        repo_info is None
        or "Undefined" in repo_info
        or "undefined" in repo_info
        or "ERR!" in repo_info
        # or "error" in repo_info
    ):
        repos_output_json[package] = {"github": "Could not find"}
        undefined.append(f"Undefined for {package}, {repo_info}")
    else:
        url = extract_repo_url(repo_info)
        # print(f"[INFO] Found GitHub URL for {package}: {url}")
        repos_output_json[package] = {"github": url}
        if url:
            repos_output.append(url)
            if url not in same_repos_deps:
                same_repos_deps[url] = []
            same_repos_deps[url].append(package)
        else:
            some_errors.append(f"No GitHub URL for {package}\n{repo_info}")


def get_github_repo_url(folder, dep_list, pm):
    repos_output = []  # List to store GitHub URLs
    some_errors = []  # List to store packages without a GitHub URL
    undefined = []  # List to store packages with undefined repository URLs
    same_repos_deps = {}  # Dict to store packages with same GitHub URL
    repos_output_json = {}  # Dict to store packages with GitHub URL

    print("Getting GitHub URLs of packages...")
    total_packages_to_process = len(dep_list.get("resolutions", []))
    # have not process patches
    with tqdm(total=total_packages_to_process, desc="Getting GitHub URLs") as pbar:
        for pkg_res in dep_list.get("resolutions"):
            package = pkg_res

            process_package(
                package,
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
