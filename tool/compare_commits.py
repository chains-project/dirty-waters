import requests
import logging
import os
from tool.tool_config import get_cache_manager, make_github_request

cache_manager = get_cache_manager()


def tag_format(tag, package_name, repo_name):
    _, repo_name = repo_name.split("/")  # splits owner and repo name
    project_name = repo_name.split("-")[-1]  # deals with lots of maven-<project_name> repos (e.g., surefire, etc)
    tag_formats = set(
        [
            f"{tag}",
            f"v{tag}",
            f"v_{tag}",
            f"r{tag}",
            f"release-{tag}",
            f"parent-{tag}",
            # Below: further tag formats found in the AROMA paper, table 3: https://dl.acm.org/doi/pdf/10.1145/3643764
            f"release/{tag}",
            f"{tag}-release",
            f"v.{tag}",
        ]
        + [
            f"{name}{suffix}"
            for name in [package_name, repo_name, project_name]
            for suffix in [f"@{tag}", f"-v{tag}", f"_v{tag}", f"-{tag}", f"_{tag}"]
        ]
    )

    only_package_name, artifact_id_parts = None, None
    if "/" in package_name:  # NPM-based
        only_package_name = package_name.split("/")[1]
    elif ":" in package_name:  # Maven based
        only_package_name = package_name.split(":")[1].split("@")[0]
        # p1, p2, p3 from AROMA
        artifact_id_parts = only_package_name.split("-")

    if only_package_name:
        tag_formats.add(f"{only_package_name}@{tag}")
        tag_formats.add(f"{only_package_name}-v{tag}")
        tag_formats.add(f"{only_package_name}-{tag}")
        tag_formats.add(f"{only_package_name}_{tag}")
    if artifact_id_parts and len(artifact_id_parts) > 1:
        # p1, p2, p3 from AROMA
        # needs to be reversed with [::-1] because p1 is actually the last element, p2 the 2nd to last, etc
        tag_formats.update(["-".join(artifact_id_parts[::-1][: i + 1]) + tag for i in range(len(artifact_id_parts))])

    return tag_formats


def find_existing_tags_batch(tag_formats, repo_name):
    # Get all tags in one request; MAY FAIL if the repo has too many tags
    tags_url = f"https://api.github.com/repos/{repo_name}/git/refs/tags"
    response = make_github_request(tags_url)

    if not response:
        return []
    elif response == 504:
        for tag_format in tag_formats:
            response = make_github_request(f"{tags_url}/{tag_format}")
            if response:
                return [tag_format]
        return []

    # Create a map of all tags
    all_tags = {ref["ref"].replace("refs/tags/", ""): ref for ref in response}

    # Find the matching tag formats
    matching_tags = []
    for tag_format in tag_formats:
        if tag_format in all_tags:
            matching_tags.append(tag_format)

    return matching_tags if matching_tags else []


def get_commit_info(commit):
    if commit.get("committer") is None:
        committer_login = "No committer info"
        return None

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

    return {
        "sha": sha,
        "node_id": node_id,
        "commit_url": commit_url,
        "name": author_name,
        "email": author_email,
        "login": author_login,
        "a_type": author_type,
        "id": author_id,
    }


def get_authors_from_response(url, data, package_info):
    result = {
        "repo": package_info.get("repo_pure"),
        "repo_name": package_info.get("repo_name"),
        "category": package_info.get("message"),
        "compare_url": url,
    }

    authors_info = []
    commits = data.get("commits")
    if commits:
        for commit in commits:
            # Retrieve commit info from cache
            commit_info = cache_manager.commit_comparison_cache.get_authors_from_url(commit.get("url"))
            if not commit_info:
                commit_info = get_commit_info(commit)
                cache_manager.commit_comparison_cache.cache_authors_from_url(commit.get("url"), commit_info)

            if commit_info:
                authors_info.append(commit_info)
        result.update(
            {
                "authors": authors_info,
                "tag1": package_info.get("chosen_v1"),
                "tag2": package_info.get("chosen_v2"),
            }
        )
    else:
        result.update(
            {
                "tag1": package_info.get("version1"),
                "tag2": package_info.get("version2"),
                "commits_info_message": "No commits found",
                "status_code": 200,
            }
        )

    return result


def get_authors_from_tags(tag1, tag2, package, package_info):
    repo_name = package_info.get("repo_name")
    tag_formats_old = tag_format(tag1, package, repo_name)
    existing_tag_format_old = find_existing_tags_batch(tag_formats_old, repo_name)
    logging.info(f"Existing tag format old: {existing_tag_format_old}")
    tag_formats_new = tag_format(tag2, package, repo_name)
    existing_tag_format_new = find_existing_tags_batch(tag_formats_new, repo_name)
    logging.info(f"Existing tag format new: {existing_tag_format_new}")

    if not existing_tag_format_old:
        status_old = "GitHub old tag not found"
    if not existing_tag_format_new:
        status_new = "GitHub new tag not found"

    response = None
    for old_tag, new_tag in zip(existing_tag_format_old, existing_tag_format_new):
        logging.info(f"Old tag: {old_tag}, New tag: {new_tag}")
        compare_url = f"https://api.github.com/repos/{repo_name}/compare/{old_tag}...{new_tag}"
        response = make_github_request(compare_url, max_retries=2)
        if response:
            logging.info(f"Found response for {old_tag}...{new_tag}")
            break

    if not response:
        status_old = "GitHub old tag not found" if not existing_tag_format_old else existing_tag_format_old[0]
        status_new = "GitHub new tag not found" if not existing_tag_format_new else existing_tag_format_new[0]

        return {
            "tag1": existing_tag_format_old[0] if existing_tag_format_old else list(tag_formats_old)[0],
            "tag2": existing_tag_format_new[0] if existing_tag_format_new else list(tag_formats_new)[0],
            "status_old": status_old,
            "status_new": status_new,
            "category": "Upgraded package",
            "repo_name": package_info.get("repo_name"),
        }

    return get_authors_from_response(compare_url, response, package_info)


def get_patch_authors(repo_name, patch_name, path, release_version_sha, headers):
    url = f"https://api.github.com/repos/{repo_name}/commits?path=.yarn/patches/{path}&sha={release_version_sha}"
    patch_info = {
        "patch_name": patch_name,
        "repo_name": repo_name,
        "commit_url": url,
    }

    response = make_github_request(url, headers=headers)
    authors_info = []
    if response:
        for commit in response:
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
        patch_info.update(
            {
                "category": "patch",
                "authors": authors_info,
            }
        )
    else:
        patch_info.update(
            {
                "authors": None,
                "error": True,
                "error_message": response.status_code,
            }
        )

    return patch_info


def get_commit_authors(packages_data):
    logging.info("Getting commits for packages...")
    authors_per_package = {}
    for package, package_info in packages_data.items():
        if package_info.get("compare_message") == "COMPARE":
            tag1_chosen = package_info.get("chosen_v1")
            tag2_chosen = package_info.get("chosen_v2")
            data = cache_manager.commit_comparison_cache.get_authors_from_tags(package, tag1_chosen, tag2_chosen)
            if not data:
                # Cache miss, get authors from GitHub
                data = get_authors_from_tags(tag1_chosen, tag2_chosen, package, package_info)
                cache_manager.commit_comparison_cache.cache_authors_from_tags(package, tag1_chosen, tag2_chosen, data)
            authors_per_package[package] = data

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
    release_version_sha = cache_manager.github_cache.get_tag_to_sha(repo_name, release_version)
    if not release_version_sha:
        get_release_v_api = f"https://api.github.com/repos/{repo_name}/git/ref/tags/{release_version}"
        response = requests.get(get_release_v_api, headers=headers)
        if response.status_code == 200:
            response_json = response.json()
            release_version_sha = response_json.get("object").get("sha")
        else:
            release_version_sha = None
        cache_manager.github_cache.cache_tag_to_sha(
            repo_name, release_version, "No release found" if release_version_sha is None else release_version_sha
        )
    elif release_version_sha == "No release found":
        release_version_sha = None

    authors_per_patches = {}
    for changed_patch, details in patch_data.items():
        authors_info = []
        path = details.get("patch_file_path")
        if path is None:
            authors_per_patches[changed_patch] = {
                "patch_file_path": path,
                "repo_name": repo_name,
                "api": None,
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

        data = cache_manager.commit_comparison_cache.get_patch_authors(repo_name, path, release_version_sha)
        if not data:
            # Cache miss, get authors from GitHub
            data = get_patch_authors(repo_name, changed_patch, path, release_version_sha, headers)
            cache_manager.commit_comparison_cache.cache_patch_authors(repo_name, path, release_version_sha, data)
        authors_per_patches[changed_patch] = data

    return authors_per_patches


def get_commit_results(api_headers, repo_name, release_version, patch_data, packages_data):
    cache_manager._setup_requests_cache(cache_name="compare_commits")
    authors_per_patches_result = get_patch_commits(api_headers, repo_name, release_version, patch_data)
    authors_per_package_result = get_commit_authors(packages_data)
    commit_results = {**authors_per_patches_result, **authors_per_package_result}

    return commit_results
