import re
import logging


def parse_dependencies(file_path):
    dependencies = {}
    with open(file_path, "r") as file:
        for line in file:
            if "@" in line:
                dep, version = line.strip().rsplit("@", 1)
                if dep in dependencies:
                    dependencies[dep].append(version)
                else:
                    dependencies[dep] = [version]

    return dependencies


def sort_versions(versions):
    def parse_version(v):
        try:
            major, minor, patch = map(int, v.split("."))
            return major, minor, patch
        except ValueError:
            return float("-inf"), v

    return sorted(versions, key=parse_version)


def compare_dependencies(deps1, deps2):
    logging.info("Comparing dependencies...")
    differences_pkg = {}
    all_deps = set(list(deps1.keys()) + list(deps2.keys()))

    # 1 is old, 2 is new
    for dep in all_deps:
        versions1 = deps1.get(dep, [])
        versions2 = deps2.get(dep, [])

        if versions1 and versions2:
            only_in_1 = set(versions1) - set(versions2)
            only_in_2 = set(versions2) - set(versions1)
            unchanged_in_1 = set(versions1) - only_in_1

            if only_in_1 or only_in_2:
                differences_pkg[dep] = {
                    "only_in_1": list(sort_versions(only_in_1)),
                    "only_in_2": list(sort_versions(only_in_2)),
                    "unchanged": list(sort_versions(unchanged_in_1)),
                    "version1": list(sort_versions(versions1)),
                    "version2": list(sort_versions(versions2)),
                }

        else:
            differences_pkg[dep] = {
                "version1": list(sort_versions(versions1)),
                "version2": list(sort_versions(versions2)),
            }

    return differences_pkg


def choose_compare_version(dep_file_1, dep_file_2):
    differences = compare_dependencies(dep_file_1, dep_file_2)

    for dep, versions in differences.items():
        differences[dep]["message"] = None
        if not versions.get("only_in_2"):
            chosen_v2 = None
            if versions.get("only_in_1") is not None:
                differences[dep]["message"] = f"Deleted package - version {versions.get('only_in_1')} deleted"

        else:
            chosen_v2 = versions["only_in_2"][-1]

        if not versions.get("only_in_1"):
            unchanged = versions.get("unchanged")
            if not unchanged:
                chosen_v1 = None
            else:
                chosen_v1 = versions.get("unchanged")[-1]
        else:
            chosen_v1 = versions["only_in_1"][-1]

        differences[dep]["chosen_v2"] = chosen_v2
        differences[dep]["chosen_v1"] = chosen_v1

    return differences


def is_version_greater(v1, v2):
    v1_nums = [int(num) for num in v1.split(".") if num.isdigit()]
    v2_nums = [int(num) for num in v2.split(".") if num.isdigit()]

    return v1_nums > v2_nums


def category_dependencies(dep_file_1, dep_file_2):
    differences = choose_compare_version(dep_file_1, dep_file_2)
    newly_added_pkg = {}
    deleted_pkg = {}
    upgraded_pkg = {}
    downgraded_pkg = {}
    no_change_pkg = {}

    for dep, versions in differences.items():
        v1, v2 = versions["chosen_v1"], versions["chosen_v2"]
        allv1, allv2 = versions["version1"], versions["version2"]

        if v1 is None or v2 is None:
            if not allv1:
                differences[dep]["message"] = "Newly added package"
                newly_added_pkg[dep] = {
                    "version1": allv1,
                    "version2": allv2,
                    "message": "Newly added package",
                }
            elif not allv2:
                differences[dep]["message"] = "Deleted package"
                deleted_pkg[dep] = {
                    "version1": allv1,
                    "version2": allv2,
                    "message": "Deleted package",
                }

        else:
            if is_version_greater(v2, v1):
                differences[dep]["message"] = "Upgraded package"
                upgraded_pkg[dep] = {
                    "version1": v1,
                    "version2": v2,
                    "message": "Upgraded package",
                }
            elif is_version_greater(v1, v2):
                differences[dep]["message"] = "Downgraded package"
                downgraded_pkg[dep] = {
                    "version1": v1,
                    "version2": v2,
                    "message": "Downgraded package",
                }
            else:
                differences[dep]["message"] = "No change"
                no_change_pkg[dep] = {
                    "version1": v1,
                    "version2": v2,
                    "message": "No change",
                }

    return (
        differences,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        downgraded_pkg,
        no_change_pkg,
    )


def get_repo_from_SA(dep_file_1, dep_file_2, SA_old, SA_new):
    (
        differences,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        downgraded_pkg,
        no_change_pkg,
    ) = category_dependencies(dep_file_1, dep_file_2)

    for dep, versions in differences.items():
        differences[dep]["v1_repo_accessibility"] = None
        differences[dep]["v2_repo_accessibility"] = None
        differences[dep]["v1_repo_link"] = None
        differences[dep]["v2_repo_link"] = None
        differences[dep]["repo_message"] = None
        differences[dep]["compare_message"] = None
        differences[dep]["repo"] = None
        differences[dep]["repo_name"] = None
        differences[dep]["repo_pure"] = None
        differences[dep]["v1_repo_directed"] = None
        differences[dep]["v2_repo_directed"] = None

        if versions["message"] == "Upgraded package":
            differences[dep]["category"] = "Upgraded package"

            dep_name_version_old = f"{dep}@{versions['chosen_v1']}"
            dep_name_version_new = f"{dep}@{versions['chosen_v2']}"

            dep_old_repo_url_accessibility = (
                SA_old.get(dep_name_version_old, {}).get("github_exists", {}).get("github_exists", None)
            )
            dep_new_repo_url_accessibility = (
                SA_new.get(dep_name_version_new, {}).get("github_exists", {}).get("github_exists", None)
            )

            if dep_old_repo_url_accessibility is True and dep_new_repo_url_accessibility is True:
                dep_old_repo_url = (
                    SA_old.get(dep_name_version_old, {}).get("github_exists", {}).get("github_url", "Error")
                )
                dep_new_repo_url = (
                    SA_new.get(dep_name_version_new, {}).get("github_exists", {}).get("github_url", "Error")
                )

                differences[dep]["v1_repo_accessibility"] = dep_old_repo_url_accessibility
                differences[dep]["v2_repo_accessibility"] = dep_new_repo_url_accessibility

                differences[dep]["v1_repo_link"] = dep_old_repo_url
                differences[dep]["v2_repo_link"] = dep_new_repo_url

                if dep_old_repo_url != dep_new_repo_url:
                    differences[dep]["repo_message"] = "Different repo link"
                    differences[dep]["compare_message"] = "DO NOT COMPARE"

                    check_directed_old = (
                        SA_old.get(dep_name_version_old, {}).get("github_exists", {}).get("github_redirected", None)
                    )
                    check_directed_new = (
                        SA_new.get(dep_name_version_new, {}).get("github_exists", {}).get("github_redirected", None)
                    )

                    differences[dep]["v1_repo_directed"] = check_directed_old
                    differences[dep]["v2_repo_directed"] = check_directed_new

                else:
                    pattern = r"(github.*)"
                    match1 = re.search(pattern, dep_old_repo_url, re.IGNORECASE)

                    v1_repo_url_pure = match1.group(1) if match1 else "not github"
                    v1_repo_url_clean = (
                        v1_repo_url_pure.replace("https://", "").replace("http://", "").replace("/issues", "")
                    )

                    match2 = re.search(pattern, dep_new_repo_url, re.IGNORECASE)

                    v2_repo_url_pure = match2.group(1) if match2 else "not github"
                    v2_repo_url_clean = (
                        v2_repo_url_pure.replace("https://", "").replace("http://", "").replace("/issues", "")
                    )

                    if v1_repo_url_clean == v2_repo_url_clean:
                        repo_name = (
                            v1_repo_url_clean.replace("github.com/", "")
                            .split("#")[0]
                            .split("tree/master")[0]
                            .rstrip("/")
                        )
                        if repo_name.endswith(".git"):
                            repo_name = repo_name[:-4]
                        differences[dep]["repo"] = dep_old_repo_url
                        differences[dep]["repo_name"] = repo_name
                        differences[dep]["repo_pure"] = v1_repo_url_pure
                        differences[dep]["compare_message"] = "COMPARE"
                        differences[dep]["repo_message"] = "Repo - ok"

                    else:
                        differences[dep]["repo_message"] = "Different repo name"
                        differences[dep]["compare_message"] = "DO NOT COMPARE"

            else:
                differences[dep]["compare_message"] = "DO NOT COMPARE"
                if dep_old_repo_url_accessibility is False or dep_old_repo_url_accessibility is None:
                    differences[dep]["v1_repo_accessibility"] = "Repo link not accessible"
                    differences[dep]["compare_message"] = "DO NOT COMPARE"

                if dep_new_repo_url_accessibility is False or dep_new_repo_url_accessibility is None:
                    differences[dep]["v2_repo_accessibility"] = "Repo link not accessible"
                    differences[dep]["compare_message"] = "DO NOT COMPARE"

        else:
            differences[dep]["compare_message"] = "DO NOT COMPARE"
            dep_name_version_old = f"{dep}@{versions['chosen_v1']}"
            dep_name_version_new = f"{dep}@{versions['chosen_v2']}"
            repo_1 = SA_old.get(dep_name_version_old, {}).get("github_exists", {}).get("github_url", "Error")
            repo_2 = SA_old.get(dep_name_version_old, {}).get("github_exists", {}).get("github_url", "Error")
            if repo_1 == repo_2 and repo_1 != "Error" and repo_2 != "Error":
                differences[dep]["repo_message"] = "Repo - ok"
                differences[dep]["repo"] = repo_1
            elif repo_1 != "Error":
                differences[dep]["repo"] = repo_1
            elif repo_2 != "Error":
                differences[dep]["repo"] = repo_2

            differences[dep]["category"] = versions["message"]

    return (
        differences,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        downgraded_pkg,
        no_change_pkg,
    )


def changed_patch(package_data_old, package_data_new):
    patches_change = {}
    no_change_patches = {}
    if package_data_old and package_data_new:
        common_patches = set(package_data_old.keys()) & set(package_data_new.keys())
        unique_patches_in_data2 = set(package_data_new.keys()) - set(package_data_old.keys())

        for new_patch in unique_patches_in_data2:
            patches_change[new_patch] = {
                "name": new_patch,
                "version": package_data_new[new_patch].get("version"),
                "patch_file_path": package_data_new[new_patch].get("patch_file_path"),
            }

        no_change_patches["No change patches"] = list(common_patches)
    else:
        patches_change["No packages patch found"] = {
            "name": None,
            "version": None,
            "patch_file_path": None,
        }
        no_change_patches["No change patches"] = []

    return patches_change, no_change_patches


def differential(dep_file_1, dep_file_2, SA_1, SA_2):
    compare_differences = choose_compare_version(dep_file_1, dep_file_2)

    (
        differences_pkg_full,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        downgraded_pkg,
        no_change_pkg,
    ) = get_repo_from_SA(dep_file_1, dep_file_2, SA_1, SA_2)

    return (
        compare_differences,
        differences_pkg_full,
        downgraded_pkg,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        no_change_pkg,
    )
