"""Module for extracting dependencies.
Support npm, yarn classic, yarn berry, pnpm
"""

import re
import os
import subprocess
import json
import logging
import sys
import shutil
from collections import defaultdict

from tool_config import PNPM_LIST_COMMAND

logger = logging.getLogger(__name__)


def extract_deps_from_pnpm_lockfile(pnpm_lockfile_yaml):
    """
    Extract dependencies from a pnpm-lock.yaml file.

    Args:
        pnpm_lockfile_yaml (str): The content of the pnpm lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    yaml_data = yaml.safe_load(pnpm_lockfile_yaml)
    yaml_version = yaml_data.get("lockfileVersion")
    if yaml_version != "9.0":
        logging.error("Invalid pnpm lockfile version: %s", yaml_version)
        print("The pnpm lockfile version is not supported(yet): ", yaml_version)
        # end the process
        sys.exit(1)

    try:
        # pkg_name_with_resolution = set()
        deps_list_data = {}

        package_keys = sorted(list(yaml_data.get("packages", {}).keys()))
        patches = sorted(list(yaml_data.get("patchedDependencies", {}).keys()))

        deps_list_data = {
            "resolutions": package_keys,
            "patches": patches,
        }

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from pnpm-lock.yaml: %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_npm(npm_lock_file):
    """
    Extract dependencies from a "package-lock.json" file.

    Args:
        npm_lock_file (dict): The content of the npm lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.

    """

    lock_file_json = json.loads(npm_lock_file)
    try:
        patches = []
        pkg_name_with_resolution = set()
        deps_list_data = {}

        packages = {}

        # Extract packages from the "packages" object
        if lock_file_json.get("packages") and isinstance(lock_file_json["packages"], dict):
            for package_path, package_info in lock_file_json["packages"].items():
                if package_path.startswith("node_modules/"):
                    package_name = package_path.split("/", 1)[1]
                    if "node_modules" in package_name:
                        package_name = package_name.split("node_modules/")[-1]

                    if package_info.get("version"):
                        packages[package_name] = package_info["version"]
                        pkg_name_with_resolution.add(f"{package_name}@{package_info['version']}")

            deps_list_data = {
                "resolutions": sorted(list(pkg_name_with_resolution)),
                "patches": patches,
            }

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from package-lock.json: %s",
            str(e),
        )

    return {"resolutions": [], "patches": []}


def extract_deps_from_yarn_berry(yarn_lock_file):
    """
    # JavaScript
    Extract dependencies from a Yarn Berry lock file.

    Args:
        yarn_lock_file (str): The content of the Yarn Berry lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    try:
        patches = []
        pkg_name_with_resolution = []

        for line in yarn_lock_file.splitlines():
            match = re.match(r"^\s+resolution:\s+(.+)$", line)
            if match:
                if "@patch" in line:
                    # Check if "patch" is present in the line
                    line = line.replace('resolution: "', "").strip('"').lstrip()
                    patches.append(line)
                else:
                    pkg_name_with_resolution.append(match.group(1).strip('"'))

        deps_list_data = {"resolutions": pkg_name_with_resolution, "patches": patches}

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Berry): %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_v1_yarn(yarn_lock_file):
    """
    # JavaScript
    Extract dependencies from a Yarn Classic lock file.

    Args:
        yarn_lock_file (str): The content of the Yarn Classic lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    # yarn-classic
    try:
        extracted_info = []
        patches = []

        pattern = r'^\s*$\n\"?(\@?([^\s]+))@.*?:\n\s*version\s+"([^\s]+)"'

        matches = re.findall(pattern, yarn_lock_file, re.MULTILINE)

        extracted_info = [f"{match[0]}@{match[2]}" for match in matches]
        for item in extracted_info:
            if len(item.split("@npm:")) > 1:
                extracted_info.remove(item)
                extracted_info.append(item.split("@npm:")[1])

        extracted_info = sorted(extracted_info)

        deps_list_data = {"resolutions": extracted_info, "patches": patches}

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Classic): %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_pnpm_lock_yaml(pnpm_lock_yaml_file):
    """
    Extract dependencies from a pnpm-lock.yaml file.
    """


def get_pnpm_dep_tree(folder_path, version_tag, project_repo_name):
    """
    Get pnpm dependency tree for the given project.

    Args:
        folder_path (str): Path to the project folder
        version_tag (str): Version tag of the project
        project_repo_name (str): Name of the project repository

    Returns:
        dict: Dependency tree
    """
    version_tag_name = version_tag.replace("/", "-")
    project_repo_name_for_dir = project_repo_name.replace("/", "-")
    # for pnpm mono repo
    dir_name = f"{project_repo_name_for_dir}-{version_tag_name}"

    if not os.path.exists(dir_name):
        repo_url = f"https://github.com/{project_repo_name}.git"
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                f"{version_tag}",
                repo_url,
                dir_name,
            ],
            check=True,
        )
        logging.info("Cloning %s Repository...", project_repo_name)

        # repo_name = repo_url.split("/")[-1].replace(".git", "")

        logging.info("Cloned to %s", dir_name)

        os.chdir(dir_name)

        logging.info("Installing dependencies...")
        # try:
        subprocess.run(["pnpm", "install", "--ignore-scripts"], check=True)

    try:
        # if it is not in dir_name, change to dir_name
        dir_if = os.getcwd().split("/")[-1]
        if dir_if != dir_name:
            os.chdir(dir_name)

        logging.info("Getting pnpm dependency tree by running %s", PNPM_LIST_COMMAND)

        command = PNPM_LIST_COMMAND
        print("Getting pnpm dependency tree...")
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )

        parent_directory = os.path.abspath("..")
        details_folder = os.path.join(parent_directory, folder_path)

        output_file_path = os.path.join(details_folder, "pnpm_dep_tree.txt")
        logging.info("Writing pnpm dependency tree to %s", output_file_path)

        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)

        # os.chdir("..")
        change_to_cloned_parent_dir = f"../{dir_name}"
        shutil.rmtree(change_to_cloned_parent_dir)
        logging.info("Removed %s", dir_name)
        # change to child folder

        return result.stdout.splitlines(), folder_path

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info("Removed %s", dir_name)


def extract_deps_from_pnpm_mono(folder_path, version_tag, project_repo_name):
    """
    Extract dependencies from a pnpm monorepo.

    Args:
        folder_path (str): Path to the monorepo folder
        version_tag (str): Version tag to use

    Returns:
        tuple: Lists of all dependencies and registry dependencies
    """
    all_deps = []
    registry_dep = []
    workspace_dep = []
    patched_dep = []

    tree, folder_path_for_this = get_pnpm_dep_tree(folder_path, version_tag, project_repo_name)

    os.chdir("..")
    if tree is None:
        return {}
    dependencies = defaultdict(list)

    dep_pattern = re.compile(r"([a-zA-Z0-9@._/-]+)\s+(\S+)")
    logging.info("Extracting dependencies from pnpm list output")

    for line in tree:
        if "ledger-live-desktop" in line or "production dependency, optional only, dev only" in line:
            print("ledger-live-desktop found")
            continue

        match = dep_pattern.search(line)
        if match:
            dep_name = match.group(1).strip()
            dep_version = match.group(2).strip()
            dependencies[dep_name].append(dep_version)
            print("dependency found", dep_name)

        # logging.info(f"Number of dependencies({version_tag}): {len(dependencies)}")

    for dep, versions in sorted(dependencies.items()):
        for version in sorted(set(versions)):
            formatted_dep = f"{dep}@{version}"
            all_deps.append(formatted_dep)
            if "link:" in formatted_dep:
                workspace_dep.append(formatted_dep)
            elif "patch_hash=" in formatted_dep:
                patched_dep.append(formatted_dep)
            else:
                registry_dep.append(formatted_dep)

    dep_all_path = os.path.join(folder_path_for_this, "deps_list_all_installed.json")

    logging.info("Writing all dependencies to %s", dep_all_path)

    with open(dep_all_path, "w", encoding="utf-8") as f:
        json.dump(all_deps, f, indent=4)

    deps_list_data = {
        "resolutions": registry_dep,
        "patches": patched_dep,
        "workspace": workspace_dep,
    }

    logging.info(
        "Number of packages from registry(%s): %d",
        version_tag,
        len(deps_list_data["resolutions"]),
    )
    logging.info(
        "Number of packages from workspace(%s): %d",
        version_tag,
        len(deps_list_data["workspace"]),
    )
    logging.info(
        "Number of patched packages(%s): %d",
        version_tag,
        len(deps_list_data["patches"]),
    )

    return deps_list_data


def extract_deps_from_maven(pom_xml_content):
    """
    Extract dependencies from a Maven pom.xml file.

    Args:
        pom_xml_content (str): The content of the pom.xml file.

    Returns:
        dict: A dictionary containing the extracted dependencies.
    """
    try:
        deps_list = []
        properties = {}

        # Extract properties
        prop_pattern = r"<properties>(.*?)</properties>"
        prop_matches = re.findall(prop_pattern, pom_xml_content, re.DOTALL)
        for prop_content in prop_matches:
            # print(f"Properties content: {prop_content}")
            prop_items = re.findall(r"<([^>]+)>(.*?)</\1>", prop_content, re.DOTALL)
            properties.update(dict(prop_items))

        # Extract parent version if exists
        parent_version_pattern = r"<parent>.*?<version>(.*?)</version>.*?</parent>"
        parent_version_match = re.search(parent_version_pattern, pom_xml_content, re.DOTALL)
        if parent_version_match:
            properties["project.version"] = parent_version_match.group(1)

        # Extract parent artifactId if exists
        parent_artifactId_pattern = r"<parent>.*?<artifactId>(.*?)</artifactId>.*?</parent>"
        parent_artifactId_match = re.search(parent_artifactId_pattern, pom_xml_content, re.DOTALL)
        if parent_artifactId_match:
            properties["project.artifactId"] = parent_artifactId_match.group(1)

        # Extract parent groupId if exists
        parent_groupId_pattern = r"<parent>.*?<groupId>(.*?)</groupId>.*?</parent>"
        parent_groupId_match = re.search(parent_groupId_pattern, pom_xml_content, re.DOTALL)
        if parent_groupId_match:
            properties["project.groupId"] = parent_groupId_match.group(1)

        pattern = r"<dependency>.*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?<version>(.*?)</version>.*?</dependency>"
        matches = re.findall(pattern, pom_xml_content, re.DOTALL)

        for group_id, artifact_id, version in matches:
            # Resolve property placeholders
            if group_id.startswith("${"):
                group_id = properties.get(group_id[2:-1], group_id)
            if artifact_id.startswith("${"):
                artifact_id = properties.get(artifact_id[2:-1], artifact_id)
            if version.startswith("${"):
                version = properties.get(version[2:-1], version)
            deps_list.append(f"{group_id}:{artifact_id}@{version}")

        deps_list_data = {"resolutions": deps_list, "patches": []}

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from pom.xml file: %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def deps_versions(deps_versions_info_list):
    """
    Extract dependencies versions from a list of dependency versions.

    Args:
        deps_versions_info_list (list): List of dependency versions

    Returns:
        dict: Dictionary containing dependency names and their versions
    """
    deps_versions_dict = {}
    for pkg in deps_versions_info_list.get("resolutions"):
        pkg_name, version = pkg.rsplit("@", 1)

        version = version.replace("npm:", "")

        if pkg_name in deps_versions_dict:
            deps_versions_dict[pkg_name].append(version)
        else:
            deps_versions_dict[pkg_name] = [version]

    return deps_versions_dict


def get_patches_info(yarn_lock_file):
    """
    Get patches information from a Yarn Berry lock file.

    Args:
        yarn_lock_file (str): The content of the Yarn Berry lock file.

    Returns:
        dict: Dictionary containing patch information
    """
    deps_list = extract_deps_from_yarn_berry(yarn_lock_file)

    patches_info = {}
    for pkg_patches in deps_list.get("patches"):
        pattern = r"\.yarn/patches/(.*?\.patch).*version=([0-9.]+)&hash=([a-z0-9]+)"
        match = re.search(pattern, pkg_patches)

        if match:
            patch_file_path = match.group(1)
            version = match.group(2)
            hash_code = match.group(3)

            patches_info[pkg_patches] = {
                "version": str(version),
                "hash_code": str(hash_code),
                "patch_file_path": str(patch_file_path),
            }

        else:
            patches_info[pkg_patches] = {
                "version": None,
                "hash_code": None,
                "patch_file_path": None,
            }

    logging.info("Number of patches: %d", len(patches_info))

    return patches_info
