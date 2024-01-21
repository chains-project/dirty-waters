import sys
import argparse
import json
from operator import itemgetter
from datetime import datetime
import os

parser = argparse.ArgumentParser(
    description='Generate a markdown report to repos sorted by different criteria such as Contributor Count, Commit Count and Last Commit Date')
parser.add_argument('-s', '--sort', 
    choices=['commit_count', 'contributor_count', 'last_commit_date'], 
    default='contributor_count', 
    help='The criteria to sort the repos by. default: contributor_count.')
parser.add_argument('-f', '--file',
    required=True,
    help='The JSON file to read from.')

args = parser.parse_args()
sort_by = args.sort

file_name = args.file

current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d %H:%M:%S")

with open(file_name, 'r') as file:
    repos = json.load(file)

def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

def sort_repos(repos, sort_key):
    if sort_key == 'last_commit_date':
        return sorted(repos, key=lambda x: (parse_date(x['last_commit_date'])))
    elif sort_key == 'commit_count':
        return sorted(repos, key=lambda x: x['commit_count'])
    elif sort_key == 'contributor_count':
        return sorted(repos, key=lambda x: (x['contributor_count'], parse_date(x['last_commit_date'])))
    else:
        raise ValueError("Invalid sort key.")


# contributor_count categories
less_than_1 = sum(1 for repo in repos if repo["contributor_count"] < 1)
equal_to_1 = sum(1 for repo in repos if repo["contributor_count"] == 1)
less_than_5 = sum(1 for repo in repos if 1<repo["contributor_count"] < 5)
less_than_20 = sum(1 for repo in repos if 5 <= repo["contributor_count"] < 20)
less_than_50 = sum(1 for repo in repos if 20 <= repo["contributor_count"] < 50)
more_than_50 = sum(1 for repo in repos if repo["contributor_count"] >= 50)



sorted_repos = sort_repos(repos, sort_by)


markdown_content = f"""# Summary
[//]: Generated on {formatted_date} from {file_name}

## Contributor Count Statistics

| Contributor Count Range | Repository Count |
|-------------------------|------------------|
| Less than 1             | {less_than_1}    |
| Equal to 1              | {equal_to_1}     |
| Less than 5             | {less_than_5}    |
| Less than 20            | {less_than_20}   |
| Less than 50            | {less_than_50}   |
| More than 50            | {more_than_50}   |
| Total                   | {len(repos)}     |
| Check                   | {less_than_1 + equal_to_1 + less_than_5 + less_than_20 + less_than_50 + more_than_50} |


"""



markdown_repos_sorted = """
## Repositories Sorted by {sort_key}
| Repository | Commit Count | Contributor Count | Last Commit Date |
|------------|--------------|-------------------|------------------|
""".format(sort_key=sort_by.capitalize().replace("_", " "))

for repo in sorted_repos:
    last_commit_datetime = parse_date(repo['last_commit_date'])
    markdown_repos_sorted += "| {} | {} | {} | {} |\n".format(repo["repository"], repo["commit_count"], repo["contributor_count"], last_commit_datetime)

markdown_content += markdown_repos_sorted
base_name, extension = os.path.splitext(file_name)
report_name = f"{base_name}_report_{sort_by}.md"

with open(report_name, "w") as md_file:
    md_file.write(markdown_content)

print(f"Markdown report {report_name} has been successfully created.")
