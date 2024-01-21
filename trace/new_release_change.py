import subprocess
import re
import json
import sys

def run_git_command(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:  
        raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
    return result.stdout.strip()

def handle_lines(new_version, old_version, *file_paths):
    new_path = file_paths[-1]
    authors = list(set(run_git_command(['git', 'log', '--format=%aN', f'{old_version}..{new_version}', '--', new_path]).split('\n')))
    return {'file': new_path, 'authors': authors}

def handle_files(new_version, *file_paths):  
    new_path = file_paths[-1]
    old_path = file_paths[0]
    
    authors = list(set(run_git_command(['git', 'log', '--format=%aN', new_version, '--', new_path]).split('\n')))
    return {'file': new_path, 'old_path': old_path, 'authors': authors}

def get_file_changes_authors(old_version, new_version):
    diff_output = run_git_command(['git', 'diff', '--name-status', '--find-renames', '--find-copies', old_version, new_version])
    changes_authors = {'added': [], 
                       'deleted': [], 
                       'modified': [], 
                       'renamed': [], 
                       'copied': [], 
                       'type-changed': [], 
                       'unmerged': [], 
                       'unknown': [],
                       'broken': []}

    status_handlers = {
        'A': (handle_lines, 'added'),
        'D': (handle_lines, 'deleted'),
        'M': (handle_lines, 'modified'),  
        'R': (handle_files, 'renamed'),
        'C': (handle_files, 'copied'),
        'T': (handle_files, 'type-changed'),
        'U': (handle_files, 'unmerged'),
        'X': (handle_files, 'unknown'),
        'B': (handle_files, 'broken'),
    }
    
    for line in diff_output.split('\n'):

        status, *file_paths = line.split('\t')
        handler, category = status_handlers.get(status[0], (None, None))
        if handler is not None:
            if status in ('A', 'D', 'M'):
                change_info = handler(new_version, old_version, *file_paths)
            else:
                change_info = handler(new_version, *file_paths)
            
            changes_authors[category].append(change_info)
    
    return changes_authors


    
def get_change_author_by_line(file, old_version, new_version):
    commits = run_git_command([
        'git', 'log', '--format=%H %an', '--follow', '-p', f'{old_version}..{new_version}', '--', file
    ]).split('\n')

    line_changes_details = []
    current_author = None

    commit_hash_author_regex = re.compile(r'^(\w{40})\s(.+)')
    hunk_header_regex = re.compile(r'^@@ (.*?) @@')

    for line in commits:
        commit_hash_author_match = commit_hash_author_regex.match(line)
        if commit_hash_author_match:
            _, current_author = commit_hash_author_match.groups()
            continue
        
        hunk_header_match = hunk_header_regex.match(line)
        if hunk_header_match:
            chunk_range = hunk_header_match.group(1)
            line_changes_details.append({
                'chunk_range': chunk_range,
                'author': current_author,
            })

    return line_changes_details

def get_modified_files_lines_authors(old_version, new_version):
    modified_files = run_git_command(['git', 'diff', '--diff-filter=M', '--name-only', old_version, new_version]).split('\n')
    modified_files_lines_authors = {}
    
    for file in modified_files:
            if file:  
                modified_files_lines_authors[file] = get_change_author_by_line(file, old_version, new_version)

    return modified_files_lines_authors


def main():
    if len(sys.argv) != 3:
        print("Usage: script.py <old_version> <new_version>")
        sys.exit(1)

    old_version = sys.argv[1]
    new_version = sys.argv[2]

    try:
        changes_authors = get_file_changes_authors(old_version, new_version)
        line_changes_authors = get_modified_files_lines_authors(old_version, new_version)
        
        filename_base = f'{old_version}_to_{new_version}_changes'
        with open(f'{filename_base}_authors.json', 'w', encoding='utf-8') as file:
            json.dump(changes_authors, file, indent=4, ensure_ascii=False)

        with open(f'{filename_base}_lines_authors.json', 'w', encoding='utf-8') as file:
            json.dump(line_changes_authors, file, indent=4, ensure_ascii=False)
    
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}\nstdout: {e.stdout}\nstderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

#latest update 2024-01-20 
# Notes:
# https://git-scm.com/docs/git-log
# https://git-scm.com/docs/git-diff 