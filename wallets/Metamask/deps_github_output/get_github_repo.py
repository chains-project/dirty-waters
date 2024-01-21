import os
import subprocess
import re
import json
import sys

def write_output(filename, data):
    with open(filename, 'w') as f:
        if isinstance(data, list):
            f.write("\n".join(data))
            f.write(f"\nTotal: {len(data)}\n")
        else: 
            json.dump(data, f, indent=2)
        

def extract_repo_url(repo_info):
    pattern = r'(github.*)'
    match = re.search(pattern, repo_info, re.IGNORECASE)
    return match.group(1) if match else None

def process_package(package, patches, repos_output, errors, undefined, same_repos_deps, some_errors):
    global not_found_count
    global some_error_count
    
    if "@patch:" in package:
        patches.append(package)
        return

    try:
        result = subprocess.run(
            ["yarn", "info", package, "repository.url"],
            capture_output=True,
            text=True,
            check=True
        )
        
        repo_info = result.stdout

        if repo_info is None or "undefined" in repo_info:
            undefined.append(f"Undefined for {package}")
        else:
            url = extract_repo_url(repo_info)
            if url:
                repos_output.append(url)
                if url not in same_repos_deps:
                    same_repos_deps[url] = []
                same_repos_deps[url].append(package)
            else:
                some_errors.append(f"No GitHub URL for {package}\n{repo_info}")
                

    except subprocess.CalledProcessError as e:
        errors.append(f"Error for {package}: {e.stderr}")



def main(input_file):
    patches = []  # list with @patch packages
    repos_output = []  # List to store GitHub URLs
    errors = []  # List to store packages with errors
    some_errors = []  # List to store packages without a GitHub URL
    undefined = []  # List to store packages with undefined repository URLs
    same_repos_deps = {}  # Dict to store packages with same GitHub URL


    os.makedirs('output', exist_ok=True)


    with open(input_file, 'r') as file:
        lines = file.readlines()[:-1] 
        for line in lines:
            package = line.strip()
            print(f"Processing: {package}")
            process_package(
                package, 
                patches, 
                repos_output, 
                errors, 
                undefined, 
                same_repos_deps, 
                some_errors)

    # Write collected data to files
    unique_repos_output = sorted(set(repos_output))
    outputs = {
        'github_repo_all.txt': repos_output,
        'github_repo_unique.txt': unique_repos_output,
        'github_repo_patch.txt': patches,
        'github_repo_errors.log': errors,
        'github_repo_undefined.log': undefined,
        'github_repo_some_error.log': some_errors,
        'github_repos_depsnsamerepo.json': same_repos_deps,
    }

    for filename, data in outputs.items():
        filepath = os.path.join('output', filename)
        write_output(filepath, data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("you need <input_file_path>")
        sys.exit(1)
    input_file_path = sys.argv[1]
    main(input_file_path)

#latest update: 2024-01-19