from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
from typing import Iterable
import logging

from git import Repo


logger = logging.getLogger(__name__)


@dataclass
class GitOperations:
    """Lightweight git wrapper used by the agent to modify a repo."""

    repo_url: str
    base_branch: str = "main"
    token: str | None = None
    _repo: Repo | None = None
    _workdir: Path | None = None

    def __enter__(self) -> "GitOperations":
        self.clone_repo(self.repo_url, branch=self.base_branch)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    @property
    def workdir(self) -> Path:
        if not self._workdir:
            raise RuntimeError("Repository not cloned yet")
        return self._workdir

    def clone_repo(self, repo_url: str, target_dir: str | None = None, branch: str = "main"):
        """Clone the repository to a temp dir or the provided target directory."""
        if target_dir:
            target = Path(target_dir)
        else:
            target = Path(tempfile.mkdtemp(prefix="ai-coding-agent-"))
        self._workdir = target
        clone_url = self._with_token(repo_url)
        self._repo = Repo.clone_from(clone_url, target, branch=branch)
        if self._repo and self.token:
            self._repo.remote().set_url(clone_url)
        return self._repo

    def create_branch(self, branch_name: str) -> None:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        self._repo.git.checkout("-b", branch_name)

    def ensure_branch(self, branch_name: str) -> None:
        """Checkout or create the branch locally, stashing changes if needed."""
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        stash_created = self._stash_if_needed()
        try:
            self._repo.remotes.origin.fetch()
            remote_refs = {ref.name for ref in self._repo.remotes.origin.refs}
            if branch_name in {head.name for head in self._repo.heads}:
                self._repo.git.checkout(branch_name)
                return
            remote_ref = f"origin/{branch_name}"
            if remote_ref in remote_refs:
                self._repo.git.checkout("-b", branch_name, remote_ref)
                return
            self._repo.git.checkout("-b", branch_name)
        finally:
            if stash_created:
                self._restore_stash()

    def checkout_branch(self, branch_name: str) -> None:
        """Checkout an existing local branch, stashing changes if needed."""
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        stash_created = self._stash_if_needed()
        try:
            self._repo.git.checkout(branch_name)
        finally:
            if stash_created:
                self._restore_stash()

    def get_current_branch(self) -> str:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        return self._repo.active_branch.name

    def stage_files(self, files: Iterable[str]) -> None:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        self._repo.index.add(list(files))

    def commit_changes(self, message: str) -> None:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        self._repo.index.commit(message)

    def push_changes(self, branch: str, force: bool = False) -> None:
        """Push the local branch to the remote."""
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        if self.token:
            self._repo.remote().set_url(self._with_token(self.repo_url))
        self._repo.remote().push(refspec=f"{branch}:{branch}", force=force)

    def get_changed_files(self) -> list[str]:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        return [item.a_path for item in self._repo.index.diff(None)]

    def get_repo_structure(self) -> dict:
        """Return a nested dict of the repository file tree."""
        tree = {}
        for path in self.workdir.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(self.workdir)
            parts = rel.parts
            current = tree
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = None
        return tree

    def read_file(self, filepath: str) -> str:
        path = self.workdir / filepath
        return path.read_text(encoding="utf-8")

    def write_file(self, filepath: str, content: str) -> None:
        path = self.workdir / filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def cleanup(self) -> None:
        if self._workdir and self._workdir.exists():
            shutil.rmtree(self._workdir)
        self._workdir = None
        self._repo = None

    def _with_token(self, repo_url: str) -> str:
        if not self.token:
            return repo_url
        if repo_url.startswith("https://"):
            if repo_url.endswith(".git"):
                base = repo_url
            else:
                base = f"{repo_url}.git"
            return base.replace("https://", f"https://x-access-token:{self.token}@")
        return repo_url

    def _stash_if_needed(self) -> bool:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        if not self._repo.is_dirty(untracked_files=True):
            return False
        before = self._stash_count()
        message = "agent-autostash"
        self._repo.git.stash("push", "-u", "-m", message)
        after = self._stash_count()
        created = after > before
        if created:
            logger.warning("Repository had local changes; stashed before branch switch.")
        return created

    def _restore_stash(self) -> None:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        try:
            self._repo.git.stash("pop")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to re-apply stashed changes: %s", exc)

    def _stash_count(self) -> int:
        if not self._repo:
            raise RuntimeError("Repository not initialized")
        output = self._repo.git.stash("list")
        lines = [line for line in output.splitlines() if line.strip()]
        return len(lines)
