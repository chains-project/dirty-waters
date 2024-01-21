
import os
import requests
import sys
import json
from time import sleep, time
from tqdm import tqdm

#generate json file contains commit_count, contributor_count, last_commit_date


def request_paged_data(api_url, headers, max_pages=None):
    items = []
    page = 1
    first_item = None
    exceeded_limit = False 
    while True:
        # if page > max_pages:
        #     exceeded_limit = True
        #     break
        response = requests.get(f"{api_url}?per_page=100&page={page}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if len(data) == 0:
                break
            if page == 1 and data:
                first_item = data[0] 
            items.extend(data)
            page += 1

        elif response.status_code == 202:
            time_to_wait = 10
            time_started_waiting = time()
            while time() - time_started_waiting < time_to_wait:
                sleep(1)
            continue
        else:
            raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
        
        sleep(0.5)  
    
    return items, first_item, exceeded_limit

def get_repository_stats(user_repo_path, headers, max_pages=None):
    commits_url = f"https://api.github.com/repos/{user_repo_path}/commits"
    contributors_url = f"https://api.github.com/repos/{user_repo_path}/contributors"

    commits, latest_commit, commits_exceeded = request_paged_data(commits_url, headers, max_pages)
    contributors, _, contributors_exceeded = request_paged_data(contributors_url, headers, max_pages)

    commit_count = len(commits)
    contributor_count = len(contributors)
    last_commit_date = latest_commit['commit']['author']['date'] if latest_commit else None

    return commit_count, contributor_count, last_commit_date,commits_exceeded, contributors_exceeded

def save_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def main(input_file):
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)
    headers = {
        'Authorization': f'Bearer {os.getenv("GITHUB_API_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json',
    }


    with open(input_file, 'r') as file:
        repo_urls = [line.strip() for line in file.readlines()]

    max_pages = 100
    save_interval = 10
    repository_stats = []
    errors = {}
    exceeding_limit_repos = []

    total_repos = len(repo_urls) 
    for repo_url in tqdm(repo_urls, desc="Processing", unit="repo"):
        user_repo_path = '/'.join(repo_url.split('/')[-2:]).replace('.git', '')
        try:
            commit_count, contributor_count, last_commit_date, commits_exceeded, contributors_exceeded = get_repository_stats(user_repo_path, headers, max_pages)
            stats = {
                'repository': user_repo_path,
                'repo_url': repo_url,
                'commit_count': commit_count,
                'contributor_count': contributor_count,
                'last_commit_date': last_commit_date,
                # 'commits_exceeded': commits_exceeded,
                # 'contributors_exceeded': contributors_exceeded
            }
            repository_stats.append(stats)
            # if stats['commits_exceeded'] or stats['contributors_exceeded']:
            #     exceed_info = {
            #         'repo_url': repo_url,
            #         'commits_exceeded': commits_exceeded,
            #         'contributors_exceeded': contributors_exceeded
            #     }
            #     exceeding_limit_repos.append(exceed_info)  
        except Exception as e:
            print(f"Error processing {user_repo_path}: {e}")
            error_info = {
                'repo_url': repo_url,
                'error': str(e)
            }
            if isinstance(e, requests.HTTPError):
                error_info['status_code'] = e.response.status_code
                error_info['message'] = e.response.reason
            elif isinstance(e, requests.RequestException):
                error_info['status_code'] = 'N/A'
                error_info['message'] = str(e)
            else: 
                error_info['status_code'] = 'N/A'
                error_info['message'] = 'Unknown Error'
            errors[user_repo_path] = error_info

        if (len(repository_stats) % save_interval == 0) or (len(repository_stats) == total_repos):
            save_to_file(repository_stats, 'repository_stats_intermediate.json')
            save_to_file(errors, 'repository_errors_intermediate.json')
            # save_to_file(exceeding_limit_repos, 'exceeding_limit_repos_intermediate.json')
            print(f"Saved intermediate results after processing {len(repository_stats)} repositories.")

        sleep(0.5)

    save_to_file(repository_stats, 'repository_stats.json')
    save_to_file(errors, 'repository_errors.json')
    # save_to_file(exceeding_limit_repos, 'exceeding_limit_repos.json')
    print(f"Processed {len(repository_stats)} repositories with {len(exceeding_limit_repos)} exceeding_limit_repos, {len(errors)} errors.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file>")
        sys.exit(1)
    main(sys.argv[1])

