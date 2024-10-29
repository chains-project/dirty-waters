import pandas as pd
from datetime import datetime


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

        commits = info.get("authors", [])

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


def generate_diff_report(data, project_repo_name, release_version_old, release_version_new, output_file):
    print(f"Generating differential report for {project_repo_name}")
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

    counts = {
        ":heavy_exclamation_mark: Downgraded packages": downgraded_number,
        ":alien: Commits made by both New Authors and Reviewers": both_new_commits,
        ":neutral_face: Commits made by New Authors": new_author_commits,
        ":see_no_evil: Commits approved by New Reviewers": new_reviewer_commits,
    }

    # We write into a markdown file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Differential Report of {project_repo_name} - {release_version_old} & {release_version_new}\n")
        f.write("\n")

        for key, val in counts.items():
            f.write(f"\n {key}: {val}\n")
            f.write("\n")

        f.write("### Fine grained information\n")

        if downgraded_number > 0:
            f.write("\n")
            f.write(
                f"""
<details>
            <summary>Downgraded packages</summary>
                        """
            )
            f.write("\n\n\n")
            f.write(df_down_selected_without_index.to_markdown(index=True))
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
    print(f"Report generated at {output_file}")
