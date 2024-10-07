import os
import subprocess
import re
import json
import sqlite3

# from datetime import datetime
from pathlib import Path


script_dir = Path(__file__).parent.absolute()
database_file = script_dir / "database" / "github_repo_info_all.db"

conn = sqlite3.connect(database_file)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS pkg_github_repo_output (
                package TEXT PRIMARY KEY,
                github TEXT)""")

conn.commit()


def write_output(folder_path, filename, data):
    folder_path = os.path.join(folder_path, "dep_lists")
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    # check if the folder exists

    with open(file_path, "w") as f:
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

    print(f"Getting packges {package}'s GitHub URL...")

    if db_result:
        repo_info = db_result[0]
        print(f"Repo info from database {package}: {repo_info}")

    else:
        try:
            if pm == "yarn-berry" or pm == "yarn-classic":
                result = subprocess.run(
                    ["yarn", "info", package, "repository.url"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            elif pm == "pnpm":
                result = subprocess.run(
                    ["pnpm", "info", package, "repository.url"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            repo_info = result.stdout if result.stdout else result.stderr
            print(f"Repo info for {package}: {repo_info}")
            c.execute(
                "INSERT OR IGNORE INTO pkg_github_repo_output (package, github) VALUES (?,?)",
                (package, repo_info),
            )
            conn.commit()

        except subprocess.CalledProcessError as e:
            some_errors.append(f"Error for {package}: {e.stderr}")
            repo_info = None

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

    # have not process patches
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

    # Write collected data to files
    unique_repos_output = sorted(set(repos_output))
    outputs = {
        "github_repo_all.txt": repos_output,
        "github_repo_unique.txt": unique_repos_output,
        "github_repo_undefined.log": undefined,
        "github_repo_some_error.log": some_errors,
        "github_repos_depsnsamerepo.json": same_repos_deps,
        "github_repos_output.json": repos_output_json,
    }

    for filename, data in outputs.items():
        write_output(folder, filename, data)

    return repos_output_json
