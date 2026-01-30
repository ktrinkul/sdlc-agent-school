from __future__ import annotations

from pathlib import Path

from github import GithubIntegration


class GitHubAppAuth:
    """Authenticate via GitHub App installation tokens."""

    def __init__(self, app_id: str, private_key_path: str) -> None:
        self._app_id = app_id
        self._private_key = Path(private_key_path).read_text(encoding="utf-8")
        self._integration = GithubIntegration(self._app_id, self._private_key)

    def get_installation_token(self, installation_id: int) -> str:
        return self._integration.get_access_token(installation_id).token

    def get_installation_id_for_repo(self, repo: str) -> int:
        owner, name = repo.split("/", 1)
        installation = self._integration.get_installation(owner, name)
        return installation.id
