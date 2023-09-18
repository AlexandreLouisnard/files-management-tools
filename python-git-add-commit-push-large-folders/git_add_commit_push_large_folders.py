import os
import sys
import subprocess

# The objective is to add, commit and push all files/folders recursively taking into account the Github max 2 Go / push limit.


MAX_PUSH_SIZE = 1900000000 # 1.9 Go, Github max size push limit
MAX_DEPTH_WITHOUT_GIT = 1 # Max depth to explore from the root dir, before stopping or finding a git repo

def main():
    path = '.'
    try:
        path = sys.argv[1]
    except:
        print('USAGE: py git.py root_path => without root_path arg, it will consider path="."')

    handle_path_recursively(path)
    
def handle_path_recursively(path='.', depth=0, repo_path=''):
    tab = " " * depth
    print(f'\nPATH: {tab}{path}')
    if not is_git_repo(path):
        # Not a GIT repo
        print(f'{tab}Not a GIT repository')
        if depth >= MAX_DEPTH_WITHOUT_GIT:
            # Stop
            print(f'{tab}MAX_DEPTH_WITHOUT_GIT reached')
            print(f'{tab}=> SKIPPING DIR')
        else:
            # Browse deeper
            print(f'{tab}=> BROWSE INTO (not a GIT repo)')
            for item in os.listdir(path):
                if item != ".git" and not os.path.isfile(item):
                    handle_path_recursively(os.path.join(path, item), depth+1, repo_path)
    else:
        # GIT repo
        if len(repo_path) == 0:
            if os.path.isfile(path):
                repo_path = os.path.join(path, '..')
            else:
                repo_path = path
            print(f'{tab}Found GIT repository')
        if os.path.isfile(path):
            # File in GIT repo
            if get_dir_or_file_size(path) > MAX_PUSH_SIZE:
                # File is too big
                print(f'{tab}ERROR: FILE is too big: {get_dir_or_file_size(path):,} bytes')
                print(f'{tab}=> SKIPPING FILE')
            else:
                # Version file
                print(f'{tab}=> ADD/COMMIT/PUSH FILE')
                git_add_commit_push(path, repo_path)
        else:
            # Dir
            process = subprocess.Popen(['git', 'status', '--porcelain'], cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if len(stdout) == 0:
                # Repo already up-to-date, push just in case
                print(f'{tab}Nothing to add/commit')
                print(f'{tab}=> PUSH just in case')
                git_push(repo_path)
            else:
                if get_dir_or_file_size(path) < MAX_PUSH_SIZE: # max github push is 2Go, limit to 1.9Go
                    # Commit dir
                    print(f'{tab}=> ADD/COMMIT/PUSH DIR')
                    git_add_commit_push(path, repo_path)
                else:
                    # Too big dir, browse into to split size
                    print(f'{tab}DIR is too big: {get_dir_or_file_size(path):,} bytes)')
                    print(f'{tab}=> BROWSE INTO')
                    for item in os.listdir(path):
                        if item != ".git":
                            handle_path_recursively(os.path.join(path, item), depth+1, repo_path)

def get_dir_or_file_size(path='.'):
    total = 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    else:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_or_file_size(entry.path)
    return total

def git_add_commit_push(path, repo_path):
    git_add(path, repo_path)
    git_commit(path, repo_path)
    git_push(repo_path)

def git_add(path, repo_path):
    relative_path = os.path.relpath(path, repo_path)
    process = 0
    if path == repo_path:
        process = subprocess.Popen(['git', 'add', '-A'], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        process = subprocess.Popen(['git', 'add', relative_path], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'from "{repo_path}", calling "{process.args}"')
    stdout, stderr = process.communicate()
    print (f'stdout: {str(stdout)[:100]}')
    print (f'stderr: {str(stderr)[:100]}')

def git_commit(path, repo_path):
    relative_path = os.path.relpath(path, repo_path)
    process = subprocess.Popen(['git', 'commit', '-m', f'Added {relative_path}'], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'from "{repo_path}", calling "{process.args}"')
    stdout, stderr = process.communicate()
    print (f'stdout: {str(stdout)[:100]}')
    print (f'stderr: {str(stderr)[:100]}')

def git_push(repo_path):
    process = subprocess.Popen(['git', 'push', 'origin', 'master'], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f'from "{repo_path}", calling "{process.args}"')
    stdout, stderr = process.communicate()
    print (f'stdout: {str(stdout)[:100]}')
    print (f'stderr: {str(stderr)[:100]}')
    if (str(stderr).__contains__('fatal')):
        sys.exit("PUSH FAILED => Exiting !")

def is_git_repo(path):
    if os.path.isfile(path):
        path = os.path.join(path, '..')
    process = subprocess.Popen(['git', 'status'], cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return len(stderr) == 0

main()
