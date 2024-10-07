import requests
import json
import argparse
import logging
import os

import extract_deps
import github_repo
import static_analysis
import compare_packages
import compare_commits
import get_user_commit_info
import get_pr_info
import get_pr_review
import tool_config
import report_static
import report_diff


github_token = os.getenv("GITHUB_API_TOKEN")
if not github_token:
    raise ValueError(
        "GitHub API token(GITHUB_API_TOKEN) is not set in the environment variables."
    )

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json",
}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--wallet-repo-name",
        required=True,
        help="Specify the wallet repository name. Example: MetaMask/metamask-extension",
    )
    parser.add_argument(
        "-v",
        "--release-version-old",
        required=True,
        help="The old release tag of the wallet repository. Example: v10.0.0",
    )
    parser.add_argument(
        "-vn",
        "--release-version-new",
        help="The new release version of the wallet repository.",
    )
    parser.add_argument(
        "-s",
        "--static-analysis",
        required=True,
        action="store_true",
        help="Run static analysis and generate a markdown report of the project",
    )
    parser.add_argument(
        "-d",
        "--differential-analysis",
        action="store_true",
        help="Run diffenretial analysis and generate a markdown report of the project",
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
        choices=["yarn-classic", "yarn-berry", "pnpm"],
    )

    args = parser.parse_args()

    return args


def logging_setup(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        filemode="w",
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_lockfile(wallet_repo_name, release_version, package_manager):
    tool_config.setup_cache("demo")
    # logging.info("Cache [demo_cache] setup complete")

    logging.info(f"Getting lockfile for {wallet_repo_name}@{release_version}")
    logging.info(f"Package manager: {package_manager}")

    print(f"Getting lockfile for {wallet_repo_name}@{release_version}")

    if package_manager == "yarn-classic" or package_manager == "yarn-berry":
        lockfile_name = "yarn.lock"
    elif package_manager == "pnpm":
        lockfile_name = "pnpm-lock.yaml"
    else:
        raise ValueError("Invalid package manager.")

    response = requests.get(
        f"https://api.github.com/repos/{wallet_repo_name}/contents/{lockfile_name}?ref={release_version}",
        headers=headers,
    )

    if response.status_code == 200:
        data = response.json()
        download_url = data.get("download_url")
        yarn_lock_content = requests.get(download_url).text
        print("Yarn.lock file is downloaded.")
    else:
        raise ValueError("Failed to get yarn.lock.")

    repo_branch_api = f"https://api.github.com/repos/{wallet_repo_name}"
    repo_branch_response = requests.get(repo_branch_api, headers=headers)

    if repo_branch_response.status_code == 200:
        data = repo_branch_response.json()
        default_branch = data["default_branch"]
        logging.info(f"{default_branch} is the default branch of {wallet_repo_name}.")
    else:
        raise ValueError("Failed to get default branch")

    return yarn_lock_content, default_branch, wallet_repo_name


def get_deps(folder_path, wallet_repo_name, release_version, package_manager):
    patches_info = None
    logging.info(f"Getting dependencies for {wallet_repo_name}@{release_version}...")

    # if it is a pnpm monorepo
    if package_manager == "pnpm":
        deps_list_all = extract_deps.extract_deps_from_pnpm_mono(
            folder_path, release_version
        )

    # extract deps from lockfile
    else:
        yarn_file, _, _ = get_lockfile(
            wallet_repo_name, release_version, package_manager
        )
        if package_manager == "yarn-classic":
            deps_list_all = extract_deps.extract_deps_from_v1_yarn(yarn_file)
        elif package_manager == "yarn-berry":
            deps_list_all = deps_list_all = extract_deps.extract_deps_from_yarn_berry(
                yarn_file
            )
            patches_info = extract_deps.get_pacthes_info(yarn_file)

    logging.info(
        f"Number of dependencies: {len(deps_list_all.get('resolutions', {}))} "
    )
    logging.info(f"Number of patches: {len(deps_list_all.get('patches', {}))} ")
    logging.info(
        f"Number of workspace dependencies: {len(deps_list_all.get('workspace', {}))} "
    )

    # dep with different resolutions for further analysis
    dep_with_many_versions = extract_deps.deps_versions(deps_list_all)
    logging.info(
        f"Number of dependencies with different resolutions: {len(dep_with_many_versions)}"
    )

    rv_name = release_version.replace("/", "_")

    write_to_file(f"{rv_name}_deps_list_all.json", folder_path, deps_list_all)
    write_to_file(
        f"{rv_name}_dep_with_many_versions.json", folder_path, dep_with_many_versions
    )
    write_to_file(f"{rv_name}_patches_info.json", folder_path, patches_info)

    return deps_list_all, dep_with_many_versions, patches_info


def static_analysis_all(
    folder_path, wallet_repo_name, release_version, package_manager, check_match=False
):
    deps_list, dep_with_many_versions, patches_info = get_deps(
        folder_path, wallet_repo_name, release_version, package_manager
    )
    repo_url_info = github_repo.get_github_repo_url(
        folder_path, deps_list, package_manager
    )

    static_results, errors = static_analysis.get_static_data(
        folder_path, repo_url_info, check_match=check_match
    )
    logging.info(f"Errors: {errors}")

    rv_name = release_version.replace("/", "_")
    write_to_file(f"{rv_name}_repo_info.json", folder_path, repo_url_info)

    return static_results, deps_list, dep_with_many_versions, patches_info


def differential_analysis(
    new_release_version,
    old_rv_dep_versions,
    new_rv_dep_versions,
    SA_1,
    SA_2,
    patches_new,
    patches_old,
    wallet_repo_name,
):
    logging.info("Running differential analysis...")

    (
        compare_differences,
        differences_pkg_full,
        downgraded_pkg,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        no_change_pkg,
    ) = compare_packages.differential(
        old_rv_dep_versions, new_rv_dep_versions, SA_1, SA_2
    )

    changed_patches, _ = compare_packages.changed_patch(patches_old, patches_new)

    authors = compare_commits.get_commit_results(
        headers,
        wallet_repo_name,
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
    file_path = os.path.join(directory, filename)

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def main():
    args = get_args()

    wallet_repo_name = args.wallet_repo_name
    release_version_old = args.release_version_old
    release_version_new = args.release_version_new
    check_match = args.name_match
    package_manager = args.package_manager

    release_version_old_name = release_version_old.replace("/", "_")
    release_version_new_name = (
        release_version_new.replace("/", "_") if release_version_new else None
    )

    dir_path = tool_config.PathManager()
    result_folder_path, json_directory, diff_folder = dir_path.create_folders(
        release_version_old_name
    )

    log_file_path = result_folder_path / "log_file.log"
    logging_setup(log_file_path)

    # Static Analysis
    static_results_old, deps_list_old, dep_with_many_versions_old, patches_info_old = (
        static_analysis_all(
            json_directory,
            wallet_repo_name,
            release_version_old,
            package_manager,
            check_match,
        )
    )

    write_to_file(
        f"{release_version_old_name}_static_results.json",
        json_directory,
        static_results_old,
    )

    file1_summary = result_folder_path / f"{release_version_old_name}_static_summary.md"

    # generate static analysis report for old release
    logging.info(f"Generating static analysis report for {release_version_old_name}...")
    report_static.get_s_summary(
        static_results_old,
        wallet_repo_name,
        release_version_old,
        summary_filename=file1_summary,
    )

    if release_version_new:
        json_directory_new = result_folder_path / "details" / release_version_new_name
        json_directory_new.mkdir(parents=True, exist_ok=True)

        (
            static_results_new,
            deps_list_new,
            dep_with_many_versions_new,
            patches_info_new,
        ) = static_analysis_all(
            json_directory_new,
            wallet_repo_name,
            release_version_new,
            package_manager,
            check_match,
        )
        write_to_file(
            f"{release_version_new_name}_static_results.json",
            json_directory,
            static_results_new,
        )

        file2_summary = (
            result_folder_path / f"{release_version_new_name}_static_summary.md"
        )

        # generate static analysis report for new release
        logging.info(
            f"Generating static analysis report for {release_version_new_name}..."
        )
        report_static.get_s_summary(
            static_results_new,
            wallet_repo_name,
            release_version_new,
            summary_filename=file2_summary,
        )

    if release_version_old and release_version_new and args.differential_analysis:
        (
            compare_differences_pkg,
            diff_downgraded_pkg,
            diff_upgraded_pkg,
            diff_compare_all_info,
        ) = differential_analysis(
            release_version_new,
            dep_with_many_versions_old,
            dep_with_many_versions_new,
            static_results_old,
            static_results_new,
            patches_info_new,
            patches_info_old,
            wallet_repo_name,
        )

        write_to_file(
            "compare_differences_pkg.json", diff_folder, compare_differences_pkg
        )
        write_to_file("downgraded_pkg.json", diff_folder, diff_downgraded_pkg)
        write_to_file("upgraded_pkg.json", diff_folder, diff_upgraded_pkg)
        write_to_file("compare_prr_infos.json", diff_folder, diff_compare_all_info)

        diff_summary = (
            result_folder_path
            / f"{release_version_old_name}_{release_version_new_name}_diff_summary.md"
        )

        # generate differential analysis report
        logging.info("Generating differential analysis report...")
        report_diff.generate_diff_report(
            diff_compare_all_info,
            wallet_repo_name,
            release_version_old_name,
            release_version_new_name,
            diff_summary,
        )


if __name__ == "__main__":
    args = get_args()
    main()
    print("Analysis completed.")
