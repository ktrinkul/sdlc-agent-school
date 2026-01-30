from unittest.mock import Mock

from src.core.github_client import GitHubClient


def test_get_issue_uses_repo() -> None:
    repo = Mock()
    repo.get_issue.return_value = "issue"
    client = GitHubClient(token="token")
    client._client = Mock()
    client._client.get_repo.return_value = repo

    issue = client.get_issue("owner/repo", 1)

    assert issue == "issue"
    repo.get_issue.assert_called_once_with(number=1)


def test_get_pr_diff_returns_text() -> None:
    response = Mock()
    response.status_code = 200
    response.text = "diff"
    response.raise_for_status.return_value = None
    session = Mock()
    session.request.return_value = response

    client = GitHubClient(token="token")
    client._session = session

    diff = client.get_pr_diff("owner/repo", 2)

    assert diff == "diff"


def test_find_pull_by_head_returns_pr() -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = [{"number": 7}]
    response.raise_for_status.return_value = None
    session = Mock()
    session.request.return_value = response

    repo = Mock()
    pr = Mock()
    repo.get_pull.return_value = pr

    client = GitHubClient(token="token")
    client._session = session
    client._client = Mock()
    client._client.get_repo.return_value = repo

    result = client.find_pull_by_head("owner/repo", "owner:branch")

    assert result == pr
    repo.get_pull.assert_called_once_with(7)
