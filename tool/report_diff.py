import pandas as pd
from datetime import datetime
import logging


def process_data(data):
    record = []
    record_dict = {}
    author_dict = {}

    for package_name, info in data.items():
        repo_name = info.get("repo_name", "")
        pkg_category = info.get("category", "")
        old_version = info.get("tag1", "")
        new_version = info.get("tag2", "")
        repo_link = info.get("repo_link", "")

        # The 'or' is to handle the case where the information returned is None
        commits = info.get("authors", []) or []

        if not commits:
            record.append(
                {
                    "package_name": package_name,
                    "repo_name": repo_name,
                    "repo_link": repo_link,
                    "category": pkg_category,
                    "old_version": old_version,
                    "new_version": new_version,
                    "sha": None,
                    "author": None,
                    "author_first": None,
                    "merger": None,
                    "prr_first": None,
                    "reviewer": None,
                    "reviewer_type": None,
                }
            )

        for commit in commits:
            sha = commit.get("sha", "")
            author = commit.get("login", "")
            author_first = commit.get("commit_result", {}).get("is_first_commit", "")

            commit_merge_infos = commit.get("commit_merged_info", [])

            prr_first = None
            reviewer = None
            reviewer_type = None
            merger = None

            for commit_merge_info in commit_merge_infos:
                merger = commit_merge_info.get("merge_by", "")
                if "reviews" in commit_merge_info and isinstance(commit_merge_info["reviews"], list):
                    for review in commit_merge_info["reviews"]:
                        if isinstance(review, dict) and "prr_data" in review:
                            reviewer = review.get("review_author")
                            reviewer_type = review.get("review_author_type")
                            prr_data = review.get("prr_data", {})
                            if prr_data:
                                prr_first = prr_data.get("is_first_prr")

                if sha in record_dict:
                    if package_name not in record_dict[sha]["package_name"]:
                        record_dict[sha]["package_name"].append(package_name)
                else:
                    record_dict[sha] = {
                        "package_name": [package_name],
                        "repo_name": repo_name,
                        "old_version": old_version,
                        "new_version": new_version,
                        "sha": sha,
                        "author": author,
                        "author_first": author_first,
                        "merger": merger,
                        "prr_first": prr_first,
                        "reviewer": reviewer,
                        "reviewer_type": reviewer_type,
                    }

                package_number = len(record_dict[sha]["package_name"])
                record_dict[sha]["package_number"] = package_number

            record.append(
                {
                    "package_name": package_name,
                    "repo_name": repo_name,
                    "category": pkg_category,
                    "old_version": old_version,
                    "new_version": new_version,
                    "sha": sha,
                    "author": author,
                    "author_first": author_first,
                    "merger": merger,
                    "prr_first": prr_first,
                    "reviewer": reviewer,
                    "reviewer_type": reviewer_type,
                }
            )

    record_list = list(record_dict.values())
    author_list = list(author_dict.values())

    return record, record_list, author_list


def create_dataframe(record):
    df = pd.DataFrame(record)
    return df


def filter_df(df):
    df_author_first = df[(df["author_first"] == True)]
    df_review_first = df[df["prr_first"] == True]
    df_both_first = df[(df["author_first"] == True) & (df["prr_first"] == True)]

    return df_author_first, df_review_first, df_both_first

def print_check_info(df, summary, md_file, amount):
    if amount > 0:
        md_file.write("\n")
        md_file.write(
            f"""
<details>
    <summary>{summary} ({amount})</summary>
        """
        )
        md_file.write("\n\n\n")
        md_file.write(df.to_markdown(index=False))
        md_file.write("\n</details>\n")
        return True
    return False

def generate_diff_report(data, project_repo_name, release_version_old, release_version_new, gradual_report, output_file):
    logging.info(f"Generating differential report for {project_repo_name}")
    record, record_list, author_list = process_data(data)

    df_all = create_dataframe(record)

    # To know downgraded packages
    downgraded = df_all["category"] == "Downgraded package"
    downgraded_number = df_all[downgraded]["package_name"].nunique()
    selected_columns = [
        "package_name",
        "repo_link",
        "category",
        "old_version",
        "new_version",
    ]
    df_down_selected = df_all[downgraded][selected_columns]
    df_down_selected_without_index = df_down_selected.reset_index(drop=True)

    # We want a table that indexes the author
    df_author = pd.DataFrame(record_list).set_index("author")

    new_order = ["sha"] + [col for col in df_author.columns if col != "sha"]
    df_author = df_author.reindex(columns=new_order)

    df_author_new_author, df_author_new_reviewer, df_author_both_new = filter_df(df_author)

    # know the columns

    profile_url = "https://github.com/"

    cp_df_author_new_author = df_author_new_author.copy()
    cp_df_author_new_author.index = df_author_new_author.index.map(lambda x: f"[{x}]({profile_url}{x})")
    # df_author_new_author.loc[:,"author"] = df_author_new_author.loc[:,"author"].map(lambda x: f"[{x}]({profile_url}{x})")

    cp_df_author_new_reviewer = df_author_new_reviewer.copy()
    cp_df_author_new_reviewer["reviewer"] = df_author_new_reviewer["reviewer"].apply(
        lambda x: f"[{x}]({profile_url}{x})"
    )

    cp_df_author_both_new = df_author_both_new.copy()
    cp_df_author_both_new.index = df_author_both_new.index.map(lambda x: f"[{x}]({profile_url}{x})")
    cp_df_author_both_new["reviewer"] = df_author_both_new["reviewer"].apply(lambda x: f"[{x}]({profile_url}{x})")

    new_author_commits = df_author_new_author.shape[0]
    new_reviewer_commits = df_author_new_reviewer.shape[0]
    both_new_commits = df_author_both_new.shape[0]

    signature_changes = df_all[df_all["category"] == "Upgraded package with signature changes"]
    signature_changes_number = signature_changes["package_name"].nunique()

    reports = {
        "signature_changes": {
            "amount": signature_changes_number,
            "df": signature_changes_df,
            "summary": ":lock: Packages with signature changes (⚠️⚠️⚠️)",
        },
        "downgraded": {
            "amount": downgraded_number,
            "df": df_down_selected_without_index,
            "summary": ":heavy_exclamation_mark: Downgraded packages (⚠️⚠️)",
        },
        "both_new": {
            "amount": both_new_commits,
            "df": cp_df_author_both_new,
            "summary": ":alien: Commits made by both New Authors and Reviewers (⚠️⚠️)",
        },
        "new_reviewer": {
            "amount": new_reviewer_commits,
            "df": cp_df_author_new_reviewer,
            "summary": ":see_no_evil: Commits approved by New Reviewers (⚠️⚠️)",
        },
        "new_author": {
            "amount": new_author_commits,
            "df": cp_df_author_new_author,
            "summary": ":neutral_face: Commits made by New Authors (⚠️)",
        },
    }

    # We write into a markdown file
    with open(output_file, "w", encoding="utf-8") as f:
        preamble = f"""
# Software Supply Chain Report of {project_repo_name} - {release_version_old} &rarr; {release_version_new}
"""
        if gradual_report:
            preamble += """
\nThis report is a gradual report: that is, only the highest severity smell type with issues found within this project is reported.
Gradual reports are enabled by default. You can disable this feature, and get a full report, by setting the `--gradual-report` flag to `false`.
"""
        preamble += "\n"
        f.write(preamble)

        for info in reports.values():
            f.write(f"\n {info["summary"]}: ({info["amount"]})\n")

        f.write("\n")
        f.write("### Fine grained information\n")
        f.write(
            "\n:dolphin: For further information about software supply chain smells in your project, take a look at the following tables.\n"
        )

        for info in reports.values():
            printed = print_check_info(info["df"], info["summary"], f, info["amount"])
            if gradual_report and printed:
                f.write("\n")
                break

        if signature_changes_number > 0:
            f.write("\n")
            f.write(
                f"""
    <details>
        <summary>Packages with signature changes</summary>
                """
            )
            f.write("\n\n\n")
            selected_columns = ["package_name", "old_version", "new_version", "signature_changes"]
            signature_changes_df = signature_changes[selected_columns]
            f.write(signature_changes_df.to_markdown(index=False))
            f.write("\n")
            f.write("</details>")
            f.write("\n")

        if both_new_commits > 0:
            f.write("\n")
            f.write(
                f"""
<details>
            <summary>Both Authors and Reviewers are new to the repository </summary>
                """
            )
            f.write("\n\n\n")
            f.write(cp_df_author_both_new.to_markdown(index=True))
            f.write("\n")
            f.write("</details>")

        if new_author_commits > 0:
            f.write("\n")
            f.write(
                f"""
<details>
            <summary>Authors are new to the repository </summary>
                    """
            )
            f.write("\n\n\n")
            f.write(cp_df_author_new_author.to_markdown(index=True))
            f.write("\n")
            f.write("</details>")

        if new_reviewer_commits > 0:
            f.write("\n")
            f.write(
                f"""
<details>
            <summary>Reviewers are new to the repository </summary>
                """
            )
            f.write("\n\n\n")
            f.write(cp_df_author_new_reviewer.to_markdown(index=True))
            f.write("\n")
            f.write("</details>")

        f.write(f"---\n")
        f.write(
            f"\nReport created by [dirty-waters](https://github.com/chains-project/dirty-waters/) - version: commit.\n"
        )
        f.write(f"\nReport created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Tool version
        # tool_commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('utf-8')
        # md_file.write(f"- Tool version: {tool_commit_hash}\n")
        f.write(f"- project Name: {project_repo_name}\n")
        f.write(f"- Compared project Versions: {release_version_old} & {release_version_new}\n")
    print(f"Report from differential analysis generated at {output_file}")
