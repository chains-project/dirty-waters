"""
Generate the report for the static analysis results.
"""

import json
import subprocess
from datetime import datetime
import pandas as pd

# Mapping smell to package managers that support it
SUPPORTED_SMELLS = {
    "no_source_code": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "github_404": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "sha_not_found": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "deprecated": ["yarn-classic", "yarn-berry", "pnpm", "npm"],
    "forked_package": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "provenance": ["yarn-classic", "yarn-berry", "pnpm", "npm"],
    "code_signature": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "invalid_code_signature": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "aliased_packages": ["yarn-classic", "yarn-berry", "npm"],
}

SHOW_PARENTS = ["yarn-classic", "yarn-berry", "npm", "maven"]


def load_data(filename):
    """Load data from a JSON file got from static analysis."""

    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def get_package_url(package_name, package_manager):
    if package_manager == "maven":
        ga, v = package_name.split("@")
        g, a = ga.split(":")
        return f"https://central.sonatype.com/artifact/{g}/{a}/{v}"
    elif package_manager in ["npm", "yarn-berry", "yarn-classic", "pnpm"]:
        name_in_url = "/v/".join(package_name.rsplit("@", 1))  # replaces last occurrence of @ for /v/
        return f"https://npmjs.com/package/{name_in_url}"
    raise ValueError("Package Manager not supported for acquiring package URL.")


def get_registry_url(package_name, package_manager):
    if package_manager == "maven":
        ga, v = package_name.split("@")
        g, a = ga.split(":")
        return f"https://central.sonatype.com/artifact/{g}/{a}/{v}"
    elif package_manager in ["npm", "yarn-berry", "yarn-classic", "pnpm"]:
        name_in_url = "/".join(package_name.rsplit("@", 1))  # replaces last occurrence of @ for /v/
        return f"https://registry.npmjs.com/{name_in_url}"
    raise ValueError("Package Manager not supported for acquiring registry URL.")


def create_dataframe(data, deps_list, package_manager):
    """
    Create a dataframe from the data got from static analysis.
    Aliased packages are added to the dataframe from the deps_list.

    """

    aliased_packages = deps_list.get("aliased_packages", {})
    rows = []

    for package_name, package_data in data.items():
        source_code_data = package_data.get("source_code", {}) or {}
        match_data = package_data.get("match_info", {}) or {}
        sc_version_info = source_code_data.get("source_code_version", {}) or {}
        aliased_package_name = aliased_packages.get(package_name, None)

        # Create a row for each package
        package_url = get_package_url(package_name, package_manager)
        registry_url = get_registry_url(package_name, package_manager)
        printed_package_name = f"[{package_name}]({package_url})"

        printed_sha_info, printed_tag_info = "", ""
        if not sc_version_info.get("is_sha"):
            # When package manager does not have a field for commit SHA
            printed_sha_info = f"[Commit SHA not directly available]({registry_url})"
        else:
            if sc_version_info.get("sha_status_code") == 404:
                printed_sha_info = f"[Commit SHA present but not found in repo]({sc_version_info.get('sha_url')})"
            else:
                printed_sha_info = f"[Commit SHA present in repo]({sc_version_info.get('sha_url')})"
                printed_tag_info = f"Not acquired due to SHA presence"
        if not printed_tag_info:
            if not sc_version_info.get("exists"):
                printed_tag_info = f"[Release tag not found in repo]({sc_version_info.get('tag_url')})"
            else:
                printed_tag_info = f"[Release tag found in repo]({sc_version_info.get('tag_url')})"
        row = {
            "package_name": printed_package_name,
            "deprecated_in_version": package_data.get("package_info", {}).get("deprecated_in_version"),
            "provenance_in_version": package_data.get("package_info", {}).get("provenance_in_version"),
            "all_deprecated": package_data.get("package_info", {}).get("all_deprecated", None),
            "signature_present": package_data.get("code_signature", {}).get("signature_present"),
            "signature_valid": package_data.get("code_signature", {}).get("signature_valid"),
            "parent": f"`{package_data.get("parent", "-")}`",
            "command": f"`{package_data.get("command", "-")}`",
            "is_github": source_code_data.get("is_github", False),
            "github_url": source_code_data.get("github_url", "Could not find repo from package registry"),
            "github_exists": source_code_data.get("github_exists", None),
            "github_redirected": source_code_data.get("github_redirected", None),
            "archived": source_code_data.get("archived", None),
            "is_fork": source_code_data.get("is_fork", None),
            "parent_repo_link": source_code_data.get("parent_repo_link", None),
            "open_issues_count": source_code_data.get("open_issues_count", "-"),
            "is_aliased": aliased_package_name is not None,
            "aliased_package_name": f"`{aliased_package_name}`" if aliased_package_name else "-",
            "is_match": match_data.get("match", None),
            "sha_exists": sc_version_info.get("exists", False),
            "sha_info": printed_sha_info,
            "tag_info": printed_tag_info,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    return df.set_index("package_name")


def no_source_code(combined_repo_problems_df, md_file, amount, package_manager):
    """
    Create a section for packages with no source code.
    """

    if not combined_repo_problems_df.empty:
        md_file.write(
            f"""
<details>
<summary>Source code links that could not be found({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        combined_repo_problems_df.index = range(1, len(combined_repo_problems_df) + 1)
        markdown_text = combined_repo_problems_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["github_404"]:
        md_file.write(
            f"\nThe package manager ({package_manager}) does not support checking for not found source code links.\n"
        )
    else:
        md_file.write("All analyzed packages have a source code repo.\n")
        return False

    return True


def sha_not_found(sha_not_found_df, md_file, amount, package_manager):
    """
    Create a section for packages with inaccessible commit SHAs/release tags.
    """

    if not sha_not_found_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages with available source code repos but with inaccessible commit SHAs/tags({amount})</summary>
    """
        )

        md_file.write("\n\n\n")
        markdown_text = sha_not_found_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["sha_not_found"]:
        md_file.write(
            f"\nThe package manager ({package_manager}) does not support checking for inaccessible commit SHAs/tags.\n"
        )
    else:
        md_file.write("\nAll packages have accessible tags.\n")
        return False

    return True


def deprecated(version_deprecated_df, md_file, amount, package_manager):
    """
    Create a section for deprecated packages.
    """

    if not version_deprecated_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of deprecated packages({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = version_deprecated_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["deprecated"]:
        md_file.write(
            f"\nThe package manager ({package_manager}) does not support checking for deprecated packages.\n"
        )
    else:
        md_file.write("\nNo deprecated package found.\n")
        return False

    return True


def forked_package(forked_package_df, md_file, amount, package_manager):
    """
    Create a section for forked packages.
    """

    if not forked_package_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages from fork({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = forked_package_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["forked_package"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for forked packages.\n")
    else:
        md_file.write("\nNo package is from fork.\n")
        return False

    return True


def provenance(provenance_df, md_file, amount, package_manager):
    """
    Create a section for packages without provenance.
    """

    if not provenance_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages without provenance({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = provenance_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["provenance"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for provenance.\n")
    else:
        md_file.write("\nAll packages have provenance.\n")
        return False

    return True


def code_signature(code_signature_df, md_file, amount, package_manager):
    """
    Create a section for packages without code signature.
    """

    if not code_signature_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages without code signature({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = code_signature_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["code_signature"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for code signature.\n")
    else:
        md_file.write("\nAll packages have code signature.\n")
        return False

    return True


def invalid_code_signature(invalid_code_signature_df, md_file, amount, package_manager):
    """
    Create a section for packages with invalid code signature.
    """

    if not invalid_code_signature_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages with an existing but invalid code signature({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = invalid_code_signature_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["code_signature"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for code signature.\n")
    else:
        md_file.write("\nAll packages have valid code signature.\n")
        return False

    return True


def aliased_package(aliased_package_df, md_file, amount, package_manager):
    """
    Create a section for aliased packages.
    """

    if not aliased_package_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of aliased packages({amount})</summary>
    """
        )
        md_file.write("\n\n\n")
        markdown_text = aliased_package_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["aliased_packages"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for aliased packages.\n")
    else:
        md_file.write("\nNo aliased package found.\n")
        return False

    return True


def write_summary(
    df, project_name, release_version, package_manager, filename, enabled_checks, gradual_report, mode="w"
):
    """
    Write a summary of the static analysis results to a markdown file.
    """

    no_source_code_repo_df = df.loc[
        df["github_url"] == "No_repo_info_found",
        ["github_url", "github_exists"]
        + (["parent"] if package_manager in SHOW_PARENTS else [])
        + (["command"] if package_manager == "maven" else []),
    ]
    github_repo_404_df = df.loc[
        df["github_exists"] == False,
        ["github_url", "github_exists"]
        + (["parent"] if package_manager in SHOW_PARENTS else [])
        + (["command"] if package_manager == "maven" else []),
    ]
    not_on_github_df = (
        df.loc[
            (df["is_github"] == False) & (df["github_url"] != "No_repo_info_found"),
            ["github_url"]
            + (["parent"] if package_manager in SHOW_PARENTS else [])
            + (["command"] if package_manager == "maven" else []),
        ]
        .reset_index(drop=False)
        .drop_duplicates(subset=["package_name"])
    )
    not_on_github_counts = not_on_github_df.shape[0]

    combined_repo_problems_df = (
        pd.concat([no_source_code_repo_df, github_repo_404_df])
        .reset_index(drop=False)
        .drop_duplicates(subset=["package_name"])
    )
    # could not find SHA/release tag while github exists
    sha_not_found_df = df.loc[
        (df["sha_exists"] == False) & (df["github_exists"] == True),
        (
            [
                "sha_info",
                "tag_info",
            ]
            + (["parent"] if package_manager in SHOW_PARENTS else [])
            + (["command"] if package_manager == "maven" else [])
        ),
    ]
    # all_deprecated_df = df[df["all_deprecated"] is True]
    version_deprecated_df = df.loc[
        df["deprecated_in_version"] == True,
        [
            "deprecated_in_version",
            "all_deprecated",
        ]
        + (["parent"] if package_manager in SHOW_PARENTS else []),
    ]
    forked_package_df = df.loc[
        df["is_fork"] == True,
        (
            [
                "is_fork",
                "github_url",
                "parent_repo_link",
            ]
            + (["parent"] if package_manager in SHOW_PARENTS else [])
            + (["command"] if package_manager == "maven" else [])
        ),
    ]
    provenance_df = df.loc[
        df["provenance_in_version"] == False,
        [
            "provenance_in_version",
        ]
        + (["parent"] if package_manager in SHOW_PARENTS else []),
    ]
    code_signature_df = df.loc[
        df["signature_present"] == False,
        (
            [
                "signature_present",
            ]
            + (["parent"] if package_manager in SHOW_PARENTS else [])
            + (["command"] if package_manager == "maven" else [])
        ),
    ]
    invalid_code_signature_df = df.loc[
        (df["signature_present"] == True) & (df["signature_valid"] == False),
        (
            [
                "signature_valid",
            ]
            + (["parent"] if package_manager in SHOW_PARENTS else [])
            + (["command"] if package_manager == "maven" else [])
        ),
    ]
    aliased_package_df = df.loc[
        df["is_aliased"] == True,
        [
            "aliased_package_name",
        ]
        + (["parent"] if package_manager in SHOW_PARENTS else [])
        + (["command"] if package_manager == "maven" else []),
    ]

    common_counts = {
        "### Total packages in the supply chain": len(df),
    }

    # Only include sections for enabled checks
    warning_counts = {}
    if enabled_checks.get("source_code"):
        warning_counts["no_source_code"] = (
            f":heavy_exclamation_mark: Packages with no source code URL (⚠️⚠️⚠️): {no_source_code_repo_df.shape[0]}"
        )
        warning_counts["github_404"] = (
            f":no_entry: Packages with repo URL that is 404 (⚠️⚠️⚠️): {github_repo_404_df.shape[0]}"
        )

    if enabled_checks.get("source_code_sha"):
        warning_counts["sha_not_found"] = (
            f":wrench: Packages with inaccessible commit SHA/tag (⚠️⚠️): {sha_not_found_df.shape[0]}"
        )

    if enabled_checks.get("deprecated"):
        warning_counts["deprecated"] = f":x: Packages that are deprecated (⚠️⚠️): {version_deprecated_df.shape[0]}"

    if enabled_checks.get("code_signature"):
        warning_counts["code_signature"] = f":lock: Packages without code signature (⚠️⚠️): {code_signature_df.shape[0]}"
        warning_counts["invalid_code_signature"] = (
            f":unlock: Packages with invalid code signature (⚠️⚠️): {invalid_code_signature_df.shape[0]}"
        )

    if enabled_checks.get("forks"):
        warning_counts["forked_package"] = f":cactus: Packages that are forks (⚠️): {(forked_package_df.shape[0])}"

    if enabled_checks.get("provenance"):
        warning_counts["provenance"] = (
            f":black_square_button: Packages without build attestation (⚠️): {provenance_df.shape[0]}"
        )

    if enabled_checks.get("aliased_packages"):
        warning_counts["aliased_packages"] = f":alien: Packages that are aliased (⚠️): {aliased_package_df.shape[0]}"

    source_sus = no_source_code_repo_df.shape[0] + github_repo_404_df.shape[0]

    with open(filename, mode, encoding="utf-8") as md_file:
        preamble = f"""
# Software Supply Chain Report of {project_name} - {release_version}
"""
        if gradual_report:
            preamble += """
\nThis report is a gradual report: that is, only the highest severity smell type with issues found within this project is reported.
Gradual reports are enabled by default. You can disable this feature, and get a full report, by using the `--gradual-report=false` flag.
"""
        preamble += "\n"
        md_file.write(preamble)

        # Section showing which checks were performed
        any_specific = any(enabled_checks.values())
        if any_specific and not gradual_report:
            md_file.write("## Enabled Checks\n")
            md_file.write("The following checks were specifically requested:\n\n")
            for check, enabled in enabled_checks.items():
                if enabled:
                    md_file.write(f"- {check.replace('_', ' ').title()}: `{check}`\n")
            md_file.write("\n---\n\n")
        else:
            md_file.write("All available checks were performed.\n\n---\n\n")

        md_file.write(
            """
<details>
    <summary>How to read the results :book: </summary>
    \n Dirty-waters has analyzed your project dependencies and found different categories for each of them:\n
    \n - ⚠️⚠️⚠️ : high severity \n
    \n - ⚠️⚠️: medium severity \n
    \n - ⚠️: low severity \n
</details>
        """
        )

        md_file.write("\n")

        for key, val in common_counts.items():
            md_file.write(f"\n {key}: {val}\n")
        md_file.write("\n")

        for key, val in warning_counts.items():
            if package_manager in SUPPORTED_SMELLS[key]:
                md_file.write(f"\n{val}\n")
        md_file.write("\n")

        md_file.write("\n### Fine grained information\n")
        md_file.write(
            "\n:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.\n"
        )
        reports = {
            "no_source_code": {
                "enabled": enabled_checks.get("source_code"),
                "function": lambda: no_source_code(combined_repo_problems_df, md_file, source_sus, package_manager),
            },
            "sha_not_found": {
                "enabled": enabled_checks.get("source_code_sha"),
                "function": lambda: sha_not_found(
                    sha_not_found_df, md_file, sha_not_found_df.shape[0], package_manager
                ),
            },
            "deprecated": {
                "enabled": enabled_checks.get("deprecated"),
                "function": lambda: deprecated(
                    version_deprecated_df, md_file, (df["deprecated_in_version"] == True).sum(), package_manager
                ),
            },
            "code_signature": {
                "enabled": enabled_checks.get("code_signature"),
                "function": lambda: code_signature(
                    code_signature_df, md_file, code_signature_df.shape[0], package_manager
                ),
            },
            "invalid_code_signature": {
                "enabled": enabled_checks.get("code_signature"),
                "function": lambda: invalid_code_signature(
                    invalid_code_signature_df, md_file, invalid_code_signature_df.shape[0], package_manager
                ),
            },
            "forked_package": {
                "enabled": enabled_checks.get("forks"),
                "function": lambda: forked_package(
                    forked_package_df, md_file, (df["is_fork"] == True).sum(), package_manager
                ),
            },
            "provenance": {
                "enabled": enabled_checks.get("provenance"),
                "function": lambda: provenance(
                    provenance_df, md_file, (df["provenance_in_version"] == False).sum(), package_manager
                ),
            },
            "aliased_packages": {
                "enabled": enabled_checks.get("aliased_packages"),
                "function": lambda: aliased_package(
                    aliased_package_df, md_file, aliased_package_df.shape[0], package_manager
                ),
            },
        }

        printed = False
        for report in reports:
            if reports[report]["enabled"]:
                printed = reports[report]["function"]()
            if gradual_report and printed:
                md_file.write("\n")
                break

        md_file.write("\n### Call to Action:\n")
        md_file.write(
            """
<details>
<summary>👻What do I do now? </summary>
"""
        )

        if enabled_checks.get("source_code") or enabled_checks.get("source_code_sha"):
            md_file.write(
                """
\nFor packages **without source code & accessible SHA/release tags**:\n
- **Why?** Missing or inaccessible source code makes it impossible to audit the package for security vulnerabilities or malicious code.\n
1. Pull Request to the maintainer of dependency, requesting correct repository metadata and proper versioning/tagging. \n"""
            )

        if enabled_checks.get("deprecated"):
            md_file.write(
                """
\nFor **deprecated** packages:\n
- **Why?** Deprecated packages may contain known security issues and are no longer maintained, putting your project at risk.\n
1. Confirm the maintainer's deprecation intention 
2. Check for not deprecated versions"""
            )

        if enabled_checks.get("code_signature"):
            md_file.write(
                """
\nFor packages **without code signature**:\n
- **Why?** Code signatures help verify the authenticity and integrity of the package, ensuring it hasn't been tampered with.\n
1. Open an issue in the dependency's repository to request the inclusion of code signature in the CI/CD pipeline. \n
\nFor packages **with invalid code signature**:\n
- **Why?** Invalid signatures could indicate tampering or compromised build processes.\n
1. It's recommended to verify the code signature and contact the maintainer to fix the issue."""
            )

        if enabled_checks.get("forks"):
            md_file.write(
                """
\nFor packages **that are forks**:\n
- **Why?** Forked packages may contain malicious code not present in the original repository, and may not receive security updates.\n
1. Inspect the package and its GitHub repository to verify the fork is not malicious."""
            )

        if enabled_checks.get("provenance"):
            md_file.write(
                """
\nFor packages **without provenance**:\n
- **Why?** Without provenance, there's no way to verify that the package was built from the claimed source code, making supply chain attacks possible.\n
1. Open an issue in the dependency's repository to request the inclusion of provenance and build attestation in the CI/CD pipeline."""
            )

        if enabled_checks.get("aliased_packages"):
            md_file.write(
                """
\nFor packages that are **aliased**:\n
- **Why?** Aliased packages may hide malicious dependencies under seemingly legitimate names.\n
1. Check the aliased package and its repository to verify the alias is not malicious."""
            )

        md_file.write("\n</details>\n")

        if enabled_checks.get("source_code") and package_manager in SUPPORTED_SMELLS["no_source_code"]:
            if not_on_github_counts > 0:
                md_file.write("\n### Notes\n")
                md_file.write(
                    f"""
<details>
    <summary>Other info:</summary>
    \n- Source code repo is not hosted on GitHub:  {not_on_github_counts}\n
    This could be due, for example, to the package being hosted on a different platform.\n
    This does not mean that the source code URL is invalid.\n
    However, for non-GitHub repositories, not all checks can currently be performed.\n
"""
                )

                not_on_github_df.index = range(1, len(not_on_github_df) + 1)
                markdown_text = not_on_github_df.reset_index().to_markdown(index=False)
                md_file.write(markdown_text)
                md_file.write("\n</details>\n\n\n")

        md_file.write("---\n")
        md_file.write("\nReport created by [dirty-waters](https://github.com/chains-project/dirty-waters/).\n")
        md_file.write(f"\nReport created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Tool version
        tool_commit_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip().decode("utf-8")
        md_file.write(f"- Tool version: {tool_commit_hash}\n")
        md_file.write(f"- Project Name: {project_name}\n")
        md_file.write(f"- Project Version: {release_version}\n")
        md_file.write(f"- Package Manager: {package_manager}\n")
    print(f"Report from static analysis generated at {filename}")


def get_s_summary(
    data, deps_list, project_name, release_version, package_manager, enabled_checks, gradual_report, summary_filename
):
    """
    Get a summary of the static analysis results.
    """

    df = create_dataframe(data, deps_list, package_manager)
    write_summary(
        df,
        project_name,
        release_version,
        package_manager,
        filename=summary_filename,
        enabled_checks=enabled_checks,
        gradual_report=gradual_report,
        mode="w",
    )
