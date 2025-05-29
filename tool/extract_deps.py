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

from tool.tool_config import PNPM_LIST_COMMAND, get_cache_manager, YarnLockParser, get_package_url, get_registry_url

cache_manager = get_cache_manager()

MVN_DEPENDENCY_PLUGIN = "org.apache.maven.plugins:maven-dependency-plugin:3.8.1"
append_dependency_goal = lambda goal: f"{MVN_DEPENDENCY_PLUGIN}:{goal}"
TREE_GOAL = append_dependency_goal("tree")
RESOLVE_PLUGINS_GOAL = append_dependency_goal("resolve-plugins")
TREE_LOG = "/tmp/deps.json"
RESOLVE_PLUGINS_LOG = "/tmp/plugins.log"


def build_tree_structure_with_links(paths, package_manager):
    tree = {}
    for path in paths:
        current_level = tree
        for node in path[:-1]:
            label = f"[{node}]({get_package_url(node, package_manager)})"
            if label not in current_level:
                current_level[label] = {}
            current_level = current_level[label]
    return tree

def format_tree_as_text(tree, target_package, package_manager, indent="", is_last_child=True):
    if not tree:
        return f"{indent}└── [{target_package}]({get_package_url(target_package, package_manager)})"
    
    lines = []
    items = list(tree.items())
    for i, (label, subtree) in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└──" if is_last else "├──"
        lines.append(f"{indent}{connector} {label}")
        child_indent = indent + ("    " if is_last else "│   ")

        if not subtree:
            lines.append(f"{child_indent}└── [{target_package}]({get_package_url(target_package, package_manager)})")
        else:
            child_lines = format_tree_as_text(subtree, target_package, package_manager, child_indent, is_last)
            lines.extend(child_lines if isinstance(child_lines, list) else [child_lines])
    return lines

def format_paths_for_markdown(paths, target_package, package_manager):
    if not paths:
        return ""
    
    tree = build_tree_structure_with_links(paths, package_manager)
    if not tree:
        return f'<details><summary>1 path</summary><pre>{target_package}</pre></details>'

    tree_lines = format_tree_as_text(tree, target_package, package_manager)
    tree_text = "<br>".join(tree_lines)
    summary_text = f"{len(paths)} path{'s' if len(paths) != 1 else ''}"
    return f'<details><summary>{summary_text}</summary><pre>{tree_text}</pre></details>'



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

    try:
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

        parent_packages = defaultdict(set)
        pkg_name_with_resolution = []
        patches = []

        # Iterate through packages to build parent-child relationships
        for pkg_name, pkg_info in yaml_data.get("snapshots", {}).items():
            version_match = re.search(r"@([^@]+)$", pkg_name)
            version = version_match.group(1) if version_match else "unknown"

            # Clean up package name (remove version)
            pkg_name = re.sub(r"@[^@]+$", "", pkg_name)

            # Construct resolution string
            resolution = f"{pkg_name}@{version}"
            pkg_name_with_resolution.append(resolution)

            # Track child dependencies
            if pkg_info.get("dependencies"):
                for child_name, child_version in pkg_info["dependencies"].items():
                    child_resolution = f"{child_name}@{child_version}"
                    parent_packages[child_resolution].add(resolution)

        # Convert to required format with parent information
        deps_list_data = {
            "resolutions": list(
                {
                    "info": info,
                    "parent": list(parent_packages.get(info, set())),
                }
                for info in sorted(pkg_name_with_resolution)
            ),
            "patches": patches,
        }

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data
    except yaml.YAMLError as e:
        logging.error(
            "An error occurred while parsing the pnpm-lock.yaml file: %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}
    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from pnpm-lock.yaml: %s",
            str(e),
        )
        return {"resolutions": [], "patches": []}


def extract_deps_from_npm(repo_path, npm_lock_file):
    """
    Extract dependencies from an npm project using npm list command.

    Args:
        repo_path (str): The project's source code repository path.
        npm_lock_file (str): The npm lock file path.

    Returns:
        dict: A dictionary containing the extracted dependencies and patches.
    """
    # Generate cache key based on repo path and project info
    lockfile_hash = get_lockfile_hash(npm_lock_file)
    if not lockfile_hash:
        logging.error("No lockfile found in %s", repo_path)
        return {"resolutions": [], "patches": []}
    cached_deps = cache_manager.extracted_deps_cache.get_dependencies(repo_path, lockfile_hash)
    if cached_deps:
       logging.info(f"Using cached dependencies for {repo_path}")
       return cached_deps

    try:
        # If we reach here, we need to resolve dependencies
        current_dir = os.getcwd()
        os.chdir(repo_path)
        # Run npm list to get dependency tree
        logging.info("Running npm list to extract dependencies...")
        result = subprocess.run(
            ["npm", "list", "--json", "--all", "--long", "--package-lock-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False  # Don't fail on warnings/missing peer deps
        )
        os.chdir(current_dir)
        
        if result.returncode != 0 and result.returncode != 1:
            # Return code 1 is common for missing peer deps, which is OK
            logging.error(f"npm list failed with return code {result.returncode}")
            logging.error(f"stderr: {result.stderr}")
            return {"resolutions": [], "patches": [], "aliased_packages": {}}
        
        npm_data = json.loads(result.stdout)
        # Parse project name and version from npm list output
        project_name = npm_data.get("name")
        project_version = npm_data.get("version")

        patches = []
        pkg_name_with_resolution = set()
        aliased_packages = {}
        parent_packages = {}  # Maps package -> set of immediate parents
        dependency_tree = {}  # Maps package -> complete dependency info
        
        # Add root package
        root_name = npm_data.get("name", project_name)
        root_version = npm_data.get("version", project_version)
        root_resolution = f"{root_name}@{root_version}"
        pkg_name_with_resolution.add(root_resolution)
        
        def process_dependencies(deps_dict, parent_resolution, current_path=None):
            """Recursively process dependencies from npm list output"""
            if not deps_dict:
                return
            
            if current_path is None:
                current_path = [parent_resolution]
                
            for dep_name, dep_info in deps_dict.items():
                if not isinstance(dep_info, dict):
                    continue
                    
                dep_version = dep_info.get("version")
                if not dep_version:
                    continue
                
                # Handle npm aliases (like "my-lodash": "npm:lodash@4.17.21")  
                original_name = dep_name
                if dep_info.get("resolved") and "npm:" in str(dep_info.get("resolved", "")):
                    # This might be an alias, extract the real name
                    resolved = str(dep_info.get("resolved", ""))
                    if "npm:" in resolved:
                        real_name_match = re.search(r"npm:([^@]+)@", resolved)
                        if real_name_match:
                            real_name = real_name_match.group(1)
                            logging.info(f"Found npm alias: {dep_name} -> {real_name}@{dep_version}")
                            aliased_packages[f"{real_name}@{dep_version}"] = f"{dep_name}@{dep_version}"
                            original_name = real_name
                
                dep_resolution = f"{original_name}@{dep_version}"
                pkg_name_with_resolution.add(dep_resolution)
                
                # Map this dependency to its immediate parent
                parent_packages.setdefault(dep_resolution, set()).add(parent_resolution)
                
                # Build the full path to this dependency
                full_path = current_path + [dep_resolution]
                
                # Store all paths to this dependency
                if dep_resolution not in dependency_tree:
                    dependency_tree[dep_resolution] = {
                        'paths': [],
                        'immediate_parents': set()
                    }
                
                dependency_tree[dep_resolution]['paths'].append(full_path[:])
                dependency_tree[dep_resolution]['immediate_parents'].add(parent_resolution)
                
                # Check for patches (if using patch-package or similar)
                if dep_info.get("patched"):
                    patches.append({"info": dep_resolution})
                
                # Recursively process nested dependencies
                if dep_info.get("dependencies"):
                    process_dependencies(dep_info["dependencies"], dep_resolution, full_path)
        
        # Process all dependencies starting from root
        if npm_data.get("dependencies"):
            process_dependencies(npm_data["dependencies"], root_resolution)
        
        deps_list_data = {
            "resolutions": list(
                {
                    "info": info,
                    "parent": format_paths_for_markdown(
                        dependency_tree.get(info, {}).get("paths", []), info, "npm"
                    )
                }
                for info in sorted(pkg_name_with_resolution)
            ),
            "patches": patches,
            "aliased_packages": aliased_packages,
        }
        
        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)
        
        logging.info(f"Extracted {len(pkg_name_with_resolution)} dependencies from npm list")
        return deps_list_data

    except subprocess.CalledProcessError as e:
        os.chdir(current_dir)
        logging.error(f"Error running npm list: {e}")
        logging.error(f"stderr: {e.stderr}")
        return {"resolutions": [], "patches": [], "aliased_packages": {}}
    except json.JSONDecodeError as e:
        os.chdir(current_dir)
        logging.error(f"Error parsing npm list JSON output: {e}")
        return {"resolutions": [], "patches": [], "aliased_packages": {}}
    except Exception as e:
        os.chdir(current_dir)
        logging.error(f"Unexpected error in extract_deps_from_npm: {e}")
        return {"resolutions": [], "patches": [], "aliased_packages": {}}


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
        aliased_packages = {}

        parent_packages = {}
        parsed_lockfile = yaml.safe_load(yarn_lock_file)
        for entry_data in parsed_lockfile.values():
            resolution = entry_data.get("resolution", "")
            if resolution:
                if "@patch" in resolution:
                    # Check if "patch" is present in the resolution
                    resolution = resolution.replace('resolution: "', "").strip('"').lstrip()
                    patches.append(resolution)
                else:
                    # aliases will show up as something like my-foo@npm:foo@x.y.z
                    alias_pattern = r"(.+?)@npm:(.+?)@(.+)"
                    alias_match = re.match(alias_pattern, resolution)
                    if alias_match:
                        # if it is an alias, we add the original name to the list
                        logging.info(f"Found yarn alias for {alias_match.group(2)}@{alias_match.group(3)}")
                        logging.info(f"Aliased to {alias_match.group(1)}@{alias_match.group(3)}")
                        aliased_packages[f"{alias_match.group(2)}@{alias_match.group(3)}"] = (
                            f"{alias_match.group(1)}@{alias_match.group(3)}"
                        )
                        resolution = f"{alias_match.group(2)}@{alias_match.group(3)}"
                    pkg_name_with_resolution.append(resolution)

                if entry_data.get("dependencies"):
                    for dep_name, version in entry_data["dependencies"].items():
                        parent_packages.setdefault(f"{dep_name}@{version}", set()).add(resolution)

        deps_list_data = {
            "resolutions": list(
                {"info": info, "parent": list(parent_packages.get(info, set()))}
                for info in sorted(pkg_name_with_resolution)
            ),
            "patches": list({"info": info} for info in sorted(patches)),
            "aliased_packages": aliased_packages,
        }

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except yaml.YAMLError as e:
        logging.error(
            "An error occurred while parsing the yarn.lock file(Yarn Berry): %s",
            str(e),
        )
        return {"resolutions": [], "patches": [], "aliased_packages": []}
    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Berry): %s",
            str(e),
        )
        return {"resolutions": [], "patches": [], "aliased_packages": []}


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
        pkg_name_with_resolution = []
        patches = []
        aliased_packages = {}
        parent_packages = defaultdict(set)

        # Find all dependencies
        parser = YarnLockParser(yarn_lock_file)
        dependencies = parser.parse()
        for entry_name, entry_data in dependencies.items():
            item = f"{entry_name}@{entry_data['version_constraint']}"
            if entry_data.get("original_name"):
                logging.warning(f"Found yarn alias for {item}")
                logging.warning(f"Original name: {entry_data['original_name']}@{entry_data['version_constraint']}")
                logging.warning(f"Aliased to: {entry_name}@{entry_data['version_constraint']}")
                aliased_packages[item] = f"{entry_data['original_name']}@{entry_data['version_constraint']}"

            if entry_data.get("dependencies"):
                logging.info("Found child dependencies for %s", item)
                for dep_name, dep_version in entry_data["dependencies"].items():
                    dep_name = f"{dep_name}@{dep_version}"
                    parent_packages[dep_name].add(item)

            pkg_name_with_resolution.append(item)

        deps_list_data = {
            "resolutions": list(
                {
                    "info": info,
                    "parent": list(parent_packages.get(info, set())),
                }
                for info in sorted(pkg_name_with_resolution)
            ),
            "patches": patches,
            "aliased_packages": aliased_packages,
        }

        cache_manager.extracted_deps_cache.cache_dependencies(repo_path, lockfile_hash, deps_list_data)

        return deps_list_data

    except (IOError, ValueError, KeyError) as e:
        logging.error(
            "An error occurred while extracting dependencies from yarn.lock file(Yarn Classic): %s",
            str(e),
        )
        return {"resolutions": [], "patches": [], "aliased_packages": []}


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
    os.chdir("..")
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

    def parse_mvn_tree_logs(log_file):
        """
        Parse Maven dependency tree logs to extract dependency information.

        Args:
            log_file (str): Path to the Maven dependency tree log file

        Returns:
            list: List of dictionaries containing dependency information
        """
        dependencies = []

        def parse_dependency(dep, parent=None):
            dep_info = {
                "groupId": dep["groupId"],
                "artifactId": dep["artifactId"],
                "version": dep["version"],
                "parent": f"{parent['groupId']}:{parent['artifactId']}@{parent['version']}" if parent else None,
            }
            dependencies.append(dep_info)
            for child in dep.get("children", []):
                parse_dependency(child, dep_info)

        try:
            with open(log_file, "r") as f:
                data = json.load(f)
                for dep in data["children"]:
                    parse_dependency(dep)

        except FileNotFoundError:
            logging.error("Dependency log file not found: %s", log_file)
        except Exception as e:
            logging.error("Error parsing dependency log: %s", str(e))

        return dependencies

    def parse_mvn_plugin_logs(log_file):
        """
        Parse Maven dependency resolution logs to extract dependency information.

        Args:
            log_file (str): Path to the Maven dependency resolution log file

        Returns:
            list: List of dictionaries containing dependency information
        """
        dependencies = []
        current_parent = None
        base_indent_level = 3  # 3 spaces is the base indent level
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                parsing = False

                for line in lines:
                    if "The following plugins have been resolved:" in line:
                        parsing = True
                        continue

                    if "The following plugins have been" in line and parsing:
                        break

                    if parsing:
                        indent_level = len(line) - len(line.lstrip(" ")) - base_indent_level
                        parts = line.strip().split(":")
                        if len(parts) >= 3:
                            dep_info = {
                                "groupId": parts[0],
                                "artifactId": parts[1],
                                "version": parts[-1].split()[0],
                                "parent": None,
                            }
                            if indent_level == 0:
                                current_parent = (
                                    f"{dep_info['groupId']}:{dep_info['artifactId']}@{dep_info['version']}"
                                )
                            else:
                                dep_info["parent"] = current_parent
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
            TREE_GOAL,
            "-DoutputType=json",
            f"-DoutputFile={TREE_LOG}",
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
        retrieved_deps = parse_mvn_tree_logs(TREE_LOG)
        retrieved_plugins = parse_mvn_plugin_logs(RESOLVE_PLUGINS_LOG)

        # Go back to original directory
        os.chdir(current_dir)

        # Format the dependencies
        parsed_deps = [
            {
                "info": f"{dep['groupId']}:{dep['artifactId']}@{dep['version']}",
                "parent": dep["parent"],
                "command": "tree",
            }
            for dep in retrieved_deps
        ]
        parsed_plugins = [
            {
                "info": f"{plugin['groupId']}:{plugin['artifactId']}@{plugin['version']}",
                "parent": plugin["parent"],
                "command": "resolve-plugins",
            }
            for plugin in retrieved_plugins
        ]

        dependency_tree = defaultdict(lambda: {"paths": [], "immediate_parents": set()})
        pkg_name_with_resolution = set()

        for dep in parsed_deps + parsed_plugins:
            child = dep["info"]
            parent = dep["parent"]
            pkg_name_with_resolution.add(child)

            if parent:
                dependency_tree[child]["paths"].append([parent, child])
                dependency_tree[child]["immediate_parents"].add(parent)
            else:
                # Root dependency
                dependency_tree[child]["paths"].append([child])

        # Create the result
        deps_list_data = {
            "resolutions": list(
                {
                    "info": info,
                    "parent": format_paths_for_markdown(
                        dependency_tree.get(info, {}).get("paths", []),
                        info,
                        "maven"
                    ),
                    "command": command
                }
                for info, command in {
                    item["info"]: item["command"] for item in parsed_deps + parsed_plugins
                }.items()
            ),
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
