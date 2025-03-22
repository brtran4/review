import json
import requests
import subprocess
import typing
import os
import sys

project_name = "naurffxiv"
repo_name = "naurffxiv" # TODO: get current repo
git_pulls_api = "https://api.github.com/repos/{0}/{1}/pulls".format(
    project_name,
    repo_name
)    


def create_pull_request(user, head_branch, base_branch, git_token):
    """Creates the pull request for the head_branch against the base_branch"""
    headers = {
        "Authorization": "token {0}".format(git_token),
        "Content-Type": "application/json"
    }

    title, description, sha = get_commit_message()
    subprocess.check_output(["git", "push", "--force", "origin", "HEAD"])

    git_commits_api = "https://api.github.com/repos/{0}/{1}/commits/{2}/pulls".format(
        project_name,
        repo_name,
        sha,
    )
    r = requests.get(
        git_commits_api,
        headers=headers,
    )
    
    # a PR was found, update the PR instead
    if r.status_code != 422:
        return False
    
    if subprocess.check_output(["git", "log", f"origin/{base_branch}..HEAD"]).decode("utf-8") == "":
        print("No changes detected")
        return

    payload = {
        "title": title,
        "body": description,
        "head": head_branch,
        "base": base_branch,
    }

    r = requests.post(
        git_pulls_api,
        headers=headers,
        data=json.dumps(payload))

    if not r.ok:
        print(f"Pull request updated for branch {head_branch}")
        return True
    
    pull_request_result = r.json()

    # assign the current user to the pull request
    git_assignee_api = "https://api.github.com/repos/{0}/{1}/issues/{2}/assignees".format(
        project_name,
        repo_name,
        str(pull_request_result["number"]),
    )

    data = {
        "assignees": [user],
    }
    r = requests.post(
        git_assignee_api,
        headers=headers,
        data=json.dumps(data)
    )
    return True

def update_pull_request():
    subprocess.check_output(["git", "push", "--force", "origin", "HEAD"])

def get_git_branch(path = None):
    '''Returns the git branch the user is on.'''
    if path is None:
        path = os.path.curdir
    command = 'git rev-parse --abbrev-ref HEAD'.split()
    branch = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=path).stdout.read()
    return branch.strip().decode('utf-8')


def get_commit_message():
    '''Parses the first local commit message that have not been pushed remotely yet.'''
    # TODO: replace hardcoded dev with target branch
    res = subprocess.check_output(["git", "log", "origin/dev..HEAD"]).decode("utf-8").split("\n")
    title = ""
    description = ""
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    title_parsed = False

    for line in res[4:]:
        message = line.lstrip()
        if not title_parsed:
            if not message:
                title_parsed = True
            else:
                title = message
        else:
            if not message:
                break
            description += message + "\n"
    
    return title, description, sha

def create_new_branch(new_branch, target_branch):
    try:
        subprocess.check_output(["git", "checkout", "-b", new_branch, target_branch])
        subprocess.check_output(["git", "pull", "--rebase", "origin", target_branch])
        subprocess.check_output(["git", "push", "--set-upstream", "origin", new_branch])
        subprocess.check_output(["git", "branch", f"--set-upstream-to=origin/{target_branch}", new_branch])
    except:
        print("ERROR: cannot create new branch.")
        return

def config(git_username, access_token):
    headers = {
        "Authorization": "token {0}".format(access_token),
        "Content-Type": "application/json"
    }
    
    git_find_user = "https://api.github.com/users/{0}".format(git_username)
    r = requests.get(git_find_user)

    if r.status_code == 404:
        print("User was not found. Please check your username.")
        return

    # check for available assignees in the repo
    available_assignees = "https://api.github.com/repos/{0}/{1}/assignees".format(
        project_name,
        repo_name,
    )
    r = requests.get(available_assignees, headers=headers)
    
    try:
        if not any(user["login"] == git_username for user in r.json()):
            print("User is not in the repository. Contact Remengis to gain access.")
            return
    except:
        print("Access token is not valid.")
        return
    
    with open("config", "w") as f:
        f.write(f"{git_username}\n")
        f.write(f"{access_token}\n")
    print("Username and access token stored in config")


if __name__ == "__main__":
    print(sys.argv)
    # ./review
    if len(sys.argv) == 1:
        conf = []
        try:
            with open("config") as file:
                for line in file:
                    conf.append(line.strip())
        except:
            print("No config file found. Run: ./review config")

        is_new_pull_request = create_pull_request(
            conf[0], # current user
            get_git_branch(), # head_branch
            "dev", # base_branch TODO: change to automatically detect base branch
            conf[1], # git_token
        )
        if not is_new_pull_request:
            update_pull_request()

    elif len(sys.argv) == 2 and "config" in sys.argv:
        git_username = input("Input your git username.\n")
        access_token = input("Input your git access token.\n")
        config(git_username, access_token)
    
    # ./review new <BRANCH_NAME> <TARGET_BRANCH>
    elif len(sys.argv) == 4 and sys.argv[1] == "new":
        create_new_branch(sys.argv[2], sys.argv[3])

    
