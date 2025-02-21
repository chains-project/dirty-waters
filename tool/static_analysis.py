import json
import os
import base64
import time
import urllib.parse
from tqdm import tqdm

import requests
import subprocess
import re

from tool.tool_config import get_cache_manager, make_github_request
from tool.compare_commits import tag_format as construct_tag_format
import logging
import xmltodict

github_token = os.getenv("GITHUB_API_TOKEN")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}

cache_manager = get_cache_manager()


MAX_WAIT_TIME = 15 * 60

DEFAULT_ENABLED_CHECKS = {
    "source_code": True,
    "release_tags": True,
    "deprecated": True,
    "forks": True,
    "provenance": True,
    "code_signature": True,
}


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


def check_code_signature(package_name, package_version, pm):
    # TODO: find a package where we can check this, because with spoon everything is fine
    def check_maven_signature(package_name, package_version):
        # Construct the command
        command = f"mvn org.simplify4u.plugins:pgpverify-maven-plugin:1.18.2:show -Dartifact={package_name}:{package_version}"

        # Run the command
        output = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Regular expression to extract the PGP signature section
        pgp_signature_pattern = re.compile(r"PGP signature:\n(?:[ \t]*.+\n)*?[ \t]*status:\s*(\w+)", re.MULTILINE)
        match = pgp_signature_pattern.search(output.stdout)
        if match:
            # Extract the status
            status = match.group(1).strip().lower()
            return {"signature_present": True, "signature_valid": status == "valid"}

        # If no match is found, return no PGP signature present
        return {"signature_present": False, "signature_valid": False}

    def check_npm_signature(package, package_version):
        # NOTE: for future reference, NPM migrated from PGP signatures to ECDSA registry signatures
        # PGP-based registry signatures were deprecated on April 25th, 2023
        try:
            response = requests.get(f"https://registry.npmjs.org/{package}", timeout=20)
            response.raise_for_status()

            data = response.json()
            version_info = data.get("versions", {}).get(package_version, {})

            # Check for signature in dist metadata
            dist_info = version_info.get("dist", {})
            signatures = dist_info.get("signatures", [])

            if signatures:
                valid_signatures = [sig for sig in signatures if sig.get("keyid") and sig.get("sig")]
                return {"signature_present": True, "signature_valid": len(valid_signatures) > 0}

            return {"signature_present": False, "signature_valid": False}

        except requests.RequestException as e:
            logging.error(f"Error checking NPM signature: {str(e)}")
            return {"signature_present": False, "signature_valid": False}

    if pm == "maven":
        return check_maven_signature(package_name, package_version)
    elif pm in ("yarn-berry", "yarn-classic", "pnpm", "npm"):
        return check_npm_signature(package_name, package_version)
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
        package_name = package_name.replace("npm:", "")
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
        error_message = f"[INFO][api_constructor] Error: {str(e)}"
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"

    return repo_api, simplified_path, package_full_name, name, version, error_message


def check_parent_scm(package):
    name, version = package.split("@")
    group_id, artifact_id = name.split(":")

    existing_scm_data, repo_api, simplified_path, package_full_name = None, None, None, None
    stopping = False
    while not stopping:
        # First, getting the parent's pom contents
        command = [
            "mvn",
            "org.apache.maven.plugins:maven-help-plugin:3.5.1:evaluate",
            "-Dexpression=project.parent",
            f"-Dartifact={group_id}:{artifact_id}:{version}",
            "-q",
            "-DforceStdout",
        ]
        output = subprocess.run(command, capture_output=True, text=True)
        parent_pom = output.stdout.strip()
        if not parent_pom or "null" in parent_pom:
            # If there's no parent, we stop
            stopping = True
        else:
            parents_contents = xmltodict.parse(parent_pom)
            parent_group_id, parent_artifact_id = [
                parents_contents.get("project", {}).get("groupId", ""),
                parents_contents.get("project", {}).get("artifactId", ""),
            ]
            if not parent_group_id or not parent_artifact_id or parent_group_id != group_id:
                # If the parent is lacking data we stop;
                # If the parent doesn't share the same group, we went too far, so we stop too
                stopping = True
                break
            parent_scm_locations = [
                parents_contents.get("project", {}).get("scm", {}).get(location, "")
                for location in ["url", "connection", "developerConnection"]
            ] + [parents_contents.get("project", {}).get("url", "")]
            for location in parent_scm_locations:
                if location:
                    repo_api, simplified_path, package_full_name, _, _, _ = api_constructor(package, location)
                    data = make_github_request(repo_api, max_retries=3)
                    if data:
                        stopping = True
                        existing_scm_data = data
                        break
            if not stopping:
                group_id, artifact_id = parent_group_id, parent_artifact_id

    return {
        "data": existing_scm_data,
        "repo_api": repo_api,
        "simplified_path": simplified_path,
        "package_full_name": package_full_name,
    }


def check_existence(package_name, repository, package_manager):
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
    status_code = 404

    data = make_github_request(repo_api, max_retries=3)
    parent_scm_result = {}
    if not data:
        if package_manager == "maven":
            # There's the possibility of, in maven's case, assembly inheritance not having worked well;
            # As such, if the package manager is maven, we'll try to "work our way up", and perform the same check in the parent
            parent_scm_result = check_parent_scm(package_name)

    if not data and not parent_scm_result.get("data"):
        # simplified_path = parent_scm_result.get("simplified_path", simplified_path)
        # If we went up, and there's no still data, there really isn't a findable repository
        logging.warning(f"No repo found for {package_name} in {repo_link}")
        archived = None
        is_fork = None
        repo_link = f"https://github.com/{simplified_path}".lower()
    else:
        data = data or parent_scm_result["data"]
        simplified_path = parent_scm_result.get("simplified_path", simplified_path)
        repo_api = parent_scm_result.get("repo_api", repo_api)
        package_full_name = parent_scm_result.get("package_full_name", package_full_name)

        status_code = 200
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
            release_tag_url = None
            tag_related_info = "No tag was found in the repo"
            status_code_release_tag = have_no_tags_response_status_code
        else:
            tag_possible_formats = construct_tag_format(version, package_full_name, repo_name=simplified_path)
            # Making the default case not finding the tag
            tag_related_info = "The given tag was not found in the repo"
            if tag_possible_formats:
                for tag_format in tag_possible_formats:
                    tag_url = f"{repo_api}/git/ref/tags/{tag_format}"
                    response = make_github_request(tag_url, silent=True)
                    if response:
                        release_tag_exists = True
                        release_tag_url = tag_url
                        tag_related_info = f"Tag {tag_format} is found in the repo"
                        status_code_release_tag = 200
                        break
            if not release_tag_exists:
                logging.info(f"No tags found for {package_name} in {repo_api}")

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
        logging.error(f"Request error: {str(e)} for URL: {api}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)} for URL: {api}")
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
    cache_manager._setup_requests_cache(cache_name="static_analysis")

    _, repo_name, _, _, _, _ = api_constructor(package_name, repository)
    original_package_name = package_name.rsplit("@", 1)[0]

    query = f'"\\"name\\": \\"{original_package_name}\\""'
    repo = f"{repo_name}"

    encoded_search_term = urllib.parse.quote(query)
    encoded_repo = urllib.parse.quote(repo)

    url = f"https://api.github.com/search/code?q={encoded_search_term}+in:file+repo:{encoded_repo}"

    response = requests.get(url, headers=headers, timeout=20)

    # if not response.from_cache:
    #     time.sleep(6)

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


def analyze_package_data(package, repo_url, pm, check_match=False, enabled_checks=DEFAULT_ENABLED_CHECKS):
    """
    Analyze package data with configurable smell checks.

    Args:
        package: Package to analyze
        repo_url: Repository URL
        pm: Package manager
        check_match: Whether to check name matches
        enabled_checks: Dictionary of enabled smell checks
    """
    package_info = {}
    try:
        package_name, package_version = package.rsplit("@", 1)
        package_version = package_version.replace("npm:", "")

        # Try to get from cache first
        cached_analysis = cache_manager.package_cache.get_package_analysis(package_name, package_version, pm)

        # Initialize missing_checks to track what needs to be analyzed
        missing_checks = {}

        if cached_analysis:
            logging.info(f"Found cached analysis for {package}")
            package_info = cached_analysis

            # Check which enabled checks are missing from cache
            for check, enabled in enabled_checks.items():
                if enabled:
                    if check == "deprecated" and "deprecated" not in cached_analysis:
                        missing_checks["deprecated"] = True
                    elif check == "provenance" and "provenance" not in cached_analysis:
                        missing_checks["provenance"] = True
                    elif check == "code_signature" and "code_signature" not in cached_analysis:
                        missing_checks["code_signature"] = True
                    elif check == "source_code" and "github_exists" not in cached_analysis:
                        missing_checks["source_code"] = True
                    elif check == "forks" and (
                        "github_exists" not in cached_analysis
                        or "is_fork" not in cached_analysis.get("github_exists", {})
                    ):
                        missing_checks["forks"] = True

            if not missing_checks:
                logging.info(f"Using complete cached analysis for {package}")
                return package_info
            logging.info(
                f"Found partial cached analysis for {package}, analyzing missing checks: {list(missing_checks.keys())}"
            )
        else:
            logging.info(f"No cached analysis for {package}, analyzing all enabled checks")
            missing_checks = enabled_checks

        if missing_checks.get("deprecated") or missing_checks.get("provenance"):
            package_infos = check_deprecated_and_provenance(package_name, package_version, pm)
            if missing_checks.get("deprecated"):
                package_info["deprecated"] = package_infos.get("deprecated_in_version")
            if missing_checks.get("provenance"):
                package_info["provenance"] = package_infos.get("provenance_in_version")
            package_info["package_info"] = package_infos

        if missing_checks.get("code_signature"):
            package_info["code_signature"] = check_code_signature(package_name, package_version, pm)

        if missing_checks.get("source_code") or missing_checks.get("forks"):
            if "Could not find" in repo_url:
                package_info["github_exists"] = {"github_url": "No_repo_info_found"}
            elif "not github" in repo_url:
                package_info["github_exists"] = {"github_url": "Not_github_repo"}
            else:
                github_info = check_existence(package, repo_url, pm)
                package_info["github_exists"] = github_info

        if check_match and package_info.get("github_exists") and package_info["github_exists"].get("github_exists"):
            repo_url_to_use = github_info.get("redirected_repo") or repo_url
            if package_info.get("provenance") == False:
                if (
                    package_info["github_exists"].get("is_fork") == True
                    or package_info["github_exists"].get("archived") == True
                ):
                    package_info["match_info"] = check_name_match_for_fork(package, repo_url_to_use)
                else:
                    package_info["match_info"] = check_name_match(package, repo_url_to_use)
            else:
                package_info["match_info"] = {
                    "has_provenance": True,
                    "match": True,
                    "repo_name": repo_url,
                }

        # Cache the updated analysis
        cache_manager.package_cache.cache_package_analysis(package_name, package_version, pm, package_info)

    except Exception as e:
        logging.error(f"Analyzing package {package}: {str(e)}")
        package_info["error"] = str(e)

    return package_info


def get_static_data(folder, packages_data, pm, check_match=False, enabled_checks=DEFAULT_ENABLED_CHECKS):
    logging.info("Analyzing package static data...")
    package_all = {}
    errors = {}

    with tqdm(total=len(packages_data), desc="Analyzing packages") as pbar:
        for package, repo_urls in packages_data.items():
            logging.info(f"Currently analyzing {package}")
            repo_url = repo_urls.get("github", "")
            command = repo_urls.get("command", None)
            analyzed_data = analyze_package_data(
                package, repo_url, pm, check_match=check_match, enabled_checks=enabled_checks
            )
            error = analyzed_data.get("error", None)
            pbar.update(1)

            if error:
                errors[package] = error
            else:
                package_all[package] = analyzed_data
                package_all[package]["command"] = command

    return package_all, errors


def save_results_to_file(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
