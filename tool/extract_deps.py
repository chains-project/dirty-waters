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
import json
import hashlib
from pathlib import Path
import yaml

from tool.tool_config import PNPM_LIST_COMMAND, get_cache_manager

logger = logging.getLogger(__name__)
cache_manager = get_cache_manager()

MVN_DEPENDENCY_PLUGIN = "org.apache.maven.plugins:maven-dependency-plugin:3.8.1"
append_dependency_goal = lambda goal: f"{MVN_DEPENDENCY_PLUGIN}:{goal}"
RESOLVE_GOAL = append_dependency_goal("resolve")
RESOLVE_PLUGINS_GOAL = append_dependency_goal("resolve-plugins")
RESOLVE_LOG = "/tmp/deps.log"
RESOLVE_PLUGINS_LOG = "/tmp/plugins.log"


def get_lockfile_hash(lockfile_content):
    """Generate a hash of the lockfile to detect changes"""
    return hashlib.sha256(str(lockfile_content).encode()).hexdigest()


def extract_deps_from_pnpm_lockfile(repo_path, pnpm_lockfile_yaml):
    """
    Extract dependencies from a pnpm-lock.yaml file.

    Args:
        repo_path (str): The project's source code repository.
        pnpm_lockfile_yaml (str): The content of the pnpm lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """

    yaml_data = yaml.safe_load(pnpm_lockfile_yaml)
    yaml_version = yaml_data.get("lockfileVersion")
    if yaml_version != "9.0":
        logging.error("Invalid pnpm lockfile version: %s", yaml_version)
        logging.error("The pnpm lockfile version is not supported(yet): ", yaml_version)
        # end the process
        sys.exit(1)

    lockfile_hash = get_lockfile_hash(yaml_data)
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
        logging.info(f"Using cached dependencies for {repo_path}")
        return cached_deps

    try:
        # pkg_name_with_resolution = set()
        deps_list_data = {}

        package_keys = list({"info": info} for info in sorted(yaml_data.get("packages", {}).keys()))
        patches = list({"info": info} for info in sorted(yaml_data.get("patchedDependencies", {}).keys()))

        deps_list_data = {
            "resolutions": package_keys,
            "patches": patches,
        }

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from pnpm-lock.yaml: %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_npm(repo_path, npm_lock_file):
    """
    Extract dependencies from a "package-lock.json" file.

    Args:
        repo_path (str): The project's source code repository.
        npm_lock_file (dict): The content of the npm lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    lock_file_json = json.loads(npm_lock_file)
    lockfile_hash = get_lockfile_hash(lock_file_json)
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
        logging.info(f"Using cached dependencies for {repo_path}")
        return cached_deps
    try:
        patches = []
        pkg_name_with_resolution = set()
        aliased_packages = {}
        deps_list_data = {}

        packages = {}

        if lock_file_json.get("packages") and isinstance(lock_file_json["packages"], dict):
            for package_path, package_info in lock_file_json["packages"].items():
                if package_path.startswith("node_modules/"):
                    package_name = package_path.split("/", 1)[1]
                    if "node_modules" in package_name:
                        package_name = package_name.split("node_modules/")[-1]

                    if package_info.get("version"):
                        version = package_info["version"]
                        # Handle npm aliases
                        original_name = package_info.get("name")
                        if original_name:
                            logging.warning(f"Found npm alias for {original_name}@{version}")
                            aliased_packages[f"{original_name}@{version}"] = package_name
                            package_name = original_name

                        packages[package_name] = version
                        pkg_name_with_resolution.add(f"{package_name}@{version}")

            deps_list_data = {
                "resolutions": list({"info": info} for info in sorted(pkg_name_with_resolution)),
                "patches": patches,
                "aliased_packages": aliased_packages,
            }

            cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from package-lock.json: %s",
            str(e),
        )

    return {"resolutions": [], "patches": [], "aliased_packages": []}


def extract_deps_from_yarn_berry(repo_path, yarn_lock_file):
    """
    # JavaScript
    Extract dependencies from a Yarn Berry lock file.

    Args:
        repo_path (str): The project's source code repository.
        yarn_lock_file (str): The content of the Yarn Berry lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    lockfile_hash = get_lockfile_hash(yarn_lock_file)
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
        logging.info(f"Using cached dependencies for {repo_path}")
        return cached_deps

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

        deps_list_data = {
            "resolutions": list({"info": info} for info in sorted(pkg_name_with_resolution)),
            "patches": list({"info": info} for info in sorted(patches)),
        }

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Berry): %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_v1_yarn(repo_path, yarn_lock_file):
    """
    # JavaScript
    Extract dependencies from a Yarn Classic lock file.

    Args:
        repo_path (str): The project's source code repository.
        yarn_lock_file (str): The content of the Yarn Classic lock file.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    # yarn-classic
    lockfile_hash = get_lockfile_hash(yarn_lock_file)
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
        logging.info(f"Using cached dependencies for {repo_path}")
        return cached_deps
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

        deps_list_data = {"resolutions": list({"info": info} for info in extracted_info), "patches": patches}

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Classic): %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def get_pnpm_dep_tree(folder_path, version_tag, repo_path, pnpm_scope):
    """
    Get pnpm dependency tree for the given project.

    Args:
        folder_path (str): Path to the project folder
        version_tag (str): Version tag of the project
        repo_path (str): Name of the project repository
        pnpm_scope (str): Scope of the pnpm package

    Returns:
        dict: Dependency tree
    """
    version_tag_name = version_tag.replace("/", "-")
    repo_path_for_dir = repo_path.replace("/", "-")
    # for pnpm mono repo
    dir_name = f"{repo_path_for_dir}-{version_tag_name}"

    if not os.path.exists(dir_name):
        repo_url = f"https://github.com/{repo_path}.git"
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
        logging.info("Cloning %s Repository...", repo_path)

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

        logging.info("Getting pnpm dependency tree by running %s", PNPM_LIST_COMMAND(pnpm_scope))

        command = PNPM_LIST_COMMAND(pnpm_scope)
        logging.info("Getting pnpm dependency tree...")
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
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            logging.info("Removed %s", dir_name)


def extract_deps_from_pnpm_mono(folder_path, version_tag, repo_path, pnpm_scope):
    """
    Extract dependencies from a pnpm monorepo.

    Args:
        folder_path (str): Path to the monorepo folder
        version_tag (str): Version tag to use
        repo_path (str): Name of the project repository
        pnpm_scope (str): Scope of the pnpm package

    Returns:
        tuple: Lists of all dependencies and registry dependencies
    """
    all_deps = []
    registry_dep = []
    workspace_dep = []
    patched_dep = []

    tree, folder_path_for_this = get_pnpm_dep_tree(folder_path, version_tag, repo_path, pnpm_scope)
    lockfile_hash = get_lockfile_hash(tree)  # not really a lockfile, but an approximation
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
        logging.info(f"Using cached dependencies for {repo_path}")
        return cached_deps

    os.chdir("..")
    if tree is None:
        return {}
    dependencies = defaultdict(list)

    dep_pattern = re.compile(r"([a-zA-Z0-9@._/-]+)\s+(\S+)")
    logging.info("Extracting dependencies from pnpm list output")

    for line in tree:
        # if "ledger-live-desktop" in line or "production dependency, optional only, dev only" in line:
        if pnpm_scope in line or "production dependency, optional only, dev only" in line:
            logging.info("ledger-live-desktop found")
            continue

        match = dep_pattern.search(line)
        if match:
            dep_name = match.group(1).strip()
            dep_version = match.group(2).strip()
            dependencies[dep_name].append(dep_version)
            logging.info("dependency found: %s", dep_name)

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
        "resolutions": list({"info": info} for info in registry_dep),
        "patches": list({"info": info} for info in patched_dep),
        "workspace": workspace_dep,
    }

    cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

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


def get_pom_hash(repo_path):
    """Generate a hash of the pom.xml file to detect changes"""
    pom_path = Path(repo_path) / "pom.xml"
    if not pom_path.exists():
        return None

    with open(pom_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_deps_from_maven(repo_path):
    """
    Extract dependencies from a Maven package, given the path to its locally cloned repo.

    Args:
        repo_path (str): The path to the locally cloned Maven package.

    Returns:
        dict: A dictionary containing the extracted dependencies.
    """

    def parse_mvn_dependency_logs(log_file, plugins=False):
        """
        Parse Maven dependency resolution logs to extract dependency information.

        Args:
            log_file (str): Path to the Maven dependency resolution log file
            plugins (bool): Whether we're dealing with resolve-plugin logs.

        Returns:
            list: List of dictionaries containing dependency information
        """
        dependencies = []

        try:
            with open(log_file, "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 3:  # Minimum required parts, [2] would be type
                        if plugins:
                            # Version will always be the last here, no scope
                            dep_info = {"groupId": parts[0], "artifactId": parts[1], "version": parts[-1].split()[0]}
                        else:
                            # Version will be the fourth one, after type; the last one is scope
                            dep_info = {"groupId": parts[0], "artifactId": parts[1], "version": parts[3].split()[0]}
                        dependencies.append(dep_info)

        except FileNotFoundError:
            logging.error("Dependency log file not found: %s", log_file)
        except Exception as e:
            logging.error("Error parsing dependency log: %s", str(e))

        return dependencies

    # Generate a cache key based on the repo path and pom.xml hash
    pom_hash = get_pom_hash(repo_path)
    if not pom_hash:
        logging.error("No pom.xml found in %s", repo_path)
        return {"resolutions": [], "patches": []}

    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, pom_hash)
    if cached_deps:
        logging.info(f"Using cached Maven dependencies for {repo_path}")
        return cached_deps

    # If we reach here, we need to resolve dependencies
    current_dir = os.getcwd()
    os.chdir(repo_path)

    retrieval_commands = {
        "regular": [
            "mvn",
            RESOLVE_GOAL,
            "-Dsort=true",
            f"-DoutputFile={RESOLVE_LOG}",
        ],
        "plugins": [
            "mvn",
            RESOLVE_PLUGINS_GOAL,
            "-Dsort=true",
            f"-DoutputFile={RESOLVE_PLUGINS_LOG}",
        ],
    }

    try:
        # Run Maven commands to resolve dependencies
        subprocess.run(retrieval_commands["regular"], check=True)
        subprocess.run(retrieval_commands["plugins"], check=True)

        # Parse the dependency logs
        retrieved_deps = parse_mvn_dependency_logs(RESOLVE_LOG)
        retrieved_plugins = parse_mvn_dependency_logs(RESOLVE_PLUGINS_LOG, plugins=True)

        # Go back to original directory
        os.chdir(current_dir)

        # Format the dependencies
        parsed_deps = [
            {"info": f"{dep['groupId']}:{dep['artifactId']}@{dep['version']}", "command": "resolve"}
            for dep in retrieved_deps
        ]
        parsed_plugins = [
            {"info": f"{plugin['groupId']}:{plugin['artifactId']}@{plugin['version']}", "command": "resolve-plugins"}
            for plugin in retrieved_plugins
        ]

        # Create the result
        deps_list_data = {
            "resolutions": list({item["info"]: item for item in parsed_plugins + parsed_deps}.values()),
            "patches": [],
        }

        # Cache the results
        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, pom_hash, deps_list_data)

        return deps_list_data

    except subprocess.CalledProcessError as e:
        os.chdir(current_dir)
        logging.error("Error resolving Maven dependencies: %s", str(e))
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
        pkg_name, version = pkg["info"].rsplit("@", 1)

        version = version.replace("npm:", "")

        if pkg_name in deps_versions_dict:
            deps_versions_dict[pkg_name].append(version)
        else:
            deps_versions_dict[pkg_name] = [version]

    return deps_versions_dict


def get_patches_info(repo_path, yarn_lock_file):
    """
    Get patches information from a Yarn Berry lock file.

    Args:
        repo_path (str): The project's source code repository.
        yarn_lock_file (str): The content of the Yarn Berry lock file.

    Returns:
        dict: Dictionary containing patch information
    """
    deps_list = extract_deps_from_yarn_berry(repo_path, yarn_lock_file)

    patches_info = {}
    for pkg_patches in deps_list.get("patches"):
        pattern = r"\.yarn/patches/(.*?\.patch).*version=([0-9.]+)&hash=([a-z0-9]+)"
        match = re.search(pattern, pkg_patches["info"])

        if match:
            patch_file_path = match.group(1)
            version = match.group(2)
            hash_code = match.group(3)

            patches_info[pkg_patches["info"]] = {
                "version": str(version),
                "hash_code": str(hash_code),
                "patch_file_path": str(patch_file_path),
            }

        else:
            patches_info[pkg_patches["info"]] = {
                "version": None,
                "hash_code": None,
                "patch_file_path": None,
            }

    logging.info("Number of patches: %d", len(patches_info))

    return patches_info
