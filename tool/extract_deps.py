import re
import os
import subprocess
import json
import logging
import sys
import shutil
from collections import defaultdict

logger = logging.getLogger(__name__)


def extract_deps_from_yarn_berry(yarn_lock_file):
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

    except Exception as e:
        logging.error(
            f"An error occurred while extracting dependencies from yarn.lock file(Yarn Berry): {e}"
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_v1_yarn(yarn_lock_file):
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

    except Exception as e:
        logging.error(
            f"An error occurred while extracting dependencies from yarn.lock file(Yarn Classic): {e}"
        )
        return {"resolutions": [], "patches": []}


def get_pnpm_dep_tree(folder_path, version_tag):
    version_tag_name = version_tag.replace("/", "-")
    # for ledger-live
    dir_name = f"ledger-live-{version_tag_name}"

    if not os.path.exists(f"ledger-live-{version_tag_name}"):
        repo_url = "https://github.com/LedgerHQ/ledger-live.git"
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
        logging.info("Cloning Ledger-live Repository...")

        # repo_name = repo_url.split("/")[-1].replace(".git", "")

        logging.info(f"Cloned to {dir_name}")

        os.chdir(dir_name)

        logging.info("Installing dependencies...")
        # try:
        subprocess.run(["pnpm", "install", "--ignore-scripts"], check=True)

    try:
        # if it is not in dir_name, change to dir_name
        dir_if = os.getcwd().split("/")[-1]
        if dir_if != dir_name:
            os.chdir(dir_name)

        logging.info(
            "Getting pnpm dependency tree by running `pnpm list --filter ledger-live-desktop --depth Infinity`"
        )
        print("Getting pnpm dependency tree...")
        result = subprocess.run(
            ["pnpm", "list", "--filter", "ledger-live-desktop", "--depth", "Infinity"],
            check=True,
            capture_output=True,
            text=True,
        )

        parent_directory = os.path.abspath("..")
        details_folder = os.path.join(parent_directory, folder_path)

        output_file_path = os.path.join(details_folder, "pnpm_dep_tree.txt")
        logging.info(f"Writing pnpm dependency tree to {output_file_path}")

        with open(output_file_path, "w") as f:
            f.write(result.stdout)

        # os.chdir("..")
        change_to_cloned_parent_dir = f"../{dir_name}"
        shutil.rmtree(change_to_cloned_parent_dir)
        logging.info(f"Removed {dir_name}")
        # change to child folder

        return result.stdout.splitlines(), folder_path

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info(f"Removed {dir_name}")


def extract_deps_from_pnpm_mono(folder_path, version_tag):
    all_deps = []
    registry_dep = []
    workspace_dep = []
    patched_dep = []

    tree, folder_path_for_this = get_pnpm_dep_tree(folder_path, version_tag)

    os.chdir("..")
    if tree is None:
        return {}
    dependencies = defaultdict(list)

    dep_pattern = re.compile(r"([a-zA-Z0-9@._/-]+)\s+(\S+)")
    logging.info("Extracting dependencies from pnpm list output")

    for line in tree:
        if (
            "ledger-live-desktop" in line
            or "production dependency, optional only, dev only" in line
        ):
            print("ledger-live-desktop found")
            continue

        match = dep_pattern.search(line)
        if match:
            dep_name = match.group(1).strip()
            dep_version = match.group(2).strip()
            dependencies[dep_name].append(dep_version)
            print("dep_name match", dep_name)

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

    logging.info(f"Writing all dependencies to {dep_all_path}")

    with open(dep_all_path, "w") as f:
        json.dump(all_deps, f, indent=4)

    deps_list_data = {
        "resolutions": registry_dep,
        "patches": patched_dep,
        "workspace": workspace_dep,
    }

    logging.info(
        f"Number of packages from registry({version_tag}): {len(deps_list_data['resolutions'])}"
    )
    logging.info(
        f"Number of packages from workspace({version_tag}): {len(deps_list_data['workspace'])}"
    )
    logging.info(
        f"Number of patched packages({version_tag}): {len(deps_list_data['patches'])}"
    )

    return deps_list_data


def deps_versions(deps_versions_info_list):
    deps_versions = {}
    for pkg in deps_versions_info_list.get("resolutions"):
        pkg_name, version = pkg.rsplit("@", 1)

        version = version.replace("npm:", "")

        if pkg_name in deps_versions:
            deps_versions[pkg_name].append(version)
        else:
            deps_versions[pkg_name] = [version]

    return deps_versions


def get_pacthes_info(yarn_lock_file):
    deps_list = extract_deps_from_yarn_berry(yarn_lock_file)

    pacthse_info = {}
    for pkg_patches in deps_list.get("patches"):
        pattern = r"\.yarn/patches/(.*?\.patch).*version=([0-9.]+)&hash=([a-z0-9]+)"
        match = re.search(pattern, pkg_patches)

        if match:
            patch_file_path = match.group(1)
            version = match.group(2)
            hash_code = match.group(3)

            pacthse_info[pkg_patches] = {
                "version": str(version),
                "hash_code": str(hash_code),
                "patch_file_path": str(patch_file_path),
            }

        else:
            pacthse_info[pkg_patches] = {
                "version": None,
                "hash_code": None,
                "patch_file_path": None,
            }

    logging.info(f"Number of patches: {len(pacthse_info)}")

    return pacthse_info
