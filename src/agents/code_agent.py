from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
import re
import traceback
from datetime import datetime, timezone

from git import GitCommandError

from src.core.git_operations import GitOperations
from src.core.github_client import GitHubClient
from src.core.llm_client import LLMClient
from src.core.config import Settings
from src.agents.review_agent import ReviewAgent


logger = logging.getLogger(__name__)


@dataclass
class CodeAgent:
    """Core agent that turns an issue into code changes and a PR."""

    github: GitHubClient
    llm: LLMClient
    config: Settings
    iteration: int = 0
    state_dir: Path = field(default_factory=lambda: Path(".agent_state"))
    reviewer: ReviewAgent | None = None

    def process_issue(self, repo: str, issue_number: int) -> bool:
        """Run the end-to-end workflow for a single issue."""
        try:
            self._load_state(repo, issue_number)
            issue = self.fetch_issue(repo, issue_number)
            pr_number = self.check_existing_pr(repo, issue_number)

            state = self._load_state_data(repo, issue_number) or {}
            feedback_history: list[dict] = state.get("feedback_history", [])
            plan: dict | None = state.get("plan")
            last_comment_id = state.get("last_issue_comment_id")

            issue_comments = self.github.get_issue_comments(repo, issue_number)
            issue_context, latest_comment_id, latest_comment_body = (
                self._prepare_issue_context(issue.body or "", issue_comments)
            )

            self._ensure_reviewer()
            should_exit, plan, feedback_history = self._handle_comment_restart(
                repo=repo,
                issue_number=issue_number,
                state=state,
                issue_context=issue_context,
                latest_comment_id=latest_comment_id,
                latest_comment_body=latest_comment_body,
                plan=plan,
                feedback_history=feedback_history,
                last_comment_id=last_comment_id,
            )
            if should_exit:
                return True

            if self.iteration >= self.config.max_iterations:
                logger.error("Max iterations reached for issue %s", issue_number)
                return False

            if not self.github.can_push(repo):
                logger.error(
                    "Token does not have push permissions for %s. "
                    "Update the PAT with repo write access.",
                    repo,
                )
                return False

            self._save_state(
                repo,
                issue_number,
                {
                    "iteration": self.iteration,
                    "pr_number": pr_number,
                    "step": "requirements",
                    "last_issue_comment_id": latest_comment_id,
                },
            )
            requirements = self.analyze_requirements(issue_context)

            with self.clone_repository(repo) as git_ops:
                self._save_state(
                    repo,
                    issue_number,
                    {"iteration": self.iteration, "pr_number": pr_number, "step": "analyze"},
                )
                repo_structure = json.dumps(git_ops.get_repo_structure(), indent=2)
                relevant_files = self.analyze_codebase(git_ops, requirements, repo_structure)
                if not plan:
                    plan = self.reviewer.generate_plan(
                        requirements, repo_structure, relevant_files
                    )
                    self._save_state(
                        repo,
                        issue_number,
                        {
                            "iteration": self.iteration,
                            "pr_number": pr_number,
                            "step": "plan",
                            "plan": plan,
                            "feedback_history": feedback_history,
                        },
                    )

                while self.iteration < self.config.max_iterations:
                    self.iteration += 1
                    self._save_state(
                        repo,
                        issue_number,
                        {
                            "iteration": self.iteration,
                            "pr_number": pr_number,
                            "step": "apply",
                            "plan": plan,
                            "feedback_history": feedback_history,
                        },
                    )
                    payload = self.generate_solution(
                        requirements,
                        repo_structure,
                        self._augment_relevant_files(relevant_files, plan, feedback_history),
                    )
                    self.apply_changes(git_ops, payload)
                    self.validate_changes(git_ops)
                    self.commit_and_push(git_ops, issue_number, payload, repo)

                    pr = self.create_or_update_pr(repo, issue_number, payload["commit_message"])
                    self._save_state(
                        repo,
                        issue_number,
                        {
                            "iteration": self.iteration,
                            "pr_number": pr.number,
                            "step": "pr",
                            "plan": plan,
                            "feedback_history": feedback_history,
                        },
                    )

                    diff = self.github.get_pr_diff(repo, pr.number)
                    review = self.reviewer.review_changes(
                        requirements,
                        plan,
                        diff,
                        feedback_history,
                    )
                    feedback_history.append(review)
                    self._save_state(
                        repo,
                        issue_number,
                        {
                            "iteration": self.iteration,
                            "pr_number": pr.number,
                            "step": "final_review",
                            "plan": plan,
                            "feedback_history": feedback_history,
                            "review": review,
                            "last_issue_comment_id": latest_comment_id,
                        },
                    )
                    self._post_review_comment(repo, pr.number, review)
                    self._save_state(
                        repo,
                        issue_number,
                        {
                            "iteration": self.iteration,
                            "pr_number": pr.number,
                            "step": "completed",
                            "plan": plan,
                            "feedback_history": feedback_history,
                            "review": review,
                            "last_issue_comment_id": latest_comment_id,
                        },
                    )
                    return True

            return False
        except Exception as exc:  # noqa: BLE001
            self._record_error(repo, issue_number, exc)
            logger.exception("Issue processing failed for %s#%s", repo, issue_number)
            return False

    def fetch_issue(self, repo: str, issue_number: int):
        """Fetch the GitHub issue object."""
        return self.github.get_issue(repo, issue_number)

    def check_existing_pr(self, repo: str, issue_number: int) -> int | None:
        """Find an existing PR for this issue branch, if any."""
        owner, _ = repo.split("/", 1)
        branch = f"agent/issue-{issue_number}"
        existing = self.github.find_pull_by_head(repo, f"{owner}:{branch}")
        if existing:
            return existing.number
        return None

    def analyze_requirements(self, issue_description: str) -> str:
        """Summarize the issue into actionable requirements for the coder."""
        prompt = self._render_prompt(
            "requirements_analysis.txt",
            issue_description=issue_description,
        )
        logger.debug("Requirements analysis prompt:\n%s", prompt)
        response = self.llm.generate(prompt, system="Return a concise, actionable summary.")
        logger.info("Requirements analysis completed.")
        logger.debug("Requirements analysis response:\n%s", response)
        return response.strip() or issue_description

    def analyze_codebase(
        self, git_ops: GitOperations, issue_description: str, repo_structure: str
    ) -> str:
        """Select relevant files and return their contents as JSON."""
        file_paths = self._collect_repo_files(git_ops)
        selected = self._select_relevant_files(file_paths, issue_description)
        snippets = []
        for path in selected:
            content = self._safe_read_file(git_ops, path)
            if content is None:
                continue
            snippets.append({"path": path, "content": content})
        if not snippets:
            return repo_structure
        return json.dumps(snippets, indent=2)

    def generate_solution(self, issue_description: str, repo_structure: str, relevant_files: str) -> dict:
        """Ask the model for a structured change plan and file updates."""
        prompt = self._render_prompt(
            "code_generation.txt",
            issue_description=issue_description,
            repo_structure=repo_structure,
            relevant_files=relevant_files,
        )
        logger.debug("Code generation prompt:\n%s", prompt)
        response = self.llm.generate_structured(
            prompt, system="Return only valid JSON. Do not include markdown."
        )
        logger.debug("Code generation response:\n%s", json.dumps(response, indent=2))
        return response

    def apply_changes(self, git_ops: GitOperations, payload: dict) -> None:
        """Apply LLM-proposed file modifications to the working tree."""
        for file_entry in payload.get("files_to_modify", []):
            if isinstance(file_entry, str):
                logger.warning("Skipping invalid file entry (string): %s", file_entry)
                continue
            if not isinstance(file_entry, dict):
                logger.warning("Skipping invalid file entry (type=%s)", type(file_entry).__name__)
                continue
            path = file_entry.get("path")
            if not path:
                logger.warning("Skipping file entry without path: %s", file_entry)
                continue
            action = file_entry.get("action", "modify")
            content = file_entry.get("content")
            if action == "delete":
                target = git_ops.workdir / path
                if target.exists():
                    target.unlink()
                continue
            if content is None:
                continue
            if isinstance(content, list):
                content = "\n".join(str(line) for line in content)
            elif not isinstance(content, str):
                content = json.dumps(content, indent=2)
            git_ops.write_file(path, content)

    def validate_changes(self, git_ops: GitOperations) -> None:
        # Placeholder for syntax checks or unit tests.
        _ = git_ops.get_changed_files()

    def clone_repository(self, repo: str) -> GitOperations:
        """Clone the target repository for local modifications."""
        logger.info("Cloning repository %s", repo)
        return GitOperations(
            repo_url=f"https://github.com/{repo}",
            base_branch=self.config.base_branch,
            token=self._git_token(),
        )

    def commit_and_push(self, git_ops: GitOperations, issue_number: int, payload: dict, repo: str) -> None:
        """Commit local changes and push to the issue branch (fallback to API)."""
        branch_name = f"agent/issue-{issue_number}"
        git_ops.ensure_branch(branch_name)
        files = [file["path"] for file in payload.get("files_to_modify", [])]
        git_ops.stage_files(files)
        git_ops.commit_changes(payload["commit_message"])
        try:
            git_ops.push_changes(branch_name)
        except GitCommandError as exc:
            logger.warning("Git push failed (%s). Falling back to API commit.", exc)
            self.github.ensure_branch(repo, self.config.base_branch, branch_name)
            self.github.apply_file_changes(
                repo, branch_name, payload.get("files_to_modify", []), payload["commit_message"]
            )

    def _augment_relevant_files(
        self, relevant_files: str, plan: dict | None, feedback_history: list[dict]
    ) -> str:
        """Add reviewer context to the code generation prompt."""
        payload = {
            "relevant_files": relevant_files,
            "plan": plan,
            "feedback_history": feedback_history,
        }
        return json.dumps(payload, indent=2)

    def create_or_update_pr(self, repo: str, issue_number: int, title: str):
        """Open a PR for the issue branch, or update it if it exists."""
        pr_title = f"Resolve #{issue_number}: {title}"
        body = f"Closes #{issue_number}"
        branch = f"agent/issue-{issue_number}"
        owner, _ = repo.split("/", 1)
        existing = self.github.find_pull_by_head(repo, f"{owner}:{branch}")
        if existing:
            return self.github.update_pull_request(repo, existing.number, pr_title, body)
        return self.github.create_pull_request(repo, branch, self.config.base_branch, pr_title, body)

    def _state_path(self, repo: str, issue_number: int) -> Path:
        safe_repo = repo.replace("/", "_")
        return self.state_dir / f"{safe_repo}_{issue_number}.json"

    def _load_state(self, repo: str, issue_number: int) -> None:
        path = self._state_path(repo, issue_number)
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.iteration = data.get("iteration", 0)

    def _load_state_data(self, repo: str, issue_number: int) -> dict | None:
        path = self._state_path(repo, issue_number)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_state(self, repo: str, issue_number: int, data: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self._state_path(repo, issue_number)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _clear_state(self, repo: str, issue_number: int) -> None:
        path = self._state_path(repo, issue_number)
        if path.exists():
            path.unlink()

    def _feedback_repeated(self, repo: str, issue_number: int, feedback: dict) -> bool:
        path = self._state_path(repo, issue_number)
        if not path.exists():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        last_feedback = data.get("last_feedback")
        if last_feedback == feedback:
            return True
        data["last_feedback"] = feedback
        data["feedback_history"] = data.get("feedback_history", []) + [feedback]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return False

    def _collect_repo_files(self, git_ops: GitOperations) -> list[str]:
        repo_root = git_ops.workdir
        files = []
        for path in repo_root.rglob("*"):
            if path.is_dir():
                continue
            parts = path.relative_to(repo_root).parts
            if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in parts):
                continue
            rel = path.relative_to(repo_root)
            files.append(str(rel))
        return files

    def _select_relevant_files(self, file_paths: list[str], issue_description: str) -> list[str]:
        keywords = self._extract_keywords(issue_description)
        direct_paths = self._extract_paths(issue_description)
        selected: list[str] = []

        common_files = ["README.md", "pyproject.toml", "requirements.txt"]
        for name in common_files:
            if name in file_paths:
                selected.append(name)

        for path in direct_paths:
            if path in file_paths and path not in selected:
                selected.append(path)

        scored = []
        for path in file_paths:
            if path in selected:
                continue
            score = sum(1 for keyword in keywords if keyword in path.lower())
            if score:
                scored.append((score, path))
        scored.sort(reverse=True)
        for _, path in scored[:8]:
            selected.append(path)

        if not selected and file_paths:
            selected.extend(file_paths[:3])
        return selected[:10]

    def _extract_keywords(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9_/-]+", text.lower())
        return {word for word in words if len(word) > 2}

    def _extract_paths(self, text: str) -> set[str]:
        matches = re.findall(r"(?:\\./|/)?[\\w./-]+\\.(?:py|md|txt|toml|yml|yaml)", text)
        return {match.lstrip("./") for match in matches}

    def _safe_read_file(self, git_ops: GitOperations, path: str) -> str | None:
        max_chars = 8000
        try:
            content = git_ops.read_file(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read %s: %s", path, exc)
            return None
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... [truncated]"
        return content

    def _build_issue_context(self, body: str, comments: list) -> str:
        lines = [body.strip()] if body else []
        for comment in comments:
            text = (comment.body or "").strip()
            if text:
                lines.append(f"\nCOMMENT:\n{text}")
        return "\n".join(lines)

    def _post_review_comment(self, repo: str, pr_number: int, review: dict) -> None:
        """Post the review summary as a PR comment."""
        comment = review.get("final_comment")
        if not comment:
            summary = review.get("summary", "").strip()
            tasks = review.get("tasks", [])
            lines = [summary] if summary else []
            for task in tasks:
                message = task.get("message", "")
                file_path = task.get("file")
                line = task.get("line")
                if file_path and line:
                    lines.append(f"- {message} ({file_path}:{line})")
                else:
                    lines.append(f"- {message}")
            comment = "\n".join(line for line in lines if line) or "Review completed."
        self.github.add_pr_comment(repo, pr_number, comment)

    def _record_error(self, repo: str, issue_number: int, exc: Exception) -> None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        state = self._load_state_data(repo, issue_number) or {}
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repo": repo,
            "issue_number": issue_number,
            "iteration": state.get("iteration"),
            "step": state.get("step"),
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        log_path = log_dir / "agent_errors.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _ensure_reviewer(self) -> None:
        if self.reviewer is None:
            self.reviewer = ReviewAgent(github=self.github, llm=self.llm)

    def _prepare_issue_context(self, body: str, comments: list) -> tuple[str, int | None, str]:
        issue_context = self._build_issue_context(body, comments)
        latest_comment = comments[-1] if comments else None
        latest_comment_id = getattr(latest_comment, "id", None)
        latest_comment_body = getattr(latest_comment, "body", "") if latest_comment else ""
        return issue_context, latest_comment_id, latest_comment_body

    def _handle_comment_restart(
        self,
        repo: str,
        issue_number: int,
        state: dict,
        issue_context: str,
        latest_comment_id: int | None,
        latest_comment_body: str,
        plan: dict | None,
        feedback_history: list[dict],
        last_comment_id: int | None,
    ) -> tuple[bool, dict | None, list[dict]]:
        if not latest_comment_id or latest_comment_id == last_comment_id:
            return False, plan, feedback_history

        decision = self.reviewer.comment_requires_restart(
            issue_context,
            latest_comment_body or "",
            plan,
            feedback_history,
        )
        if decision.get("restart", False):
            self.iteration = 0
            plan = None
            feedback_history = []
            self._save_state(
                repo,
                issue_number,
                {
                    **state,
                    "iteration": self.iteration,
                    "step": "restart",
                    "last_issue_comment_id": latest_comment_id,
                    "comment_decision": decision,
                },
            )
            return False, plan, feedback_history

        self._save_state(
            repo,
            issue_number,
            {
                **state,
                "last_issue_comment_id": latest_comment_id,
                "comment_decision": decision,
            },
        )
        if state.get("step") == "completed":
            return True, plan, feedback_history
        return False, plan, feedback_history

    def _render_prompt(self, filename: str, **kwargs: str) -> str:
        prompt_path = Path("prompts") / filename
        template = prompt_path.read_text(encoding="utf-8")
        return template.format(**kwargs)

    def _git_token(self) -> str | None:
        return getattr(self.github, "token", None) or self.config.github_token
