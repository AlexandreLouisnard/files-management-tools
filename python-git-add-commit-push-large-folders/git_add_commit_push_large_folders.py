import os
import sys
import time
import subprocess

# The objective is to add, commit and push all files/folders of the GIT repositories found in root_path, taking into account the Github limits:
# - max 2 Go per push => the changes are split into several commits, pushed one by one
# - max 100 Mo per file => bigger files are stored with Git LFS
# A summary is printed at the end: what has been pushed, the errors, the folders that are not backed up and the Git LFS files.


MAX_PUSH_SIZE = 500000000 # 500 Mo, Github max size push limit is 2 Go but such big pushes time out (HTTP 408) on a slow connection
PUSH_ATTEMPTS = 3 # A push may fail because of a temporary network error (timeout, DNS...) => retry
PUSH_RETRY_DELAY = 30 # Seconds
LFS_MIN_FILE_SIZE = 100000000 # 100 Mo, Github rejects bigger files unless they are stored with Git LFS
LFS_MAX_FILE_SIZE = 2000000000 # 2 Go, Github max Git LFS file size (free plan)
LFS_FREE_QUOTA = 10 * 1024**3 # 10 Gio, Github free Git LFS storage, shared by all the repos of the account
MAX_DEPTH_WITHOUT_GIT = 1 # Max depth to explore from the root dir, before stopping or finding a git repo
REMOTE = 'origin'
BRANCH = 'master'

class GitError(Exception):
    pass

def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    path = '.'
    try:
        path = sys.argv[1]
    except IndexError:
        print('USAGE: py git_add_commit_push_large_folders.py root_path => without root_path arg, it will consider path="."')

    repos, not_repos = find_repos(path)
    results = [sync_repo(repo_path) for repo_path in repos]
    all_good = print_summary(results, not_repos)
    sys.exit(0 if all_good else 1)

def find_repos(path, depth=0):
    # Returns the GIT repos found in path, and the dirs that are not in a GIT repo (so not backed up)
    if os.path.exists(os.path.join(path, '.git')):
        return [path], []
    if depth >= MAX_DEPTH_WITHOUT_GIT:
        return [], [path]
    repos, not_repos = [], []
    for item in sorted(os.listdir(path), reverse=True):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path) and not item.startswith(('.', '__')):
            sub_repos, sub_not_repos = find_repos(item_path, depth+1)
            repos += sub_repos
            not_repos += sub_not_repos
    return repos, not_repos

def sync_repo(repo_path):
    result = {'name': os.path.basename(os.path.normpath(repo_path)), 'status': '', 'error': '', 'commits': 0, 'files': 0, 'size': 0,
              'new_lfs_files': [], 'lfs_files': [], 'skipped_files': []}
    print(f'\n=== {result["name"]} ===')
    try:
        changes = get_changes(repo_path)
        if not changes and not has_commits(repo_path):
            print('Empty repository => SKIPPING')
            result['status'] = 'empty'
            return result
        remote_head = get_remote_head(repo_path)
        if remote_head and git(repo_path, 'merge-base', '--is-ancestor', remote_head, 'HEAD', check=False).returncode != 0:
            raise GitError('the remote branch has commits that are not in the local branch => pull needed')
        changes = handle_big_files(repo_path, changes, result)
        batches = split_in_batches(changes)
        pushed = 0
        for i, batch in enumerate(batches, 1):
            batch_size = sum(size for _, size in batch)
            print(f'Commit {i}/{len(batches)}: {len(batch)} files, {format_size(batch_size)}')
            if git_commit(repo_path, batch, result['new_lfs_files']):
                result['commits'] += 1
                result['files'] += len(batch)
                result['size'] += batch_size
            remote_head, n = push_unpushed_commits(repo_path, remote_head)
            pushed += n
        if not batches:
            print('Nothing to add/commit')
            remote_head, pushed = push_unpushed_commits(repo_path, remote_head)
        verify(repo_path, result)
        result['status'] = 'pushed' if pushed else 'up to date'
    except GitError as e:
        print(f'ERROR: {e}')
        result['status'] = 'ERROR'
        result['error'] = str(e)
    result['lfs_files'] = get_lfs_files(repo_path)
    return result

def get_changes(repo_path):
    # Returns the (path, size) of the changed files (size is 0 for deleted files), .gitattributes first
    process = git(repo_path, 'status', '--porcelain', '-z', '--untracked-files=all', '--no-renames')
    changes = []
    for entry in process.stdout.split('\0'):
        if entry:
            path = entry[3:]
            full_path = os.path.join(repo_path, path)
            changes.append((path, os.path.getsize(full_path) if os.path.isfile(full_path) else 0))
    return sorted(changes, key=lambda change: (change[0] != '.gitattributes', change[0]))

def handle_big_files(repo_path, changes, result):
    # Github rejects files > 100 Mo => they are stored with Git LFS, or skipped if they are too big even for Git LFS
    for path, size in changes:
        if size > LFS_MAX_FILE_SIZE:
            print(f'ERROR: FILE is too big even for Git LFS: {path} ({format_size(size)}) => SKIPPING FILE')
            result['skipped_files'].append((path, size))
        elif size > LFS_MIN_FILE_SIZE and not is_lfs_tracked(repo_path, path):
            print(f'Big file => stored with Git LFS: {path} ({format_size(size)})')
            git(repo_path, 'lfs', 'track', '--filename', path)
            result['new_lfs_files'].append((path, size))
    if uses_lfs(repo_path):
        # Installs the Git LFS hook that uploads the LFS files on push
        git(repo_path, 'lfs', 'install', '--local')
    if result['new_lfs_files']:
        # .gitattributes has changed
        changes = get_changes(repo_path)
    skipped_paths = {path for path, _ in result['skipped_files']}
    return [(path, size) for path, size in changes if path not in skipped_paths]

def split_in_batches(changes):
    # Splits the changes in batches that can be pushed (Git LFS files are uploaded apart, so they don't count)
    batches = [[]]
    batch_size = 0
    for path, size in changes:
        git_size = 0 if size > LFS_MIN_FILE_SIZE else size
        if batch_size + git_size > MAX_PUSH_SIZE and batches[-1]:
            batches.append([])
            batch_size = 0
        batches[-1].append((path, size))
        batch_size += git_size
    return [batch for batch in batches if batch]

def git_commit(repo_path, changes, lfs_files):
    paths = [path for path, _ in changes]
    git(repo_path, 'add', '--pathspec-from-file=-', '--pathspec-file-nul', input='\0'.join(paths))
    if git(repo_path, 'diff', '--cached', '--quiet', check=False).returncode == 0:
        print('Nothing to commit')
        return False
    git(repo_path, 'commit', '-q', '-m', commit_message(paths, lfs_files))
    return True

def commit_message(paths, lfs_files):
    folders = sorted(set(path.split('/')[0] for path in paths))
    message = f'Sync {", ".join(folders[:3])}' + (f' (+{len(folders) - 3} more)' if len(folders) > 3 else '')
    paths = set(paths)
    lfs_lines = [f'{path} ({format_size(size)})' for path, size in lfs_files if path in paths]
    if lfs_lines:
        message += f'\n\nStored with Git LFS (files > {format_size(LFS_MIN_FILE_SIZE)}):\n' + '\n'.join(lfs_lines)
    return message

def push_unpushed_commits(repo_path, remote_head):
    # Pushes the local commits one by one: each commit is < MAX_PUSH_SIZE, but all together they may not be
    if not has_commits(repo_path):
        return remote_head, 0
    commits = git(repo_path, 'rev-list', '--reverse', 'HEAD', *([f'^{remote_head}'] if remote_head else [])).stdout.split()
    for i, commit in enumerate(commits, 1):
        for attempt in range(1, PUSH_ATTEMPTS + 1):
            print(f'Push {i}/{len(commits)}: {commit[:7]} (attempt {attempt}/{PUSH_ATTEMPTS})')
            try:
                git(repo_path, 'push', REMOTE, f'{commit}:refs/heads/{BRANCH}')
                break
            except GitError:
                if attempt == PUSH_ATTEMPTS:
                    raise
                print(f'=> RETRY in {PUSH_RETRY_DELAY} seconds')
                time.sleep(PUSH_RETRY_DELAY)
        remote_head = commit
    return remote_head, len(commits)

def verify(repo_path, result):
    # Checks that everything is committed, and that the remote branch is the local one
    skipped_paths = {path for path, _ in result['skipped_files']}
    remaining = [path for path, _ in get_changes(repo_path) if path not in skipped_paths]
    if remaining:
        raise GitError(f'{len(remaining)} files still not committed, e.g. "{remaining[0]}"')
    if get_remote_head(repo_path) != git(repo_path, 'rev-parse', 'HEAD').stdout.strip():
        raise GitError('the remote branch is not the same as the local branch after push')

def get_remote_head(repo_path):
    # Returns the last commit of the remote branch, '' if the remote branch doesn't exist yet
    return git(repo_path, 'ls-remote', REMOTE, f'refs/heads/{BRANCH}').stdout.split('\t')[0].strip()

def has_commits(repo_path):
    return git(repo_path, 'rev-parse', '--verify', '--quiet', 'HEAD', check=False).returncode == 0

def is_lfs_tracked(repo_path, path):
    return git(repo_path, 'check-attr', 'filter', '--', path).stdout.strip().endswith(': lfs')

def uses_lfs(repo_path):
    gitattributes = os.path.join(repo_path, '.gitattributes')
    if not os.path.isfile(gitattributes):
        return False
    with open(gitattributes, encoding='utf-8', errors='replace') as f:
        return 'filter=lfs' in f.read()

def get_lfs_files(repo_path):
    # Returns the (path, size) of the committed Git LFS files
    if not uses_lfs(repo_path):
        return []
    files = []
    for path in git(repo_path, 'lfs', 'ls-files', '--name-only', check=False).stdout.splitlines():
        full_path = os.path.join(repo_path, path)
        files.append((path, os.path.getsize(full_path) if os.path.isfile(full_path) else 0))
    return files

def git(repo_path, *args, input=None, check=True):
    # Runs a git command (paths are never interpreted as patterns), raises GitError if it fails
    process = subprocess.run(['git', '-c', 'core.quotepath=off', '--literal-pathspecs', *args], cwd=repo_path, input=input,
                             capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and process.returncode != 0:
        print(process.stderr.strip())
        raise GitError(f'"git {args[0]}" failed: {short_error(process.stderr)}')
    return process

def short_error(stderr):
    # Keeps the meaningful lines of a git error output
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    errors = [line for line in lines if any(word in line.lower() for word in ('error', 'fatal', 'rejected', 'denied', 'not found'))]
    return ' | '.join((errors or lines[-1:])[:3])

def format_size(size):
    return f'{size / 1e9:.1f} GB' if size >= 1e9 else f'{size / 1e6:.0f} MB'

def print_summary(results, not_repos):
    # Prints the summary of the sync, returns True if everything is backed up
    print('\n' + '=' * 35 + ' SUMMARY ' + '=' * 35)
    problems = 0
    for r in results:
        details = f'{r["commits"]} commits, {r["files"]} files, {format_size(r["size"])}' if r['commits'] else ''
        print(f'{r["name"]:<12} {r["status"]:<11} {details}')
        if r['error']:
            problems += 1
            print(f'{"":<12} => {r["error"]}')
        for path, size in r['skipped_files']:
            problems += 1
            print(f'{"":<12} => FILE TOO BIG, NOT BACKED UP: {path} ({format_size(size)})')
    for path in not_repos:
        problems += 1
        print(f'{os.path.basename(os.path.normpath(path)):<12} NOT A GIT REPO => NOT BACKED UP ({path})')

    lfs_files = {}
    for r in results:
        new_paths = {path for path, _ in r['new_lfs_files']}
        for path, size in r['lfs_files'] + r['new_lfs_files']:
            lfs_files[f'{r["name"]}/{path}'] = (size, path in new_paths)
    if lfs_files:
        lfs_size = sum(size for size, _ in lfs_files.values())
        print(f'\nGit LFS files (> {format_size(LFS_MIN_FILE_SIZE)}):')
        for path, (size, new) in sorted(lfs_files.items()):
            print(f'  {"NEW" if new else "   "} {path} ({format_size(size)})')
        print(f'  Total: {format_size(lfs_size)} = {lfs_size / LFS_FREE_QUOTA:.0%} of the free Git LFS quota (10 GiB for the whole Github account)')
        if lfs_size > LFS_FREE_QUOTA:
            problems += 1
            print('  => ERROR: free Git LFS quota exceeded, Github will refuse the pushes')
        elif lfs_size > 0.8 * LFS_FREE_QUOTA:
            print('  => WARNING: the free Git LFS quota is almost full')

    if problems:
        print(f'\n=> {problems} PROBLEM(S), see above')
    else:
        print('\n=> ALL GOOD: everything is backed up on Github')
    return problems == 0

if __name__ == '__main__':
    main()
