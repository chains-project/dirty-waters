import pandas as pd
import json
from datetime import datetime


def load_data(filename):
    with open(filename) as f:
        return json.load(f)


def create_dataframe(data):
    rows = []

    for package_name, package_data in data.items():
        github_exists_data = package_data.get("github_exists", {}) or {}

        match_data = package_data.get("match_info", {}) or {}

        # Create a row for each package

        row = {
            "package_name": package_name,
            "deprecated_in_version": package_data["npm_package_info"].get(
                "deprecated_in_version"
            ),
            "provenance_in_version": package_data["npm_package_info"].get(
                "provenance_in_version"
            ),
            "all_deprecated": package_data["npm_package_info"].get(
                "all_deprecated", None
            ),
            "github_url": github_exists_data.get(
                "github_url", "Could not find repo from package registry"
            ),
            "github_exists": github_exists_data.get("github_exists", None),
            "github_redirected": github_exists_data.get("github_redireted", None),
            "archived": github_exists_data.get("archived", None),
            "is_fork": github_exists_data.get("is_fork", None),
            "forked_from": github_exists_data.get("parent_repo_link", "-"),
            "open_issues_count": github_exists_data.get("open_issues_count", "-"),
            "is_match": match_data.get("match", None),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.set_index("package_name")


def write_summary(df, wallet_name, release_version, filename, mode="w"):
    No_source_code_repo_df = df.loc[
        df["github_url"] == "No_repo_info_found", ["github_url", "github_exists"]
    ]
    github_repo_404_df = df.loc[
        df["github_exists"] == False, ["github_url", "github_exists"]
    ]

    combined_repo_problems_df = (
        pd.concat([No_source_code_repo_df, github_repo_404_df])
        .reset_index(drop=False)
        .drop_duplicates(subset=["package_name"])
    )

    # all_deprecated_df = df[df["all_deprecated"] is True]
    version_deprecated_df = df[df["deprecated_in_version"] == True]
    forked_package_df = df[df["is_fork"] == True]
    # unarchived_deprecated_packages_count = all_deprecated_df[
    #     all_deprecated_df["archived"] is not True
    # ].shape[0]

    common_counts = {
        "### Total packages in the supply chain:": len(df),
    }

    warning_counts = {
        ":heavy_exclamation_mark: Packages with no Source Code URL(⚠️⚠️⚠️)": (
            df["github_url"] == "No_repo_info_found"
        ).sum(),
        ":no_entry: Packages with Github URLs that are 404(⚠️⚠️⚠️)": (
            df["github_exists"] == False
        ).sum(),
        ":x: Packages that are deprecated(⚠️⚠️)": (
            df["deprecated_in_version"] == True
        ).sum(),
        ":black_square_button: Packages without provenance(⚠️)": (
            df["provenance_in_version"] == False
        ).sum(),
        ":cactus: Packages that are forks(⚠️)": (df["is_fork"] == True).sum(),
    }

    not_on_github_counts = (df["github_url"] == "Not_github_repo").sum()
    name_not_match_counts = (df["is_match"] == False).sum()

    source_sus = (df["github_url"] == "No_repo_info_found").sum() + (
        df["github_exists"] == False
    ).sum()

    with open(filename, mode) as md_file:
        md_file.write(f"# Transparency Report of {wallet_name} - {release_version}\n")
        md_file.write("\n")

        md_file.write(f"""
<details>
    <summary>How to read the results :book: </summary>
    \n Dirty-waters has analyzed your project dependencies and found different categories for each of them:\n
    \n - ⚠️⚠️⚠️ : severe \n
    \n - ⚠️⚠️: moderate \n
    \n - ⚠️: precaution \n
</details>
        """)

        md_file.write("\n")

        for key, val in common_counts.items():
            md_file.write(f"\n {key}: {val}\n")
        md_file.write("\n")

        for key, val in warning_counts.items():
            md_file.write(f"\n{key}: {val}\n")
        md_file.write("\n")

        # md_file.write(f"#### Other info")

        md_file.write(f"""
<details>
    <summary>Other info:</summary>
     \n- Source code repo is not hosted on github:  {not_on_github_counts} \n
     \n- Name not match: {name_not_match_counts} \n
</details>
                      
                      """)

        md_file.write("\n\n")
        # md_file.write("\n---\n")
        md_file.write("\n### Fine grained information\n")
        md_file.write(
            "\n:dolphin: For further information about package transparency in your project, take a look at the following tables.\n"
        )

        if not combined_repo_problems_df.empty:
            md_file.write(f"""
<details>
    <summary>Source code could not be found({source_sus})</summary>
        """)
            md_file.write("\n\n\n")
            combined_repo_problems_df.index = range(
                1, len(combined_repo_problems_df) + 1
            )
            markdown_text = combined_repo_problems_df.reset_index().to_markdown(
                index=False
            )
            md_file.write(markdown_text)
            md_file.write("\n</details>")
        else:
            md_file.write(f"No package doesn't have source code repo.\n")

        if not version_deprecated_df.empty:
            md_file.write(f"""
<details>
    <summary>List of deprecated packages({(df['deprecated_in_version'] == True).sum()})</summary>
        """)
            # md_file.write("\n\n## List of deprecated packages:\n")
            md_file.write("\n\n\n")
            markdown_text = version_deprecated_df.reset_index().to_markdown(index=False)
            md_file.write(markdown_text)
            md_file.write("\n</details>")
        else:
            md_file.write(f"No deprecated package found.\n")

        if not forked_package_df.empty:
            md_file.write(f"""
                      
<details>
    <summary>List of packages from fork({(df["is_fork"] == True).sum()}) </summary>
        """)
            md_file.write("\n\n\n")
            markdown_text = forked_package_df.reset_index().to_markdown(index=False)
            md_file.write(markdown_text)
            md_file.write("\n</details>\n")
        else:
            md_file.write("\nNo package is from fork.\n")

        md_file.write(f"\n### Call to Action:\n")
        md_file.write(f"""
                      
<details>
    <summary>👻What do I do now? </summary>
        For packages without source code:  \n
        1. Reevaluate the dependency usage 
        2. Check if it is deprecated 
        3. Pull Request to developer (from the dependency) to ask for updating the metadata 
        \nFor deprecated packages:\n
        1. Check for not deprecated versions
        2. If all versions deprecated, confirm maintainer's reason/declaration
        \nFor packages without provenance:\n
        1. Open an issue on the dependency repository to get provenance  
        \nFor packages that are forks\n
        1. To verify the GitHub repository to prevent using malicious fork
</details>



""")
        md_file.write(f"---\n")
        md_file.write(
            f"\nReport created by [dirty-waters](https://github.com/chains-project/dirty-waters/) - version: commit.\n"
        )
        md_file.write(
            f"\nReport created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        # Tool version
        # tool_commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('utf-8')
        # md_file.write(f"- Tool version: {tool_commit_hash}\n")
        md_file.write(f"- Wallet Name: {wallet_name}\n")
        md_file.write(f"- Wallet Version: {release_version}\n")


def get_s_summary(data, wallet_name, release_version, summary_filename):
    df = create_dataframe(data)
    write_summary(df, wallet_name, release_version, filename=summary_filename, mode="w")
