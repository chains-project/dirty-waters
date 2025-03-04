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
        source_code_data = package_data.get("source_code", {}) or {}

        match_data = package_data.get("match_info", {}) or {}
        release_tag_exists_info = source_code_data.get("release_tag", {}) or {}

        # Create a row for each package

        row = {
            "package_name": package_name,
            "deprecated_in_version": package_data.get("package_info", {}).get("deprecated_in_version"),
            "provenance_in_version": package_data.get("package_info", {}).get("provenance_in_version"),
            "all_deprecated": package_data.get("package_info", {}).get("all_deprecated", None),
            "signature_present": package_data.get("code_signature", {}).get("signature_present"),
            "signature_valid": package_data.get("code_signature", {}).get("signature_valid"),
            "command": package_data.get("command", None),
            "is_github": source_code_data.get("is_github", False),
            "github_url": source_code_data.get("github_url", "Could not find repo from package registry"),
            "github_exists": source_code_data.get("github_exists", None),
            "github_redirected": source_code_data.get("github_redirected", None),
            "archived": source_code_data.get("archived", None),
            "is_fork": source_code_data.get("is_fork", None),
            "parent_repo_link": source_code_data.get("parent_repo_link", None),
            "forked_from": source_code_data.get("parent_repo_link", "-"),
            "open_issues_count": source_code_data.get("open_issues_count", "-"),
            "is_match": match_data.get("match", None),
            # "release_tag_exists_info": source_code_data.get("release_tag", {}),
            "release_tag_exists": release_tag_exists_info.get("exists", "-"),
            "tag_version": release_tag_exists_info.get("tag_version", "-"),
            "tag_url": release_tag_exists_info.get("url", "-"),
            "tag_related_info": release_tag_exists_info.get("tag_related_info", "-"),
            "status_code_for_release_tag": release_tag_exists_info.get("status_code", "-"),
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


def release_tag_not_found(release_tag_not_found_df, md_file, amount, package_manager):
    """
    Create a section for packages with inaccessible release tags.
    """

    if not release_tag_not_found_df.empty:
        md_file.write(
            f"""
<details>
<summary>List of packages with available source code repos but with inaccessible tags({amount})</summary>
    """
        )

        md_file.write("\n\n\n")
        markdown_text = release_tag_not_found_df.reset_index().to_markdown(index=False)
        md_file.write(markdown_text)
        md_file.write("\n</details>\n")
    elif package_manager not in SUPPORTED_SMELLS["release_tag_not_found"]:
        md_file.write(f"\nThe package manager ({package_manager}) does not support checking for inaccessible tags.\n")
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


def write_summary(
    df, project_name, release_version, package_manager, filename, enabled_checks, gradual_report, mode="w"
):
    """
    Write a summary of the static analysis results to a markdown file.
    """

    no_source_code_repo_df = df.loc[
        df["github_url"] == "No_repo_info_found",
        ["github_url", "github_exists"] + (["command"] if package_manager == "maven" else []),
    ]
    github_repo_404_df = df.loc[
        df["github_exists"] == False,
        ["github_url", "github_exists"] + (["command"] if package_manager == "maven" else []),
    ]
    not_on_github_df = (
        df.loc[
            df["is_github"] == False,
            ["github_url"] + (["command"] if package_manager == "maven" else []),
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
    # could not find release tag while github exists
    release_tag_not_found_df = df.loc[
        (df["release_tag_exists"] == False) & (df["github_exists"] == True),
        (
            [
                "release_tag_exists",
                "tag_version",
                "github_url",
                "tag_related_info",
                "status_code_for_release_tag",
            ]
            + (["command"] if package_manager == "maven" else [])
        ),
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
        (
            [
                "is_fork",
                "github_url",
                "parent_repo_link",
            ]
            + (["command"] if package_manager == "maven" else [])
        ),
    ]
    provenance_df = df.loc[
        df["provenance_in_version"] == False,
        [
            "provenance_in_version",
        ],
    ]
    code_signature_df = df.loc[
        df["signature_present"] == False,
        (["command"] if package_manager == "maven" else []),
    ]
    invalid_code_signature_df = df.loc[
        (df["signature_present"] == True) & (df["signature_valid"] == False),
        (["command"] if package_manager == "maven" else []),
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

    if enabled_checks.get("release_tags"):
        warning_counts["release_tag_not_found"] = (
            f":wrench: Packages with inaccessible GitHub tag (⚠️⚠️): {release_tag_not_found_df.shape[0]}"
        )

    if enabled_checks.get("deprecated"):
        warning_counts["deprecated"] = f":x: Packages that are deprecated (⚠️⚠️): {version_deprecated_df.shape[0]}"

    if enabled_checks.get("forks"):
        warning_counts["forked_package"] = f":cactus: Packages that are forks (⚠️⚠️): {(forked_package_df.shape[0])}"

    if enabled_checks.get("code_signature"):
        warning_counts["code_signature"] = f":lock: Packages without code signature (⚠️⚠️): {code_signature_df.shape[0]}"

    if enabled_checks.get("provenance"):
        warning_counts["provenance"] = (
            f":black_square_button: Packages without build attestation (⚠️): {provenance_df.shape[0]}"
        )

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

        if enabled_checks.get("source_code") and package_manager in SUPPORTED_SMELLS["no_source_code"]:
            if not_on_github_counts > 0:
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
                md_file.write("\n</details>\n")

        md_file.write("\n### Fine grained information\n")
        md_file.write(
            "\n:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.\n"
        )
        reports = {
            "no_source_code": {
                "enabled": enabled_checks.get("source_code"),
                "function": lambda: no_source_code(combined_repo_problems_df, md_file, source_sus, package_manager),
            },
            "release_tag_not_found": {
                "enabled": enabled_checks.get("release_tags"),
                "function": lambda: release_tag_not_found(
                    release_tag_not_found_df, md_file, release_tag_not_found_df.shape[0], package_manager
                ),
            },
            "deprecated": {
                "enabled": enabled_checks.get("deprecated"),
                "function": lambda: deprecated(
                    version_deprecated_df, md_file, (df["deprecated_in_version"] == True).sum(), package_manager
                ),
            },
            "forked_package": {
                "enabled": enabled_checks.get("forks"),
                "function": lambda: forked_package(
                    forked_package_df, md_file, (df["is_fork"] == True).sum(), package_manager
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
            "provenance": {
                "enabled": enabled_checks.get("provenance"),
                "function": lambda: provenance(
                    provenance_df, md_file, (df["provenance_in_version"] == False).sum(), package_manager
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
        For packages without source code & accessible release tags:  \n
        Pull Request to the maintainer of dependency, requesting correct repository metadata and proper tagging. \n
        \nFor deprecated packages:\n
        1. Confirm the maintainer’s deprecation intention 
        2. Check for not deprecated versions
        \nFor packages without provenance:\n
        Open an issue in the dependency’s repository to request the inclusion of provenance and build attestation in the CI/CD pipeline. 
        \nFor packages that are forks\n
        Inspect the package and its GitHub repository to verify the fork is not malicious. \n
        \nFor packages without code signature:\n
        Open an issue in the dependency’s repository to request the inclusion of code signature in the CI/CD pipeline. \n
        \nFor packages with invalid code signature:\n
        It's recommended to verify the code signature and contact the maintainer to fix the issue. \n
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
    print(f"Report from static analysis generated at {filename}")


def get_s_summary(
    data, project_name, release_version, package_manager, enabled_checks, gradual_report, summary_filename
):
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
        gradual_report=gradual_report,
        mode="w",
    )
