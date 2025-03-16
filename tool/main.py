"""
Main file to run the software supply chain smell analysis.
"""

import json
import argparse
import logging
import os
import sys
import requests
from git import Repo

# Allows for tool to be recognized as a package to import from
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool import extract_deps
from tool import github_repo
from tool import static_analysis
from tool import compare_packages
from tool import compare_commits
from tool import get_user_commit_info
from tool import get_pr_info
from tool import get_pr_review
from tool import tool_config
from tool import report_static
from tool import report_diff

github_token = os.getenv("GITHUB_API_TOKEN")
if not github_token:
    raise ValueError("GitHub API token(GITHUB_API_TOKEN) is not set in the environment variables.")

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}

cache_manager = tool_config.get_cache_manager()


def get_args():
    """
    Get command line arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--project-repo-name",
        required=True,
        help="Specify the project repository name. Example: MetaMask/metamask-extension",
    )
    parser.add_argument(
        "-v",
        "--release-version-old",
        required=False,
        default="HEAD",
        help="The old release tag of the project repository. Defaults to HEAD. Example: v10.0.0",
    )
    parser.add_argument(
        "-vn",
        "--release-version-new",
        help="The new release version of the project repository.",
    )
    parser.add_argument(
        "-d",
        "--differential-analysis",
        action="store_true",
        help="Run differential analysis and generate a markdown report of the project",
    )
    parser.add_argument(
        "-n",
        "--name-match",
        action="store_true",
        help="Compare the package names with the name in the in the package.json file. This option will slow down the execution time due to the API rate limit of code search.",
    )
    parser.add_argument(
        "-pm",
        "--package-manager",
        required=True,
        help="The package manager used in the project.",
        choices=["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    )
    parser.add_argument(
        "--pnpm-scope",
        required=False,
        help="Extract dependencies from pnpm with a specific scope using 'pnpm list --filter <scope> --depth Infinity' command. Configure the scope in tool_config.py file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode.",
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file (JSON)",
        type=str,
        required=False,
    )

    # Gradual report group -- mutually exclusive, preserves backward compatibility for --no-gradual-report
    gradual_report_group = parser.add_mutually_exclusive_group()
    gradual_report_group.add_argument(
        "--gradual-report",
        dest="gradual_report",
        type=lambda x: str(x).lower() in ["true", "1", "yes", "y"],
        default=True,
        help="Enable/disable gradual reporting (default: true)",
    )
    gradual_report_group.add_argument(
        "--no-gradual-report",
        dest="gradual_report",
        action="store_false",
        help="Disable gradual reporting (deprecated, use --gradual-report=false instead)",
    )

    # Add new smell check arguments
    smell_group = parser.add_argument_group("smell checks")
    smell_group.add_argument(
        "--check-source-code",
        action="store_true",
        help="Check for dependencies with no link to source code repositories",
    )
    smell_group.add_argument(
        "--check-source-code-sha",
        action="store_true",
        help="Check for dependencies with no commit sha/tag for release",
    )
    smell_group.add_argument(
        "--check-deprecated",
        action="store_true",
        help="Check for deprecated dependencies",
    )
    smell_group.add_argument(
        "--check-forks",
        action="store_true",
        help="Check for dependencies that are forks",
    )
    smell_group.add_argument(
        "--check-provenance",
        action="store_true",
        help="Check for dependencies with no build attestation",
    )
    smell_group.add_argument(
        "--check-code-signature",
        action="store_true",
        help="Check for dependencies with missing/invalid code signature",
    )
    smell_group.add_argument(
        "--check-aliased-packages",
        action="store_true",
        help="Check for aliased packages",
    )

    arguments = parser.parse_args()

    return arguments


def get_lockfile(project_repo_name, release_version, package_manager):
    """
    Get the lockfile for the given project and release version.

    Args:
        project_repo_name (str): The name of the project repository.
        release_version (str): The release version of the project.
        package_manager (str): The package manager used in the project.

    Returns:
        str: The content of the lockfile or pom.xml.
        str: The default branch of the project.
        str: The name of the project repository.
    """

    LOOKING_FOR = {
        "yarn-classic": "yarn.lock",
        "yarn-berry": "yarn.lock",
        "pnpm": "pnpm-lock.yaml",
        "npm": "package-lock.json",
        "maven": "pom.xml",
    }

    cache_manager._setup_requests_cache(cache_name="get_lockfile")
    try:
        lockfile_name = LOOKING_FOR[package_manager]
        logging.info(f"Getting {lockfile_name} for {project_repo_name}@{release_version}")
        logging.info(f"Package manager: {package_manager}")
    except KeyError:
        logging.error("Invalid package manager or lack of lockfile: %s", package_manager)
        raise ValueError("Invalid package manager or lack of lockfile.")

    file_url = f"https://api.github.com/repos/{project_repo_name}/contents/{lockfile_name}?ref={release_version}"
    response = requests.get(file_url, headers=headers, timeout=20)

    if response.status_code == 200:
        data = response.json()
        download_url = data.get("download_url")
        lock_content = requests.get(download_url, timeout=60).text
        logging.info(f"Got the {lockfile_name} file from {download_url}.")
    else:
        logging.error(f"Failed to get {lockfile_name}.")
        raise ValueError(f"Failed to get {lockfile_name}.")

    repo_branch_api = f"https://api.github.com/repos/{project_repo_name}"
    repo_branch_response = requests.get(repo_branch_api, headers=headers, timeout=20)

    if repo_branch_response.status_code == 200:
        data = repo_branch_response.json()
        default_branch = data["default_branch"]
        logging.info("%s is the default branch of %s.", default_branch, project_repo_name)
    else:
        raise ValueError("Failed to get default branch")

    return lock_content, default_branch, project_repo_name


def get_deps(folder_path, project_repo_name, release_version, package_manager):
    """
    Get the dependencies for the given project and release version.

    Args:
        folder_path (str): The path to the project folder.
        project_repo_name (str): The name of the project repository.
        release_version (str): The release version of the project.
        package_manager (str): The package manager used in the project.
    """
    patches_info = None
    deps_list_all = None

    logging.info("Getting dependencies for %s@%s...", project_repo_name, release_version)

    # if it is a pnpm monorepo
    if package_manager == "pnpm":
        if get_args().pnpm_scope:
            pnpm_scope = get_args().pnpm_scope
            deps_list_all = extract_deps.extract_deps_from_pnpm_mono(
                folder_path, release_version, project_repo_name, pnpm_scope
            )
        else:
            yaml_lockfile, _, _ = get_lockfile(project_repo_name, release_version, package_manager)
            deps_list_all = extract_deps.extract_deps_from_pnpm_lockfile(project_repo_name, yaml_lockfile)

    # extract deps from lockfile
    elif package_manager == "yarn-classic" or package_manager == "yarn-berry":
        yarn_file, _, _ = get_lockfile(project_repo_name, release_version, package_manager)
        if package_manager == "yarn-classic":
            deps_list_all = extract_deps.extract_deps_from_v1_yarn(project_repo_name, yarn_file)
        elif package_manager == "yarn-berry":
            deps_list_all = deps_list_all = extract_deps.extract_deps_from_yarn_berry(project_repo_name, yarn_file)
            patches_info = extract_deps.get_patches_info(project_repo_name, yarn_file)

    elif package_manager == "npm":
        npm_file, _, _ = get_lockfile(project_repo_name, release_version, package_manager)
        deps_list_all = extract_deps.extract_deps_from_npm(project_repo_name, npm_file)

    elif package_manager == "maven":
        # Maven is more complex, because of child packages in the repo/pom; this requires to clone the whole repo
        # TODO: Issue: not sure if this works with child projects -- probably not?
        # Example: parent package A has a child package B; we want to run it on package B, but cloning won't work here (?)
        # And even if it did, we still need to, inside the project, navigate to the child package and run the analysis there
        # So this is a side case not yet handled
        repo_path = tool_config.clone_repo(project_repo_name, release_version)
        deps_list_all = extract_deps.extract_deps_from_maven(repo_path)

    logging.info("Number of dependencies: %d", len(deps_list_all.get("resolutions", {})))
    logging.info("Number of patches: %d", len(deps_list_all.get("patches", {})))
    logging.info("Number of aliased packages: %d", len(deps_list_all.get("aliased_packages", {})))
    logging.info("Number of workspace dependencies: %d", len(deps_list_all.get("workspace", {})))

    # dep with different resolutions for further analysis
    dep_with_many_versions = extract_deps.deps_versions(deps_list_all)
    logging.info(
        "Number of dependencies with different resolutions: %d",
        len(dep_with_many_versions),
    )

    return deps_list_all, dep_with_many_versions, patches_info


def static_analysis_all(
    folder_path,
    project_repo_name,
    release_version,
    package_manager,
    check_match=False,
    enabled_checks=None,
    config=None,
):
    """
    Perform static analysis on the given project and release version.

    Args:
        folder_path (str): The path to the project folder.
        project_repo_name (str): The name of the project repository.
        release_version (str): The release version of the project.
        package_manager (str): The package manager used in the project.
        check_match (bool): Whether to check for package name matches.
        enabled_checks (dict): Dictionary of enabled smell checks.
        config (dict): Configuration dictionary
    """
    deps_list, dep_with_many_versions, patches_info = get_deps(
        folder_path, project_repo_name, release_version, package_manager
    )
    repo_url_info = github_repo.get_github_repo_url(folder_path, deps_list, package_manager)

    static_results, errors = static_analysis.get_static_data(
        folder_path,
        repo_url_info,
        package_manager,
        check_match=check_match,
        enabled_checks=enabled_checks,
        config=config,
    )
    logging.info("Errors: %s", errors)

    return static_results, deps_list, dep_with_many_versions, patches_info


def differential_analysis(
    new_release_version,
    old_rv_dep_versions,
    new_rv_dep_versions,
    sa_1,
    sa_2,
    patches_new,
    patches_old,
    project_repo_name,
    package_manager,
):
    """
    Perform differential analysis on the given project and release versions.

    Args:
        new_release_version (str): The new release version of the project.
        old_rv_dep_versions (dict): The dependencies for the old release version.
        new_rv_dep_versions (dict): The dependencies for the new release version.
        sa_1 (dict): The static analysis results for the old release version.
        sa_2 (dict): The static analysis results for the new release version.
        patches_new (dict): The patches info for the new release version.
        patches_old (dict): The patches info for the old release version.
        project_repo_name (str): The name of the project repository.
        package_manager (str): The package manager used in the project.
    Returns:
        tuple: A tuple containing the following:
            - compare_differences (dict): The comparison results for the dependencies.
            - downgraded_pkg (dict): The downgraded packages.
            - upgraded_pkg (dict): The upgraded packages.
            - all_compare_info (dict): The comparison results for the PRs.
    """

    logging.info("Running differential analysis...")

    (
        compare_differences,
        differences_pkg_full,
        downgraded_pkg,
        _,
        _,
        upgraded_pkg,
        _,
    ) = compare_packages.differential(old_rv_dep_versions, new_rv_dep_versions, sa_1, sa_2)

    if package_manager != "maven":
        changed_patches, _ = compare_packages.changed_patch(patches_old, patches_new)
    else:
        changed_patches = {}

    authors = compare_commits.get_commit_results(
        headers,
        project_repo_name,
        new_release_version,
        changed_patches,
        differences_pkg_full,
    )

    commit_results = get_user_commit_info.get_user_first_commit_info(authors)

    useful_pr_infos = get_pr_info.get_useful_pr_info(commit_results)

    all_compare_info = get_pr_review.get_pr_review_info(useful_pr_infos)

    return (
        compare_differences,
        downgraded_pkg,
        upgraded_pkg,
        all_compare_info,
    )


def write_to_file(filename, directory, data):
    """
    Write data to a JSON file.

    Args:
        filename (str): The name of the file to write to.
        directory (str): The directory to write the file to.
        data (dict): The data to write to the file.
    """
    file_path = os.path.join(directory, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def setup_project_info(args, any_check_specified):
    """Set up project information based on command-line arguments."""

    return {
        "repo_name": args.project_repo_name,
        "old_version": args.release_version_old,
        "new_version": args.release_version_new,
        "old_version_name": args.release_version_old.replace("/", "_"),
        "new_version_name": (args.release_version_new.replace("/", "_") if args.release_version_new else None),
        "check_match": args.name_match,
        "package_manager": args.package_manager,
        "pnpm_scope": args.pnpm_scope,
        "debug": args.debug,
        "gradual_report": args.gradual_report and not any_check_specified,
    }


def setup_directories_and_logging(project_info):
    """Set up necessary directories and logging."""

    dir_path = tool_config.PathManager()
    result_folder_path, json_directory, diff_folder = dir_path.create_folders(project_info["old_version_name"])
    project_info["result_folder_path"] = result_folder_path
    project_info["json_directory"] = json_directory
    project_info["diff_folder"] = diff_folder

    log_file_path = result_folder_path / "analysis.log"
    tool_config.setup_logger(log_file_path, project_info["debug"])


def perform_static_analysis(project_info, is_old_version):
    """Perform static analysis for a given version."""

    version = project_info["old_version"] if is_old_version else project_info["new_version"]
    version_name = project_info["old_version_name"] if is_old_version else project_info["new_version_name"]
    json_dir = (
        project_info["json_directory"]
        if is_old_version
        else (project_info["result_folder_path"] / "details" / version_name)
    )

    if not is_old_version:
        json_dir.mkdir(parents=True, exist_ok=True)

    results = static_analysis_all(
        json_dir,
        project_info["repo_name"],
        version,
        project_info["package_manager"],
        project_info["check_match"],
        project_info["enabled_checks"],
        project_info["config"],
    )

    write_to_file(
        f"{version_name}_static_results.json",
        project_info["json_directory"],
        results[0],
    )

    return results


def generate_static_report(analysis_results, project_info, is_old_version):
    """Generate static analysis report."""
    version = project_info["old_version"] if is_old_version else project_info["new_version"]
    version_name = project_info["old_version_name"] if is_old_version else project_info["new_version_name"]

    summary_file = project_info["result_folder_path"] / f"{version_name}_static_summary.md"

    logging.info("Generating static analysis report for %s", version_name)
    report_static.get_s_summary(
        analysis_results[0],  # static analysis results
        analysis_results[1],  # deps_list
        project_info["repo_name"],
        version,
        project_info["package_manager"],
        project_info["enabled_checks"],
        project_info["gradual_report"],
        summary_filename=summary_file,
    )


def perform_differential_analysis(old_results, new_results, project_info):
    """Perform and report differential analysis."""
    diff_results = differential_analysis(
        project_info["new_version"],
        old_results[2],
        new_results[2],  # dep_with_many_versions
        old_results[0],
        new_results[0],  # static_results
        new_results[3],
        old_results[3],  # patches_info
        project_info["repo_name"],
        project_info["package_manager"],
    )

    # Write differential analysis results to files
    for filename, data in zip(
        [
            "compare_differences_pkg.json",
            "downgraded_pkg.json",
            "upgraded_pkg.json",
            "compare_prr_infos.json",
        ],
        diff_results,
    ):
        write_to_file(filename, project_info["diff_folder"], data)

    # Generate differential analysis report
    diff_summary = (
        project_info["result_folder_path"]
        / f"{project_info['old_version_name']}_{project_info['new_version_name']}_diff_summary.md"
    )
    logging.info("Generating differential analysis report...")
    report_diff.generate_diff_report(
        diff_results[3],  # diff_compare_all_info
        project_info["repo_name"],
        project_info["old_version_name"],
        project_info["new_version_name"],
        project_info["gradual_report"],
        diff_summary,
    )


def main():
    """Main flow to run the software supply chain smell analysis."""
    dw_args = get_args()

    # Determine which checks are enabled
    enabled_checks = {}
    any_check_specified = any(
        [
            dw_args.check_source_code,
            dw_args.check_source_code_sha,
            dw_args.check_deprecated,
            dw_args.check_forks,
            dw_args.check_provenance,
            dw_args.check_code_signature,
            dw_args.check_aliased_packages,
        ]
    )

    if any_check_specified:
        # Check if source code SHA or fork checks are enabled without source code
        if any([dw_args.check_source_code_sha, dw_args.check_forks]) and not dw_args.check_source_code:
            raise ValueError(
                "The --check-source-code-sha and --check-forks flags require --check-source-code to be enabled. "
                "These can only be checked if we can first verify the source code repository."
            )

        enabled_checks = {
            "source_code": dw_args.check_source_code,
            "source_code_sha": dw_args.check_source_code_sha,
            "deprecated": dw_args.check_deprecated,
            "forks": dw_args.check_forks,
            "provenance": dw_args.check_provenance,
            "code_signature": dw_args.check_code_signature,
            "aliased_packages": dw_args.check_aliased_packages,
        }
    else:
        # If no checks specified, enable all by default
        enabled_checks = {
            "source_code": True,
            "source_code_sha": True,
            "deprecated": True,
            "provenance": True,
            "code_signature": True,
            "aliased_packages": True,
        }

    project_info = setup_project_info(dw_args, any_check_specified)
    setup_directories_and_logging(project_info)
    project_info["config"] = tool_config.load_config(dw_args.config)

    logging.info(
        f"Software supply chain smells analysis for {project_info['repo_name']} for version {project_info['old_version']}..."
    )
    if project_info["gradual_report"]:
        logging.info("Gradual report generation is enabled.")

    # Pass enabled_checks to static analysis
    project_info["enabled_checks"] = enabled_checks

    old_analysis_results = perform_static_analysis(project_info, is_old_version=True)
    generate_static_report(old_analysis_results, project_info, is_old_version=True)

    if project_info["new_version"]:
        new_analysis_results = perform_static_analysis(project_info, is_old_version=False)
        generate_static_report(new_analysis_results, project_info, is_old_version=False)

        if dw_args.differential_analysis:
            perform_differential_analysis(old_analysis_results, new_analysis_results, project_info)


if __name__ == "__main__":
    main()
    logging.info("Analysis completed.")
