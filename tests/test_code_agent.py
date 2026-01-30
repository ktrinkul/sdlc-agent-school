from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

from src.agents.code_agent import CodeAgent
from src.core.config import Settings


class FakeIssue:
    def __init__(self, body: str = "do thing") -> None:
        self.body = body


class FakeGitHub:
    def __init__(self) -> None:
        self.created_pr = False

    def get_issue(self, repo: str, issue_number: int) -> FakeIssue:
        return FakeIssue()

    def can_push(self, repo: str) -> bool:
        return True

    def find_pull_by_head(self, repo: str, head: str):
        return None

    def update_pull_request(self, repo: str, pr_number: int, title: str, body: str):
        @dataclass
        class PR:
            number: int = pr_number

        return PR()

    def create_pull_request(self, repo: str, head: str, base: str, title: str, body: str):
        self.created_pr = True

        @dataclass
        class PR:
            number: int = 1

        return PR()

    def get_pr_reviews(self, repo: str, pr_number: int) -> list:
        return []

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        return ""

    def add_pr_comment(self, repo: str, pr_number: int, comment: str) -> None:
        return None

    def get_issue_comments(self, repo: str, issue_number: int) -> list:
        return []


class FakeGitOps:
    def __init__(self, repo_url: str, base_branch: str = "main", **kwargs) -> None:
        self.repo_url = repo_url
        self.base_branch = base_branch
        self._tempdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self._tempdir.name)
        (self.workdir / "main.py").write_text("print('hi')\n", encoding="utf-8")

    def __enter__(self) -> "FakeGitOps":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tempdir.cleanup()
        return None

    def get_repo_structure(self) -> dict:
        return {"main.py": None}

    def create_branch(self, branch_name: str) -> None:
        return None

    def ensure_branch(self, branch_name: str) -> None:
        return None

    def stage_files(self, files) -> None:
        return None

    def commit_changes(self, message: str) -> None:
        return None

    def push_changes(self, branch: str) -> None:
        return None

    def get_changed_files(self) -> list[str]:
        return ["main.py"]

    def write_file(self, filepath: str, content: str) -> None:
        return None

    def read_file(self, filepath: str) -> str:
        return (self.workdir / filepath).read_text(encoding="utf-8")


class FakeLLM:
    def generate(self, prompt: str, system: str | None = None) -> str:
        return "Do the thing"

    def generate_structured(self, prompt: str, system: str | None = None) -> dict:
        if "implementation plan" in prompt.lower():
            return {
                "summary": "Plan",
                "files_to_modify": [{"path": "main.py", "reason": "Update output"}],
                "files_to_avoid": [],
                "plan": ["Step 1"],
                "safety_checks": ["Avoid unrelated changes"],
                "acceptance_criteria": ["Done"],
            }
        if "\"final_comment\"" in prompt and "\"tasks\"" in prompt:
            return {"summary": "ok", "tasks": [], "final_comment": "Done"}
        if "\"restart\"" in prompt and "\"reason\"" in prompt:
            return {"restart": False, "summary": "No change", "reason": "No new scope"}
        return {
            "files_to_modify": [
                {"path": "main.py", "action": "modify", "content": "print('hi')"}
            ],
            "commit_message": "Add feature",
        }


def test_code_agent_process_issue(monkeypatch) -> None:
    settings = Settings(
        github_token="token",
        github_repo_owner="owner",
        github_repo_name="repo",
        openai_api_key="key",
    )
    github = FakeGitHub()
    llm = FakeLLM()

    monkeypatch.setattr("src.agents.code_agent.GitOperations", FakeGitOps)

    agent = CodeAgent(github=github, llm=llm, config=settings)

    assert agent.process_issue("owner/repo", 1)
    assert github.created_pr
