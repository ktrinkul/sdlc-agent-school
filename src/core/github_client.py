from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any

import requests
from github import Github, GithubException

from src.core.github_app_auth import GitHubAppAuth
from src.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepoRef:
    full_name: str


class GitHubClient:
    """Wrapper around PyGithub and REST endpoints used by the agent."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._client = Github(token, per_page=100)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get_repo(self, repo: str):
        return self._client.get_repo(repo)

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        for attempt in range(3):
            response = self._session.request(method, url, timeout=30, **kwargs)
            if response.status_code not in {403, 429}:
                response.raise_for_status()
                return response

            reset = response.headers.get("X-RateLimit-Reset")
            wait_for = 5
            if reset and reset.isdigit():
                wait_for = max(1, int(reset) - int(time.time()))
            logger.warning("Rate limited by GitHub. Sleeping for %s seconds.", wait_for)
            time.sleep(wait_for)

        response.raise_for_status()
        return response

    def get_issue(self, repo: str, issue_number: int):
        logger.info("Fetching issue %s from %s", issue_number, repo)
        return self._get_repo(repo).get_issue(number=issue_number)

    def can_push(self, repo: str) -> bool:
        repository = self._get_repo(repo)
        permissions = getattr(repository, "permissions", None)
        if permissions is None:
            return False
        return bool(getattr(permissions, "push", False) or getattr(permissions, "admin", False))

    def get_issue_comments(self, repo: str, issue_number: int) -> list:
        issue = self.get_issue(repo, issue_number)
        return list(issue.get_comments())

    def create_branch(self, repo: str, base_branch: str, new_branch: str) -> bool:
        repository = self._get_repo(repo)
        base_ref = repository.get_git_ref(f"heads/{base_branch}")
        repository.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)
        logger.info("Created branch %s from %s", new_branch, base_branch)
        return True

    def ensure_branch(self, repo: str, base_branch: str, new_branch: str) -> None:
        repository = self._get_repo(repo)
        try:
            repository.get_git_ref(f"heads/{new_branch}")
            return
        except GithubException as exc:
            if exc.status != 404:
                raise
        base_ref = repository.get_git_ref(f"heads/{base_branch}")
        repository.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)
        logger.info("Created branch %s from %s", new_branch, base_branch)

    def create_pull_request(self, repo: str, head: str, base: str, title: str, body: str):
        repository = self._get_repo(repo)
        pr = repository.create_pull(title=title, body=body, head=head, base=base)
        logger.info("Created PR %s", pr.html_url)
        return pr

    def update_pull_request(self, repo: str, pr_number: int, title: str, body: str):
        pr = self._get_repo(repo).get_pull(pr_number)
        pr.edit(title=title, body=body)
        logger.info("Updated PR %s", pr_number)
        return pr

    def add_pr_comment(self, repo: str, pr_number: int, comment: str):
        pr = self._get_repo(repo).get_pull(pr_number)
        return pr.create_issue_comment(comment)

    def get_pull(self, repo: str, pr_number: int):
        return self._get_repo(repo).get_pull(pr_number)

    def find_pull_by_head(self, repo: str, head: str):
        url = f"https://api.github.com/repos/{repo}/pulls"
        response = self._request("GET", url, params={"state": "all", "head": head})
        pulls = response.json()
        if not pulls:
            return None
        pr_number = pulls[0].get("number")
        if not pr_number:
            return None
        return self.get_pull(repo, pr_number)

    def create_review(
        self, repo: str, pr_number: int, event: str, body: str, comments: list
    ):
        pr = self._get_repo(repo).get_pull(pr_number)
        return pr.create_review(body=body, event=event, comments=comments)

    def get_pr_files(self, repo: str, pr_number: int) -> list:
        pr = self._get_repo(repo).get_pull(pr_number)
        return list(pr.get_files())

    def get_pr_reviews(self, repo: str, pr_number: int) -> list:
        pr = self._get_repo(repo).get_pull(pr_number)
        return list(pr.get_reviews())

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
        response = self._request(
            "GET",
            url,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        return response.text

    def get_workflow_runs(self, repo: str, pr_number: int) -> list[dict]:
        url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=100"
        response = self._request("GET", url)
        runs = response.json().get("workflow_runs", [])
        filtered = []
        for run in runs:
            prs = run.get("pull_requests", [])
            if any(pr.get("number") == pr_number for pr in prs):
                filtered.append(run)
        return filtered

    def get_check_runs(self, repo: str, commit_sha: str) -> list[dict]:
        url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}/check-runs"
        response = self._request(
            "GET",
            url,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        return response.json().get("check_runs", [])

    def close_issue(self, repo: str, issue_number: int, comment: str | None = None) -> None:
        issue = self._get_repo(repo).get_issue(number=issue_number)
        if comment:
            issue.create_comment(comment)
        issue.edit(state="closed")

    def link_pr_to_issue(self, repo: str, pr_number: int, issue_number: int) -> None:
        issue = self._get_repo(repo).get_issue(number=issue_number)
        issue.create_comment(f"Linked PR #{pr_number}")

    def apply_file_changes(
        self, repo: str, branch: str, files: list[dict], commit_message: str
    ) -> None:
        repository = self._get_repo(repo)
        for file_entry in files:
            path = file_entry["path"]
            action = file_entry.get("action", "modify")
            content = file_entry.get("content", "")
            try:
                existing = repository.get_contents(path, ref=branch)
            except GithubException as exc:
                if exc.status == 404:
                    existing = None
                else:
                    raise

            if action == "delete":
                if existing:
                    repository.delete_file(path, commit_message, existing.sha, branch=branch)
                continue

            if existing:
                repository.update_file(
                    path, commit_message, content, existing.sha, branch=branch
                )
            else:
                repository.create_file(path, commit_message, content, branch=branch)

    def safe_call(self, func, *args, **kwargs):
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except GithubException as exc:
                if exc.status in {403, 429} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise


def create_github_client(settings: Settings, repo: str | None = None) -> GitHubClient:
    if settings.github_auth_mode == "app":
        if not settings.github_app_id or not settings.github_app_private_key_path:
            raise ValueError("GitHub App auth requires GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH.")
        auth = GitHubAppAuth(
            app_id=settings.github_app_id,
            private_key_path=settings.github_app_private_key_path,
        )
        installation_id = settings.github_app_installation_id
        if installation_id is None:
            if not repo:
                raise ValueError(
                    "GITHUB_APP_INSTALLATION_ID is not set and repo is unknown."
                )
            installation_id = auth.get_installation_id_for_repo(repo)
        token = auth.get_installation_token(installation_id)
        return GitHubClient(token)
    return GitHubClient(settings.github_token)
