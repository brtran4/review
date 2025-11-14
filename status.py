#!/usr/bin/env python3

import json
import requests
import os
import sys
import subprocess
from prettytable import PrettyTable
from datetime import datetime, timezone
from review import get_username

naur_repo_names = ["moddingway", "naurffxiv", "clearingway", "findingway", "raidingway", "templatingway"]
github_api = "https://api.github.com/repos"


class PullRequest:
    def __init__(
        self,
        id,
        title,
        user,
        ticket,
        repo,
        num_reviewers,
        approved_count,
        is_approved_by_me,
        last_updated,
    ):
        self.id = id
        self.title = title
        self.user = user
        self.ticket = ticket
        self.repo = repo
        self.num_reviewers = num_reviewers
        self.approved_count = approved_count
        self.is_approved_by_me = is_approved_by_me
        self.last_updated = last_updated


def get_pull_requests():
    key = ""
    project_name = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True, text=True,
    ).stdout.split(':', 1)[-1].split('/', 1)[0]
    if project_name == "":
        project_name = "naur"
    with open(f"/home/brtran/.ssh/{project_name}-github-api-key", "r") as f:  # git_token
        key = f.read().strip()

    username = get_username()
    git_token = key
    headers = {
        "Authorization": "token {0}".format(git_token),
        "Content-Type": "application/json",
    }
    review_requests = {
        "moddingway": [],
        "naurffxiv": [],
        "findingway": [],
        "clearingway": [],
        "raidingway": [],
        "templatingway": [],
    }
    for repo in naur_repo_names:
        # print(f"{github_api}/naurffxiv/{repo}/pulls")
        response = requests.get(f"{github_api}/naurffxiv/{repo}/pulls", headers=headers)
        for res in response.json():
            # for reviewer in res["requested_reviewers"]:
            # if username in reviewer["login"]:
            id = res["number"]
            title = res["title"]
            ticket = "None"
            user = res["user"]["login"]
            approved_count, review_count, is_approved_by_me = get_pull_request_reviews(
                id, repo, headers
            )
            num_reviewers = len(res["requested_reviewers"]) + review_count
            last_updated = datetime.strptime(res["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            last_updated = datetime.now(timezone.utc) - last_updated
            review_requests[repo].append(
                PullRequest(
                    id,
                    title,
                    user,
                    ticket,
                    repo,
                    num_reviewers,
                    approved_count,
                    is_approved_by_me,
                    f"{last_updated.days} days ago" if last_updated.days > 0 else f"{int(last_updated.total_seconds() / 3600)} hours ago",
                )
            )

    for repo, request_list in review_requests.items():
        print(repo)
        t = PrettyTable(
            ["PR ID", "Assignee", "Approved count", "Approved by me", "Last Updated", "Title"]
        )
        for request in request_list:
            is_approved_by_me = request.is_approved_by_me
            if request.user == "brtran4":
                is_approved_by_me = "N/A"
            t.add_row(
                [
                    request.id,
                    request.user,
                    f"{request.approved_count}/{request.num_reviewers}",
                    is_approved_by_me,
                    request.last_updated,
                    request.title,
                ]
            ),
            # t.add_divider()
        t.align["Title"] = "l"
        t.align["Assignee"] = "l"
        t.align["Last Updated"] = "l"
        print(t)


def get_pull_request_reviews(id, repo, headers):
    res = requests.get(
        f"{github_api}/naurffxiv/{repo}/pulls/{id}/reviews", headers=headers
    )
    approved_count = 0
    review_count = 0
    approved_by_me = False
    for review in res.json():
        review_count = review_count + 1
        if review["state"] == "APPROVED":
            approved_count = approved_count + 1
        if "brtran4" in review["user"]["login"] and review["state"] == "APPROVED":
            approved_by_me = True
    # print(approved_count)
    return approved_count, review_count, approved_by_me


if __name__ == "__main__":
    get_pull_requests()
