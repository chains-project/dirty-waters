import json
import os
import base64
import time
import urllib.parse
from tqdm import tqdm
import git

import requests
import subprocess
import re

from tool.tool_config import get_cache_manager, make_github_request
from tool.compare_commits import tag_format as construct_tag_format, find_existing_tags_batch
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
    "source_code_sha": True,
    "deprecated": True,
    "forks": False,
    "provenance": True,
    "code_signature": True,
    "aliased_packages": True,
}

SCHEMAS_FOR_CACHE_ANALYSIS = {
    "source_code": {
        "is_github": False,
        "github_api": "",
        "github_url": "",
        "github_exists": None,
        "github_redirected": None,
        "redirected_repo": "",
        "status_code": 200,
        "archived": None,
        "is_fork": None,
        "source_code_version": {
            "exists": None,
            "tag_version": "",
            "is_sha": None,
            "sha": "",
            "url": "",
            "message": "",
            "status_code": 404,
        },
        "parent_repo_link": "",
        "open_issues_count": 0,
        "error": "No error message.",
    },
    "package_info": {
        "package_only_name": "",
        "package_version": "",
        "deprecated_in_version": None,
        "provenance_in_version": None,
        "all_deprecated": None,
        "provenance_url": None,
        "provenance_info": None,
        "status_code": 200,
    },
    "code_signature": {
        "signature_present": None,
        "signature_valid": None,
    },
}


def update_package_info(package_info, field, new_data):
    # Also updates in place
    if field not in package_info:
        package_info[field] = {}
    package_info[field].update(new_data)
    return package_info


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
        logging.info(f"Code Signature match: {match}")
        if match:
            logging.info(f"Matched, signature match: {match.group(1)}")
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


def check_source_code_by_version(package_name, version, repo_api, repo_link, simplified_path, package_manager):
    def check_git_head_presence(package_name, version):
        # In NPM-based packages, the registry may contain a gitHead field in the package's metadata
        # Although it's not mandatory to have it, if it's present, it's the best way to check
        # the package's source code for the specific version
        try:
            response = requests.get(f"https://registry.npmjs.org/{package_name}/{version}", timeout=20)
            response.raise_for_status()
            data = response.json()
            git_head = data.get("gitHead", "")
            return git_head
        except requests.RequestException as e:
            logging.error(f"Error checking gitHead presence: {str(e)}")
            return False

    source_code_info = {
        "exists": False,
        "tag_version": version,
        "is_sha": False,
        "sha": None,
        "url": None,
        "message": "No tags found in the repo",
        "status_code": 404,
    }
    if package_manager in ["yarn-berry", "yarn-classic", "pnpm", "npm"]:
        if git_head := check_git_head_presence(package_name, version):
            # we check if the git_head is present in the git repo, using gitpython
            try:
                remote_refs = git.cmd.Git().ls_remote(repo_link)
                git_refs = [ref.split("\t")[0] for ref in remote_refs.split("\n") if ref]
                if git_head in git_refs:
                    logging.info(f"gitHead {git_head} found in {repo_link}")
                    return {
                        "exists": True,
                        "tag_version": version,
                        "is_sha": True,
                        "sha": git_head,
                        "url": None,
                        "message": "gitHead found in package metadata",
                        "status_code": 200,
                    }
                else:
                    logging.warning(f"gitHead {git_head} not found in {repo_link}, checking tags")
                    source_code_info = {
                        "exists": False,
                        "tag_version": version,
                        "is_sha": True,
                        "sha": git_head,
                        "url": None,
                        "message": f"gitHead {git_head} not found in {repo_link}",
                        "status_code": 404,
                    }
            except Exception as e:
                logging.error(f"Error checking gitHead in repo: {str(e)}")
        else:
            logging.warning(f"gitHead not found in {package_name} {version} metadata")
    else:
        logging.warning(
            f"Package manager {package_manager} not supported for gitHead checking, will proceed with tags"
        )

    have_no_tags_check_api = f"{repo_api}/tags"
    have_no_tags_response = requests.get(have_no_tags_check_api, headers=headers)
    have_no_tags_response_status_code = have_no_tags_response.status_code
    have_no_tags_data = have_no_tags_response.json()

    release_tag_exists = False
    if len(have_no_tags_data) == 0:
        logging.warning(f"No tags found for {package_name} in {repo_api}")
        release_tag_url = None
        message = "No tags found in the repo"
        status_code_release_tag = have_no_tags_response_status_code
    else:
        tag_possible_formats = construct_tag_format(version, package_name, repo_name=simplified_path)
        existing_tag_format = find_existing_tags_batch(tag_possible_formats, simplified_path)
        logging.info(f"Existing tag format: {existing_tag_format}")
        if existing_tag_format:
            existing_tag_format = existing_tag_format[0]
            release_tag_exists = True
            release_tag_url = f"{repo_api}/git/ref/tags/{existing_tag_format}"
            message = f"Tag {existing_tag_format} is found in the repo"
            status_code_release_tag = 200
        else:
            logging.warning(f"Tag {version} not found in {repo_api}")
            release_tag_url = None
            message = f"Tag {version} not found in the repo"
            status_code_release_tag = 404

    source_code_info.update(
        {
            "exists": release_tag_exists,
            "tag_version": version,
            "url": release_tag_url,
            "message": message,
            "status_code": status_code_release_tag,
        }
    )

    return source_code_info


def check_existence(package_name, repository, extract_message, package_manager):
    """Check if the package exists in the repository."""
    if "Could not find repository" in extract_message:
        return {"is_github": False, "github_url": "No_repo_info_found"}
    elif "Not a GitHub repository" in extract_message:
        return {"is_github": False, "github_url": repository}

    repo_api, simplified_path, package_full_name, _, version, error_message = api_constructor(package_name, repository)

    repo_link = f"https://github.com/{simplified_path}".lower()
    github_exists = False
    archived = False
    is_fork = False
    release_tag_exists = False
    release_tag_url = None
    message = None
    status_code_release_tag = None
    github_redirected = False
    now_repo_url = None
    open_issues_count = None
    status_code = 404

    data = make_github_request(repo_api, max_retries=3)
    parent_scm_result = {}
    source_code_info = None
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
        source_code_info = {
            "exists": release_tag_exists,
            "tag_version": version,
            "url": release_tag_url,
            "message": message,
            "status_code": status_code_release_tag,
        }
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

        source_code_info = check_source_code_by_version(
            package_full_name, version, repo_api, repo_link, simplified_path, package_manager
        )

    github_info = {
        "is_github": True,
        "github_api": repo_api,
        "github_url": repo_link,
        "github_exists": github_exists,
        "github_redirected": github_redirected,
        "redirected_repo": now_repo_url,
        "status_code": status_code,
        "archived": archived,
        "is_fork": is_fork,
        "source_code_version": source_code_info,
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


def analyze_package_data(
    package, repo_url, extract_message, pm, check_match=False, enabled_checks=DEFAULT_ENABLED_CHECKS
):
    """
    Analyze package data with configurable smell checks.

    Args:
        package: Package to analyze
        repo_url: Repository URL
        extract_message: Message from repository URL extraction - is it or not a GitHub repository
        pm: Package manager
        check_match: Whether to check name matches
        enabled_checks: Dictionary of enabled smell checks
    """

    def cached_analysis_matches_schema(cached_analysis, schema):
        for key, value in schema.items():
            if isinstance(value, dict):
                if key not in cached_analysis:
                    return False
                if not cached_analysis_matches_schema(cached_analysis[key], value):
                    return False
            elif key not in cached_analysis:
                return False
        return True

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
                    if check in ["source_code_sha", "forks"]:
                        check = "source_code"
                    elif check in ["deprecated", "provenance"]:
                        check = "package_info"
                    elif check == "aliased_packages":
                        continue
                    missing_checks[check] = not cached_analysis_matches_schema(
                        cached_analysis.get(check, {}), SCHEMAS_FOR_CACHE_ANALYSIS[check]
                    )

            if all(not missing for missing in missing_checks.values()):
                logging.info(f"Using complete cached analysis for {package}")
                return package_info
            logging.info(
                f"Found partial cached analysis for {package}, analyzing missing checks: {list(check for check, missing in missing_checks.items() if missing)}"
            )
        else:
            logging.info(f"No cached analysis for {package}, analyzing all enabled checks")
            for check, enabled in enabled_checks.items():
                if check in ["source_code_sha", "forks", "aliased_packages"]:
                    continue
                elif check in ["deprecated", "provenance"]:
                    check = "package_info"
                missing_checks[check] = enabled

        for check in missing_checks:
            if not missing_checks[check]:
                continue
            package_info[check] = SCHEMAS_FOR_CACHE_ANALYSIS[check].copy()

        if missing_checks.get("package_info"):
            package_infos = check_deprecated_and_provenance(package_name, package_version, pm)
            update_package_info(package_info, "package_info", package_infos)

        if missing_checks.get("code_signature"):
            update_package_info(
                package_info, "code_signature", check_code_signature(package_name, package_version, pm)
            )

        if missing_checks.get("source_code"):
            update_package_info(package_info, "source_code", check_existence(package, repo_url, extract_message, pm))

        if check_match and package_info.get("source_code") and package_info["source_code"].get("github_exists"):
            repo_url_to_use = package_info["source_code"].get("redirected_repo") or repo_url
            if package_info.get("provenance") == False:
                if (
                    package_info["source_code"].get("is_fork") == True
                    or package_info["source_code"].get("archived") == True
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


def disable_checks_from_config(package_name, config, enabled_checks):
    """
    Returns the enabled_checks dictionary for the package, based on the configuration file.
    config["ignore"] includes a series of entries (regex patterns) which specify which packages to ignore/do less checks on.
    We compare the package name against these patterns.
    If there are conflicting patterns, the first one that matches is used.

    Args:
        package_name (str): Name of the package
        config (dict): Configuration dictionary
        enabled_checks (dict): Dictionary of enabled checks

    Returns:
        dict: Package-specific enabled checks
    """
    if not config or "ignore" not in config:
        logging.warning("No config file provided, using default config (no packages ignored)")
        return enabled_checks

    ignore_patterns = config["ignore"]
    for pattern in ignore_patterns:
        if re.match(pattern, package_name):
            if isinstance(ignore_patterns[pattern], str):
                if ignore_patterns[pattern] == "all":
                    logging.info(f"Ignoring all checks for {package_name}")
                    return {}
            elif isinstance(ignore_patterns[pattern], list):
                for check in ignore_patterns[pattern]:
                    logging.info(f"Ignoring check {check} for {package_name}")
                    enabled_checks[check] = False
            else:
                logging.warning(f"Invalid ignore pattern for {package_name}: {ignore_patterns[pattern]}")
            break
    return enabled_checks


def get_static_data(folder, packages_data, pm, check_match=False, enabled_checks=DEFAULT_ENABLED_CHECKS, config=None):
    logging.info("Analyzing package static data...")
    package_all = {}
    errors = {}
    with tqdm(total=len(packages_data), desc="Analyzing packages") as pbar:
        for package, repo_urls in packages_data.items():
            logging.info(f"Currently analyzing {package}")

            enabled_checks = disable_checks_from_config(package, config, enabled_checks)
            if not enabled_checks:
                logging.warning(f"Package {package} will be skipped, no checks enabled for it")
                pbar.update(1)
                continue

            repo_url = repo_urls.get("url", "")
            extract_repo_url_message = repo_urls.get("message", "")
            command = repo_urls.get("command", None)
            analyzed_data = analyze_package_data(
                package, repo_url, extract_repo_url_message, pm, check_match=check_match, enabled_checks=enabled_checks
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
