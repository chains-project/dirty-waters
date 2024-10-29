import requests
import logging
import os
from tool_config import setup_cache

github_token = os.getenv("GITHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}


def tag_format(tag, package_name):
    tag_formats = [
        f"{tag}",
        f"v{tag}",
        f"{package_name}@{tag}",
        f"{package_name}-v{tag}",
        f"{package_name}-{tag}",
    ]

    if "/" in package_name:
        only_package_name = package_name.split("/")[1]
        tag_formats.append(f"{only_package_name}@{tag}")
        tag_formats.append(f"{only_package_name}-v{tag}")
        tag_formats.append(f"{only_package_name}-{tag}")

    return tag_formats


def get_commit_authors(headers, packages_data):
    logging.info("Getting commits...")

    authors_per_package = {}
    for package, package_info in packages_data.items():
        if package_info.get("compare_message") == "COMPARE":
            print(f"Getting commits of {package}...")
            repo = package_info.get("repo_pure")
            repo_name = package_info.get("repo_name")
            category = package_info.get("message")

            tag1 = package_info.get("version1")
            tag2 = package_info.get("version2")

            tag1_chosen = package_info.get("chosen_v1")
            tag2_chosen = package_info.get("chosen_v2")

            authors_info = []

            comparison_found = False
            compare_urls = []

            tag_formats_new = tag_format(tag2_chosen, package)
            tag_formats_old = tag_format(tag1_chosen, package)

            for tag_format_old, tag_format_new in zip(tag_formats_old, tag_formats_new):
                compare_urls.append(
                    f"https://api.github.com/repos/{repo_name}/compare/{tag_format_old}...{tag_format_new}"
                )

                for compare_url in compare_urls:
                    # try:
                    response = requests.get(compare_url, headers=headers)
                    if response.status_code == 200:
                        comparison_found = True
                        break

                old_tag_urls = []
                new_tag_urls = []

                if comparison_found is False:
                    for tag_old in tag_formats_old:
                        old_tag_urls.append(f"https://api.github.com/repos/{repo_name}/git/ref/tags/{tag_old}")
                    for tag_new in tag_formats_new:
                        new_tag_urls.append(f"https://api.github.com/repos/{repo_name}/git/ref/tags/{tag_new}")

                    for old_tag_url in old_tag_urls:
                        try:
                            response = requests.get(old_tag_url, headers=headers)
                            if response.status_code == 200:
                                status_old = tag_old
                                break
                            else:
                                status_old = "GitHub old tag not found"
                                category = "Upgraded package"
                        except (ValueError, KeyError) as e:
                            logging.error("Error: %s", str(e))
                            print(f"Error: {e}")
                            # Error_old = f"{e}"
                            continue

                    for new_tag_url in new_tag_urls:
                        try:
                            response = requests.get(new_tag_url, headers=headers)
                            if response.status_code == 200:
                                status_new = tag_new
                                break
                            else:
                                status_new = "GitHub new tag not found"
                                category = "Upgraded package"
                        except (ValueError, KeyError) as e:
                            logging.error("Error: %s", str(e))
                            print(f"Error: {e}")
                            continue

                    authors_per_package[package] = {
                        "repo_name": repo_name,
                        "tag1": tag_old,
                        "status_old": status_old,
                        "tag2": tag_new,
                        "status_new": status_new,
                        "category": category,
                    }

                else:
                    response_json = response.json()
                    commits = response_json.get("commits")

                    if commits:
                        for commit in commits:
                            sha = commit.get("sha")
                            node_id = commit.get("node_id")
                            commit_url = commit.get("url")
                            author_data = commit.get("commit").get("author")
                            author_name = author_data.get("name")
                            author_email = author_data.get("email")
                            author_info = commit.get("author")

                            if author_info is None:
                                author_login = "No author info"
                                author_type = "No author info"
                                author_id = "No author info"
                            else:
                                author_login = commit.get("author").get("login", "No_author_login")
                                author_id = commit.get("author").get("id", "No_author_id")
                                author_type = commit.get("author").get("type", "No_author_type")

                            if commit.get("committer") is None:
                                committer_login = "No committer info"
                            else:
                                committer_login = commit.get("committer").get("login", None)
                                committer_id = commit.get("committer").get("id", None)
                                committer_type = commit.get("committer").get("type", None)

                                authors_info.append(
                                    {
                                        "sha": sha,
                                        "node_id": node_id,
                                        "commit_url": commit_url,
                                        "name": author_name,
                                        "email": author_email,
                                        "login": author_login,
                                        "a_type": author_type,
                                        "id": author_id,
                                        "committer_login": committer_login,
                                        "committer_id": committer_id,
                                        "c_type": committer_type,
                                    }
                                )

                        authors_per_package[package] = {
                            "repo": repo,
                            "repo_name": repo_name,
                            "tag1": tag1_chosen,
                            "tag2": tag2_chosen,
                            "category": category,
                            "compare_url": compare_url,
                            "authors": authors_info,
                        }

                    else:
                        authors_per_package[package] = {
                            "repo": repo,
                            "repo_name": repo_name,
                            "tag1": tag1,
                            "tag2": tag2,
                            "category": category,
                            "compare_url": compare_url,
                            "status_code": response.status_code,
                            "commits_info_message": "No commits found",
                        }

        else:
            authors_per_package[package] = {
                "compare_message": package_info.get("compare_message"),
                "repo_link": package_info.get("repo"),
                "repo_name": package_info.get("repo_name"),
                "tag1": package_info.get("chosen_v1"),
                "tag2": package_info.get("chosen_v2"),
                "category": package_info.get("message"),
                "v1_repo_link": package_info.get("v1_repo_link"),
                "v2_repo_link": package_info.get("v2_repo_link"),
                "repo_message": package_info.get("repo_message"),
            }

    return authors_per_package


def get_patch_commits(headers, repo_name, release_version, patch_data):
    logging.info("Getting commits for patches...")

    get_release_v_api = f"https://api.github.com/repos/{repo_name}/tags?per_page=100"

    grv_response = requests.get(get_release_v_api, headers=headers)
    grv_response_json = grv_response.json()

    for release in grv_response_json:
        if release.get("name") == release_version:
            release_version_sha = release.get("commit").get("sha")
            break
        else:
            release_version_sha = None

    authors_per_patches = {}

    for changed_patch, details in patch_data.items():
        authors_info = []
        path = details.get("patch_file_path")
        if path is None:
            api = None
            authors_per_patches[changed_patch] = {
                "patch_file_path": path,
                "repo_name": repo_name,
                "api": api,
                "error": True,
                "error_message": "No patch file path found",
            }
            continue

        if release_version_sha is None:
            authors_per_patches[changed_patch] = {
                "patch_file_path": path,
                "repo_name": repo_name,
                "api": None,
                "error": True,
                "error_message": "Release version not found",
            }
            continue

        api = f"https://api.github.com/repos/{repo_name}/commits?path=.yarn/patches/{path}&sha={release_version_sha}"
        response = requests.get(api, headers=headers)

        if response.status_code == 200:
            response_json = response.json()
            for commit in response_json:
                sha = commit.get("sha")
                node_id = commit.get("node_id")
                commit_url = commit.get("url")
                author_data = commit.get("commit").get("author")
                author_name = author_data.get("name")
                author_email = author_data.get("email")
                author_info = commit.get("author")
                author_type = author_data.get("type")
                if author_info is None:
                    author_login = "null"
                else:
                    author_login = commit.get("author").get("login")
                    author_id = commit.get("author").get("id")
                if commit.get("committer") is None:
                    committer_login = "null"
                else:
                    committer_login = commit.get("committer").get("login")
                    committer_id = commit.get("committer").get("id")
                    committer_type = commit.get("committer").get("type")

                    authors_info.append(
                        {
                            "sha": sha,
                            "node_id": node_id,
                            "commit_url": commit_url,
                            "name": author_name,
                            "email": author_email,
                            "login": author_login,
                            "a_type": author_type,
                            "id": author_id,
                            "committer_login": committer_login,
                            "committer_id": committer_id,
                            "c_type": committer_type,
                        }
                    )
        else:
            authors_per_patches[changed_patch] = {
                "patch_name": changed_patch,
                "repo_name": repo_name,
                "commit_url": api,
                "authors": None,
                "error": True,
                "error_message": response.status_code,
            }

        authors_per_patches[changed_patch] = {
            "patch_name": changed_patch,
            "repo_name": repo_name,
            "category": "patch",
            "commit_url": api,
            "authors": authors_info,
        }

    return authors_per_patches


def get_commit_results(api_headers, repo_name, release_version, patch_data, packages_data):
    setup_cache("package_commits")
    authors_per_patches_result = get_patch_commits(api_headers, repo_name, release_version, patch_data)
    authors_per_package_result = get_commit_authors(headers, packages_data)
    commit_results = {**authors_per_patches_result, **authors_per_package_result}

    return commit_results
