import json
import os
import base64
import time
import urllib.parse
from tqdm import tqdm

import requests

import tool_config
from compare_commits import tag_format as construct_tag_format


github_token = os.getenv("GITHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}

# tool_config.setup_cache("static")


MAX_WAIT_TIME = 15 * 60


def check_deprecated_and_provenance(package, package_version, pm):
    """
    Check if the package is deprecated and if it has a provenance from the package manager's registry.
    """

    def check_npm(package, package_version):
        try:
            response = requests.get(f"https://registry.npmjs.org/{package}", timeout=20)

            response.raise_for_status()
        except requests.RequestException:
            return {
                "package_only_name": package,
                "package_version": package_version,
                "error": "Failed to fetch package data",
                "status_code": response.status_code if response else "No Response",
            }

        data = response.json()

        if_deprecated = False
        has_provenance = False
        provenance_url = None
        provenance_info = None
        all_deprecated = True

        version_info = data.get("versions", {}).get(package_version, {})
        all_versions = data.get("versions", {})

        deprecated_in_version = version_info.get("deprecated", "")
        provenance_in_version = version_info.get("dist", {}).get("attestations", "")

        if deprecated_in_version:
            if_deprecated = True

        if provenance_in_version:
            has_provenance = True
            provenance_url = provenance_in_version.get("url")
            provenance_info = provenance_in_version.get("provenance")

        for version in all_versions.values():
            if not version.get("deprecated"):
                all_deprecated = False
                break

        npm_package_info = {
            "package_only_name": package,
            "package_version": package_version,
            "deprecated_in_version": if_deprecated,
            "provenance_in_version": has_provenance,
            "all_deprecated": all_deprecated,
            "provenance_url": provenance_url,
            "provenance_info": provenance_info,
            "status_code": 200,
        }

        return npm_package_info

    def check_maven(package, package_version):
        return {
            "package_only_name": package,
            "package_version": package_version,
            "status_code": 404,
            "error": "Maven does not have a registry",
        }

    if pm in ("yarn-berry", "yarn-classic", "pnpm", "npm"):
        return check_npm(package, package_version)
    elif pm == "maven":
        # maven doesn't have this
        return check_maven(package, package_version)
    else:
        # log stuff
        # blow up
        logging.error(f"Package manager {pm} not supported.")


def api_constructor(package_name, repository):
    repo_url = repository.replace("https://", "").replace("http://", "").replace("/issues", "")

    # simplified_path = repo_url.replace("github.com/", "").split('#')[0].split('tree/master')[0].rstrip('/')
    simplified_path = (
        repo_url.replace("github.com:", "github.com/")
        .replace("github.com/", "")
        .split("#")[0]
        .split("/tree")[0]
        .rstrip("/")
    )

    if simplified_path.endswith(".git"):
        simplified_path = simplified_path[:-4]

    repo_api = f"https://api.github.com/repos/{simplified_path}"

    error_message = None

    try:
        parts = package_name.split("@")
        package_full_name = None
        name = None
        version = None

        if len(parts) > 2 or package_name.startswith("@"):
            package_full_name = f"@{parts[1]}"
            _, name = parts[1].split("/")  # scope,name
            version = parts[2]

        elif len(parts) == 2:
            if "/" in parts[1]:
                package_full_name = parts[0]
                scope, name = parts[0].split("/")
                version = parts[1]
            else:
                package_full_name = parts[0]
                name = parts[0]
                version = parts[1]

    except (ValueError, TypeError, AttributeError) as e:
        error_message = f"Error: {str(e)}"
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"

    return repo_api, simplified_path, package_full_name, name, version, error_message


def make_github_request(url, headers):
    """Make a GET request to the GitHub API."""

    response = requests.get(url, headers=headers)

    if response.status_code == 403 and int(response.headers.get("X-RateLimit-Remaining", 0)) <= 10:
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        sleep_time = min(reset_time - int(time.time()), MAX_WAIT_TIME)
        print(f"\nRate limit reached. Waiting for {sleep_time} seconds.")
        time.sleep(sleep_time)
        print("\nResuming analysis...")
        response = requests.get(url, headers=headers)
    return response


def check_existence(package_name, repository):
    """Check if the package exists in the repository."""
    repo_api, simplified_path, package_full_name, _, version, error_message = api_constructor(package_name, repository)

    repo_link = f"https://github.com/{simplified_path}".lower()
    github_exists = False
    archived = False
    is_fork = False
    release_tag_exists = False
    release_tag_url = None
    tag_related_info = None
    status_code_release_tag = None
    github_redirected = False
    now_repo_url = None
    open_issues_count = None

    response = make_github_request(repo_api, headers=headers)
    status_code = response.status_code
    data = response.json()

    if status_code != 200:
        print(f"Error: {data.get('message', 'No message')}")
        archived = None
        is_fork = None
        repo_link = f"https://github.com/{simplified_path}".lower()

    if status_code == 200:
        github_exists = True
        open_issues_count = data["open_issues"]
        if data["archived"]:
            archived = True
        if data["fork"]:
            is_fork = True
            # Get the parent repo link
            parent_repo_link = data.get("parent", {}).get("html_url", "")

        now_repo_url = data.get("html_url", "").lower()
        repo_link = f"https://github.com/{simplified_path}".lower()

        if now_repo_url != repo_link:
            github_redirected = True
        else:
            now_repo_url = None

        # check if the repo has any tags(to reduce the number of API requests)
        have_no_tags_check_api = f"{repo_api}/tags"
        have_no_tags_response = requests.get(have_no_tags_check_api, headers=headers)
        have_no_tags_response_status_code = have_no_tags_response.status_code
        have_no_tags_data = have_no_tags_response.json()

        if len(have_no_tags_data) == 0:
            release_tag_exists = False
            release_tag_url = None
            tag_related_info = "No tag found in the repo"
            status_code_release_tag = have_no_tags_response_status_code

        else:
            tag_possible_formats = construct_tag_format(version, package_full_name)

            if tag_possible_formats:
                for tag_format in tag_possible_formats:
                    tag_url = f"{repo_api}/git/ref/tags/{tag_format}"
                    response = make_github_request(tag_url, headers=headers)
                    if response.status_code == 200:
                        release_tag_exists = True
                        release_tag_url = tag_url
                        tag_related_info = f"Tag {tag_format} is found in the repo"
                        status_code_release_tag = response.status_code
                        break
                    else:
                        tag_related_info = "Tags are not found in the repo"
                        status_code_release_tag = response.status_code

    github_info = {
        "github_api": repo_api,
        "github_url": repo_link,
        "github_exists": github_exists,
        "github_redirected": github_redirected,
        "redirected_repo": now_repo_url,
        "status_code": status_code,
        "archived": archived,
        "is_fork": is_fork,
        "release_tag": {
            "exists": release_tag_exists,
            "tag_version": version,
            "url": release_tag_url,
            "tag_related_info": tag_related_info,
            "status_code": status_code_release_tag,
        },
        "parent_repo_link": parent_repo_link if is_fork else None,
        "open_issues_count": open_issues_count,
        "error": error_message if error_message else "No error message.",
    }

    return github_info


def get_api_content(api, headers):
    """
    Get the content of the API.
    """
    try:
        response = requests.get(api, headers=headers)
        response.raise_for_status()
        content = response.json()
        file_content = base64.b64decode(content["content"]).decode("utf-8")
        package_json = json.loads(file_content)
        return package_json

    except (
        requests.HTTPError,
        requests.ConnectionError,
        requests.Timeout,
        json.JSONDecodeError,
    ) as e:
        print(f"Request error: {str(e)} for URL: {api}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)} for URL: {api}")
        return None


def check_name_match_for_fork(package_name, repository):
    name_match = False
    unmatch_info = None

    repo_api, repo, _, pkg_only_name, _, _ = api_constructor(package_name, repository)
    fork_api_json_url = [
        f"{repo_api}/contents/package.json",
        f"{repo_api}/contents/contents/packages/{pkg_only_name}/package.json",
    ]

    fork_api_json = None
    api = ""
    status_code = None

    for api in fork_api_json_url:
        fork_api_response = requests.get(api, headers=headers, timeout=20)
        status_code = fork_api_response.status_code
        if status_code == 200:
            fork_api_json = fork_api_response.json()
            break

    if not fork_api_json:
        return {
            "repository": repository,
            "find_json_package": "",
            "repo_name": repo,
            "package_api_in_packages": api,
            "match": False,
            "unmatch_info": {
                "status_code": status_code,
                "reason": "API requests failed",
                "api_url": api,
            },
        }

    file_content = base64.b64decode(fork_api_json["content"]).decode("utf-8")
    package_json_file = json.loads(file_content)

    package_name_in_fork = package_json_file.get("name", "")
    if package_name_in_fork == package_name.rsplit("@", 1)[0]:
        name_match = True

    if not name_match:
        unmatch_info = {
            "status_code": status_code,
            "repo_name": repository,
            # 'total_count': search_results['total_count'],
            "package_name": package_name,
            "find_json_package": package_name_in_fork,
            "reason": "could not find",
            "api_url": api,
        }

    match_info = {
        "repository": repository,
        "find_json_package": package_name_in_fork,
        "package_name": package_name.rsplit("@", 1)[0],
        "repo_name": repo,
        "package_api_in_packages": api,
        "match": name_match,
        "unmatch_info": None if name_match else unmatch_info,
    }

    return match_info


def check_name_match(package_name, repository):
    tool_config.setup_cache("check_name")
    # logging.info("Cache [check_name_cache] setup complete")

    _, repo_name, _, _, _, _ = api_constructor(package_name, repository)
    original_package_name = package_name.rsplit("@", 1)[0]

    query = f'"\\"name\\": \\"{original_package_name}\\""'
    repo = f"{repo_name}"

    encoded_search_term = urllib.parse.quote(query)
    encoded_repo = urllib.parse.quote(repo)

    url = f"https://api.github.com/search/code?q={encoded_search_term}+in:file+repo:{encoded_repo}"

    response = requests.get(url, headers=headers, timeout=20)

    if not response.from_cache:
        time.sleep(6)

    status_code = response.status_code

    is_match = False
    unmatch_info = None
    package_api_in_packages = None

    if status_code != 200:
        search_results = None

    if status_code == 200:
        search_results = response.json()
        if search_results["total_count"] == 0:
            package_name = "can not find"

        else:
            for item in search_results["items"]:
                if item["name"] == "package.json":
                    package_api_in_packages = item["url"]
                    is_match = True

    else:
        is_match = False

    if not is_match:
        unmatch_info = {
            "status_code": status_code,
            "repo_name": repository,
            # 'total_count': search_results['total_count'],
            "package_name": package_name,
            "search_term": original_package_name,
            "query": query,
            "reason": "could not find",
            "api_url": url,
        }

    match_info = {
        "repository": repository,
        "find_json_package": package_api_in_packages,
        "repo_name": repo,
        "package_api_in_packages": package_api_in_packages,
        "match": is_match,
        "unmatch_info": None if is_match else unmatch_info,
    }

    return match_info


def analyze_package_data(package, repo_url, pm, check_match=False):
    package_info = {
        "deprecated": None,
        "provenance": None,
        "package_info": None,
        "github_exists": None,
        "match_info": None,
    }

    try:
        # TODO: check if this needs to be different because of differences between npm, maven, etc
        package_name, package_version = package.rsplit("@", 1)
        package_infos = check_deprecated_and_provenance(package_name, package_version, pm)
        package_info["deprecated"] = package_infos.get("deprecated_in_version")
        package_info["provenance"] = package_infos.get("provenance_in_version")
        package_info["package_info"] = package_infos

        if "Could not find" in repo_url:
            package_info["github_exists"] = {"github_url": "No_repo_info_found"}
        elif "not github" in repo_url:
            package_info["github_exists"] = {"github_url": "Not_github_repo"}
        else:
            github_info = check_existence(package, repo_url)
            package_info["github_exists"] = github_info
            if github_info.get("github_exists"):
                repo_url_to_use = github_info.get("redirected_repo") or repo_url
                if check_match:
                    # TODO: why do we only check this is provenance is false??
                    # TODO: maven currently not supported for this because of the above
                    if package_info["provenance"] == False:
                        if github_info.get("is_fork") == True or github_info.get("archived") == True:
                            package_info["match_info"] = check_name_match_for_fork(package, repo_url_to_use)
                        else:
                            package_info["match_info"] = check_name_match(package, repo_url_to_use)
                    else:
                        package_info["match_info"] = {
                            "has_provenance": True,
                            "match": True,
                            "repo_name": repo_url_to_use,
                        }

    except (ValueError, TypeError, AttributeError) as e:
        return None, {
            "error_type": type(e).__name__,
            "message": str(e),
            "repo_url": repo_url,
            "package": package,
            "package_info": package_info,
        }

    return package_info, None


def get_static_data(folder, packages_data, pm, check_match=False):
    print("Analyzing package static data...")
    package_all = {}
    errors = {}

    with tqdm(total=len(packages_data), desc="Analyzing packages") as pbar:
        for package, repo_urls in packages_data.items():
            # print(f"Analyzing {package}")
            tqdm.write(f"{package}")
            repo_url = repo_urls.get("github", "")
            analyzed_data, error = analyze_package_data(package, repo_url, pm, check_match=check_match)
            pbar.update(1)

            if error:
                errors[package] = error
            else:
                package_all[package] = analyzed_data

    # filepaths

    # file_path = os.path.join(folder, "all_info.json")
    # error_path = os.path.join(folder, "errors.json")

    # save_results_to_file(file_path, package_all)
    # save_results_to_file(error_path, errors)

    return package_all, errors


def save_results_to_file(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
