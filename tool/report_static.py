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
    "release_tag_not_found": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "deprecated": ["yarn-classic", "yarn-berry", "pnpm", "npm"],
    "forked_package": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "provenance": ["yarn-classic", "yarn-berry", "pnpm", "npm"],
    "code_signature": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
    "invalid_code_signature": ["yarn-classic", "yarn-berry", "pnpm", "npm", "maven"],
}


def load_data(filename):
    """Load data from a JSON file got from static analysis."""

    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def create_dataframe(data):
    """
    Create a dataframe from the data got from static analysis.

    """

    rows = []

    for package_name, package_data in data.items():
        github_exists_data = package_data.get("github_exists", {}) or {}

        match_data = package_data.get("match_info", {}) or {}
        release_tag_exists_info = github_exists_data.get("release_tag", {}) or {}

        # Create a row for each package

        row = {
            "package_name": package_name,
            "deprecated_in_version": package_data.get("package_info", {}).get("deprecated_in_version"),
            "provenance_in_version": package_data.get("package_info", {}).get("provenance_in_version"),
            "all_deprecated": package_data.get("package_info", {}).get("all_deprecated", None),
            "signature_present": package_data.get("code_signature").get("signature_present"),
            "signature_valid": package_data.get("code_signature").get("signature_valid"),
            "github_url": github_exists_data.get("github_url", "Could not find repo from package registry"),
            "github_exists": github_exists_data.get("github_exists", None),
            "github_redirected": github_exists_data.get("github_redirected", None),
            "archived": github_exists_data.get("archived", None),
            "is_fork": github_exists_data.get("is_fork", None),
            "parent_repo_link": github_exists_data.get("parent_repo_link", None),
            "forked_from": github_exists_data.get("parent_repo_link", "-"),
            "open_issues_count": github_exists_data.get("open_issues_count", "-"),
            "is_match": match_data.get("match", None),
            # "release_tag_exists_info": github_exists_data.get("release_tag", {}),
            "release_tag_exists": release_tag_exists_info.get("exists", "-"),
            "tag_version": release_tag_exists_info.get("tag_version", "-"),
            "tag_url": release_tag_exists_info.get("url", "-"),
            "tag_related_info": release_tag_exists_info.get("tag_related_info", "-"),
            "status_code_for_release_tag": release_tag_exists_info.get("status_code", "-"),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    return df.set_index("package_name")


def write_summary(df, project_name, release_version, package_manager, filename, enabled_checks, mode="w"):
    """
    Write a summary of the static analysis results to a markdown file.
    """

    no_source_code_repo_df = df.loc[df["github_url"] == "No_repo_info_found", ["github_url", "github_exists"]]
    github_repo_404_df = df.loc[df["github_exists"] == False, ["github_url", "github_exists"]]

    combined_repo_problems_df = (
        pd.concat([no_source_code_repo_df, github_repo_404_df])
        .reset_index(drop=False)
        .drop_duplicates(subset=["package_name"])
    )
    # could not find release tag while github exists
    release_tag_not_found_df = df.loc[
        (df["release_tag_exists"] == False) & (df["github_exists"] == True),
        [
            "release_tag_exists",
            "tag_version",
            "github_url",
            "tag_related_info",
            "status_code_for_release_tag",
        ],
    ]
    # all_deprecated_df = df[df["all_deprecated"] is True]
    version_deprecated_df = df.loc[
        df["deprecated_in_version"] == True,
        [
            "deprecated_in_version",
            "all_deprecated",
        ],
    ]
    forked_package_df = df.loc[
        df["is_fork"] == True,
        [
            "is_fork",
            "parent_repo_link",
        ],
    ]
    provenance_df = df.loc[
        df["provenance_in_version"] == False,
        [
            "provenance_in_version",
        ],
    ]
    code_signature_df = df.loc[
        df["signature_present"] == False,
        [
            "signature_present",
        ],
    ]
    invalid_code_signature_df = df.loc[
        (df["signature_present"] == True) & (df["signature_valid"] == False),
        [
            "signature_valid",
        ],
    ]

    common_counts = {
        "### Total packages in the supply chain": len(df),
    }

    # Only include sections for enabled checks
    warning_counts = {}
    if enabled_checks.get("source_code"):
        warning_counts["no_source_code"] = (
            f":heavy_exclamation_mark: Packages with no Source Code URL(⚠️⚠️⚠️) {(df['github_url'] == 'No_repo_info_found').sum()}"
        )
        warning_counts["github_404"] = (
            f":no_entry: Packages with Github URLs that are 404(⚠️⚠️⚠️) {(df['github_exists'] == False).sum()}"
        )

    if enabled_checks.get("release_tags"):
        warning_counts["release_tag_not_found"] = (
            f":wrench: Packages with accessible source code repos but inaccessible GitHub tags(⚠️⚠️⚠️) {(release_tag_not_found_df.shape[0])}"
        )

    if enabled_checks.get("deprecated"):
        warning_counts["deprecated"] = (
            f":x: Packages that are deprecated(⚠️⚠️) {(df['deprecated_in_version'] == True).sum()}"
        )

    if enabled_checks.get("forks"):
        warning_counts["forked_package"] = f":cactus: Packages that are forks(⚠️⚠️) {(df['is_fork'] == True).sum()}"

    if enabled_checks.get("code_signature"):
        warning_counts["code_signature"] = f":lock: Packages without code signature(⚠️⚠️) {(code_signature_df.shape[0])}"

    if enabled_checks.get("provenance"):
        warning_counts["provenance"] = (
            f":black_square_button: Packages without provenance(⚠️) {(df['provenance_in_version'] == False).sum()}"
        )

    not_on_github_counts = (df["github_url"] == "Not_github_repo").sum()

    source_sus = (df["github_url"] == "No_repo_info_found").sum() + (df["github_exists"] == False).sum()

    with open(filename, mode, encoding="utf-8") as md_file:
        md_file.write(f"# Software Supply Chain Report of {project_name} - {release_version}\n\n")

        # Section showing which checks were performed
        any_specific = any(enabled_checks.values())
        if any_specific:
            md_file.write("## Enabled Checks\n")
            md_file.write("The following checks were specifically requested:\n\n")
            for check, enabled in enabled_checks.items():
                if enabled:
                    md_file.write(f"- {check.replace('_', ' ').title()}\n")
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

        # md_file.write(f"#### Other info")

        if enabled_checks.get("source_code") and package_manager not in SUPPORTED_SMELLS["no_source_code"]:
            md_file.write(
                f"""
<details>
    <summary>Other info:</summary>
    \n- Source code repo is not hosted on github:  {not_on_github_counts} \n
</details>
                        
                        """
            )
            md_file.write("\n\n")

        md_file.write("\n### Fine grained information\n")
        md_file.write(
            "\n:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.\n"
        )

        if not combined_repo_problems_df.empty:
            md_file.write(
                f"""
<details>
    <summary>Source code links that could not be found({source_sus})</summary>
        """
            )
            md_file.write("\n\n\n")
            combined_repo_problems_df.index = range(1, len(combined_repo_problems_df) + 1)
            markdown_text = combined_repo_problems_df.reset_index().to_markdown(index=False)
            md_file.write(markdown_text)
            md_file.write("\n</details>")
        elif package_manager not in SUPPORTED_SMELLS["github_404"]:
            md_file.write(
                f"\nThe package manager ({package_manager}) does not support checking for not found source code links.\n"
            )
        else:
            md_file.write("All analyzed packages have a source code repo.\n")

        if enabled_checks.get("release_tags") and not release_tag_not_found_df.empty:
            md_file.write(
                f"""

<details>
    <summary>List of packages with available source code repos but with inaccessible tags({(release_tag_not_found_df.shape[0])})</summary>
        """
            )
            md_file.write("\n\n\n")
            markdown_text = release_tag_not_found_df.reset_index().to_markdown(index=False)
            md_file.write(markdown_text)
            md_file.write("\n</details>")
        elif package_manager not in SUPPORTED_SMELLS["release_tag_not_found"]:
            md_file.write(
                f"\nThe package manager ({package_manager}) does not support checking for inaccessible tags.\n"
            )
        else:
            md_file.write("\nAll packages have accessible tags.\n")

        if enabled_checks.get("deprecated"):
            if not version_deprecated_df.empty:
                md_file.write(
                    f"""
    <details>
        <summary>List of deprecated packages({(df['deprecated_in_version'] == True).sum()})</summary>
            """
                )
                md_file.write("\n\n\n")
                markdown_text = version_deprecated_df.reset_index().to_markdown(index=False)
                md_file.write(markdown_text)
                md_file.write("\n</details>")
            elif package_manager not in SUPPORTED_SMELLS["deprecated"]:
                md_file.write(
                    f"\nThe package manager ({package_manager}) does not support checking for deprecated packages.\n"
                )
            else:
                md_file.write("\nNo deprecated package found.\n")

        if enabled_checks.get("forks"):
            if not forked_package_df.empty:
                md_file.write(
                    f"""

    <details>
        <summary>List of packages from fork({(df["is_fork"] == True).sum()}) </summary>
            """
                )
                md_file.write("\n\n\n")
                markdown_text = forked_package_df.reset_index().to_markdown(index=False)
                md_file.write(markdown_text)
                md_file.write("\n</details>\n")
            elif package_manager not in SUPPORTED_SMELLS["forked_package"]:
                md_file.write(
                    f"\nThe package manager ({package_manager}) does not support checking for forked packages.\n"
                )
            else:
                md_file.write("\nNo package is from fork.\n")

        if enabled_checks.get("provenance"):
            if not provenance_df.empty:
                md_file.write(
                    f"""
    <details>
        <summary>List of packages without provenance({(df["provenance_in_version"] == False).sum()})</summary>
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

        if not code_signature_df.empty:
            md_file.write(
                f"""
<details>
    <summary>List of packages without code signature({(code_signature_df.shape[0])})</summary>
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

        if not invalid_code_signature_df.empty:
            md_file.write(
                f"""
<details>
    <summary>List of packages with an existing but invalid code signature({(invalid_code_signature_df.shape[0])})</summary>
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

        md_file.write("\n### Call to Action:\n")
        md_file.write(
            """
                      
<details>
    <summary>👻What do I do now? </summary>
        For packages without source code & accessible release tags:  \n
        Pull Request to the maintainer of dependency, requesting correct repository metadata and proper tagging. \n
        \nFor deprecated packages:\n
        1. Confirm the maintainer’s deprecation intention 
        2. Check for not deprecated versions
        \nFor packages without provenance:\n
        Open an issue in the dependency’s repository to request the inclusion of provenance and build attestation in the CI/CD pipeline. 
        \nFor packages that are forks\n
        Inspect the package and its GitHub repository to verify the fork is not malicious.
</details>



"""
        )
        md_file.write("---\n")
        md_file.write("\nReport created by [dirty-waters](https://github.com/chains-project/dirty-waters/).\n")
        md_file.write(f"\nReport created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Tool version
        tool_commit_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip().decode("utf-8")
        md_file.write(f"- Tool version: {tool_commit_hash}\n")
        md_file.write(f"- Project Name: {project_name}\n")
        md_file.write(f"- Project Version: {release_version}\n")


def get_s_summary(data, project_name, release_version, package_manager, enabled_checks, summary_filename):
    """
    Get a summary of the static analysis results.
    """

    df = create_dataframe(data)
    write_summary(
        df,
        project_name,
        release_version,
        package_manager,
        filename=summary_filename,
        enabled_checks=enabled_checks,
        mode="w",
    )
    print(f"Report created at {summary_filename}")
