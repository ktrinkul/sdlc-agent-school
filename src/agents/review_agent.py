from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import logging

import click

from src.core.config import settings
from src.core.github_client import GitHubClient, create_github_client
from src.core.llm_client import LLMClient, create_llm_client


logger = logging.getLogger(__name__)


@dataclass
class ReviewAgent:
    """Reviewer agent that provides plans, reviews, and restart decisions."""

    github: GitHubClient
    llm: LLMClient

    def generate_plan(
        self, issue_description: str, repo_structure: str, relevant_files: str
    ) -> dict:
        try:
            prompt = self._render_prompt(
                "implementation_plan.txt",
                issue_description=issue_description,
                repo_structure=repo_structure,
                relevant_files=relevant_files,
            )
        except OSError as exc:
            logger.warning("Failed to read implementation plan prompt: %s", exc)
            prompt = (
                "Create a JSON plan with summary, plan, acceptance_criteria.\n"
                f"Issue:\n{issue_description}\n\nRepo:\n{repo_structure}\n\nFiles:\n{relevant_files}"
            )
        return self.llm.generate_structured(
            prompt, system="Return only valid JSON. Do not include markdown."
        )

    def review_changes(
        self,
        issue_description: str,
        plan: dict,
        diff: str,
        feedback_history: list[dict],
    ) -> dict:
        try:
            prompt = self._render_prompt(
                "review_feedback.txt",
                issue_description=issue_description,
                plan=json.dumps(plan, indent=2),
                diff=diff,
                feedback_history=json.dumps(feedback_history, indent=2),
            )
        except OSError as exc:
            logger.warning("Failed to read review feedback prompt: %s", exc)
            prompt = (
                "Review the diff against the issue and plan. Return JSON with summary, tasks, final_comment.\n"
                f"Issue:\n{issue_description}\n\nPlan:\n{plan}\n\nDiff:\n{diff}\n\nHistory:\n{feedback_history}"
            )
        return self.llm.generate_structured(
            prompt, system="Return only valid JSON. Do not include markdown."
        )

    def comment_requires_restart(
        self,
        issue_description: str,
        comment_body: str,
        plan: dict | None,
        feedback_history: list[dict],
    ) -> dict:
        try:
            prompt = self._render_prompt(
                "issue_comment_review.txt",
                issue_description=issue_description,
                comment_body=comment_body,
                plan=json.dumps(plan, indent=2) if plan else "null",
                feedback_history=json.dumps(feedback_history, indent=2),
            )
        except OSError as exc:
            logger.warning("Failed to read issue comment review prompt: %s", exc)
            prompt = (
                "Decide if the new comment requires restart. Return JSON with restart, summary, reason.\n"
                f"Issue:\n{issue_description}\n\nComment:\n{comment_body}\n\nPlan:\n{plan}\n\nHistory:\n{feedback_history}"
            )
        return self.llm.generate_structured(
            prompt, system="Return only valid JSON. Do not include markdown."
        )

    def review_pr(self, repo: str, pr_number: int, issue_description: str) -> dict:
        diff = self.github.get_pr_diff(repo, pr_number)
        ci_results = self.github.get_workflow_runs(repo, pr_number)
        try:
            prompt = self._render_prompt(
                "code_review.txt",
                issue_description=issue_description,
                diff=diff,
                ci_results=json.dumps(ci_results, indent=2),
            )
        except OSError as exc:
            logger.warning("Failed to read code review prompt: %s", exc)
            prompt = (
                "Review the PR diff and CI results. Return JSON with summary and issues.\n"
                f"Issue:\n{issue_description}\n\nDiff:\n{diff}\n\nCI:\n{ci_results}"
            )
        return self.llm.generate_structured(
            prompt, system="Return only valid JSON. Do not include markdown."
        )

    def post_review(self, repo: str, pr_number: int, review: dict) -> None:
        decision = review.get("decision", "COMMENT")
        summary = review.get("summary", "")
        issues = review.get("issues", [])
        body_lines = [summary] if summary else []
        for issue in issues:
            body_lines.append(
                f"- {issue.get('severity', 'info')}: {issue.get('message')} "
                f"({issue.get('file')}:{issue.get('line')})"
            )
        body = "\n".join(body_lines) or "Review completed."
        self.github.create_review(repo, pr_number, decision, body, [])

    def _render_prompt(self, filename: str, **kwargs: str) -> str:
        prompt_path = Path("prompts") / filename
        template = prompt_path.read_text(encoding="utf-8")
        return template.format(**kwargs)


@click.command()
@click.option("--repo", required=True, help="Repository (owner/name)")
@click.option("--pr", "pr_number", required=True, type=int, help="Pull request number")
def main(repo: str, pr_number: int) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    github = create_github_client(settings, repo=repo)
    llm = create_llm_client(
        settings.llm_provider,
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        base_url=settings.openai_base_url,
        referer=settings.openrouter_referer,
        title=settings.openrouter_title,
    )
    agent = ReviewAgent(github=github, llm=llm)
    pr = github.get_pull(repo, pr_number)
    issue_description = pr.body or pr.title
    review = agent.review_pr(repo, pr_number, issue_description)
    Path("review-results.json").write_text(json.dumps(review, indent=2), encoding="utf-8")
    agent.post_review(repo, pr_number, review)


if __name__ == "__main__":
    main()
