import re
import logging

MESSAGE_TO_VERSIONS_MAPPING = {
    "newly_added": "Newly added package",
    "deleted": "Deleted package",
    "upgraded": "Upgraded package",
    "downgraded": "Downgraded package",
    "no_change": "No change",
}


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
    def categorize_dependency(v1, v2, allv1, allv2):
        if v1 is None or v2 is None:
            if not allv1:
                return "newly_added", allv1, allv2
            elif not allv2:
                return "deleted", allv1, allv2
        else:
            if is_version_greater(v2, v1):
                return "upgraded", v1, v2
            elif is_version_greater(v1, v2):
                return "downgraded", v1, v2
            else:
                return "no_change", v1, v2
        return None

    differences = choose_compare_version(dep_file_1, dep_file_2)
    gathered_categories = {
        "newly_added": {},
        "deleted": {},
        "upgraded": {},
        "downgraded": {},
        "no_change": {},
    }

    for dep, versions in differences.items():
        v1, v2 = versions["chosen_v1"], versions["chosen_v2"]
        allv1, allv2 = versions["version1"], versions["version2"]

        categorized_dependency = categorize_dependency(v1, v2, allv1, allv2)
        if categorized_dependency:
            category, v1, v2 = categorized_dependency
            message = MESSAGE_TO_VERSIONS_MAPPING[category]
            differences[dep]["message"] = message
            gathered_categories[category][dep] = {
                "version1": v1,
                "version2": v2,
                "message": message,
            }

    return (
        differences,
        *gathered_categories.values(),
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
            # Check code signature changes
            signature_changes = compare_code_signatures(
                dep, versions["chosen_v1"], versions["chosen_v2"], SA_old, SA_new
            )
            differences[dep]["signature_changes"] = signature_changes

            # If there are signature changes, add it to the category
            if signature_changes["has_changes"]:
                differences[dep]["category"] = "Upgraded package with signature changes"

            dep_name_version_old = f"{dep}@{versions['chosen_v1']}"
            dep_name_version_new = f"{dep}@{versions['chosen_v2']}"

            dep_old_repo_url_accessibility = (
                SA_old.get(dep_name_version_old, {}).get("source_code", {}).get("github_exists", None)
            )
            dep_new_repo_url_accessibility = (
                SA_new.get(dep_name_version_new, {}).get("source_code", {}).get("github_exists", None)
            )

            if dep_old_repo_url_accessibility is True and dep_new_repo_url_accessibility is True:
                dep_old_repo_url = (
                    SA_old.get(dep_name_version_old, {}).get("source_code", {}).get("github_url", "Error")
                )
                dep_new_repo_url = (
                    SA_new.get(dep_name_version_new, {}).get("source_code", {}).get("github_url", "Error")
                )

                differences[dep]["v1_repo_accessibility"] = dep_old_repo_url_accessibility
                differences[dep]["v2_repo_accessibility"] = dep_new_repo_url_accessibility

                differences[dep]["v1_repo_link"] = dep_old_repo_url
                differences[dep]["v2_repo_link"] = dep_new_repo_url

                if dep_old_repo_url != dep_new_repo_url:
                    differences[dep]["repo_message"] = "Different repo link"
                    differences[dep]["compare_message"] = "DO NOT COMPARE"

                    check_directed_old = (
                        SA_old.get(dep_name_version_old, {}).get("source_code", {}).get("github_redirected", None)
                    )
                    check_directed_new = (
                        SA_new.get(dep_name_version_new, {}).get("source_code", {}).get("github_redirected", None)
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
            repo_1 = SA_old.get(dep_name_version_old, {}).get("source_code", {}).get("github_url", "Error")
            repo_2 = SA_old.get(dep_name_version_old, {}).get("source_code", {}).get("github_url", "Error")
            if repo_1 == repo_2 and repo_1 != "Error" and repo_2 != "Error":
                differences[dep]["repo_message"] = "Repo - ok"
                differences[dep]["repo"] = repo_1
            elif repo_1 != "Error":
                differences[dep]["repo"] = repo_1
            elif repo_2 != "Error":
                differences[dep]["repo"] = repo_2

            differences[dep]["category"] = versions["message"]

            if versions["message"] == "Downgraded package":
                # Check code signature changes
                signature_changes = compare_code_signatures(
                    dep, versions["chosen_v1"], versions["chosen_v2"], SA_old, SA_new
                )
                differences[dep]["signature_changes"] = signature_changes

                # If there are signature changes, add it to the category
                if signature_changes["has_changes"]:
                    differences[dep]["category"] = "Downgraded package with signature changes"

    return (
        differences,
        newly_added_pkg,
        deleted_pkg,
        upgraded_pkg,
        downgraded_pkg,
        no_change_pkg,
    )


def changed_patch(package_data_old, package_data_new):
    logging.info("Comparing patches...")
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


def compare_code_signatures(pkg_name, old_version, new_version, SA_1, SA_2):
    """Compare code signatures between versions of a package."""
    old_pkg = f"{pkg_name}@{old_version}"
    new_pkg = f"{pkg_name}@{new_version}"

    old_signature = SA_1.get(old_pkg, {}).get("code_signature", {})
    new_signature = SA_2.get(new_pkg, {}).get("code_signature", {})

    changes = {
        "old_signature_present": old_signature.get("signature_present", False),
        "new_signature_present": new_signature.get("signature_present", False),
        "old_signature_valid": old_signature.get("signature_valid", False),
        "new_signature_valid": new_signature.get("signature_valid", False),
        "has_changes": False,
    }

    # Check if there are any changes in signature status
    if (
        changes["old_signature_present"]
        and not changes["new_signature_present"]
        or changes["old_signature_valid"]
        and not changes["new_signature_valid"]
    ):
        changes["has_changes"] = True

    return changes
