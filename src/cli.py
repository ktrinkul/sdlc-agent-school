from __future__ import annotations

import logging
from pathlib import Path

import click

from src.agents.code_agent import CodeAgent
from src.core.config import settings
from src.core.github_client import create_github_client
from src.core.llm_client import create_llm_client


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "agent.log"),
    ]
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers
    )


@click.group()
def cli() -> None:
    """AI Coding Agent - Automated SDLC for GitHub."""


@cli.command()
@click.option("--repo", required=True, help="Repository (owner/name)")
@click.option("--issue", required=True, type=int, help="Issue number")
@click.option("--max-iterations", type=int, help="Max iterations")
@click.option("--dry-run", is_flag=True, help="Simulate without changes")
@click.option("--verbose", is_flag=True, help="Verbose output")
def run(repo: str, issue: int, max_iterations: int | None, dry_run: bool, verbose: bool) -> None:
    """Run the agent for a single issue."""
    _configure_logging(verbose)
    if max_iterations:
        settings.max_iterations = max_iterations

    github = create_github_client(settings, repo=repo)
    llm = create_llm_client(
        settings.llm_provider,
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        base_url=settings.openai_base_url,
        referer=settings.openrouter_referer,
        title=settings.openrouter_title,
    )

    agent = CodeAgent(github=github, llm=llm, config=settings)
    if dry_run:
        click.echo("Dry run mode is not yet supported in the full workflow.")
        return
    success = agent.process_issue(repo, issue)
    if success:
        click.echo("Issue processed successfully.")
    else:
        click.echo("Issue processing failed.")


@cli.command()
@click.option("--repo", required=True)
@click.option("--issue", required=True, type=int)
def status(repo: str, issue: int) -> None:
    """Print issue status."""
    github = create_github_client(settings, repo=repo)
    issue_obj = github.get_issue(repo, issue)
    click.echo(f"Issue #{issue}: {issue_obj.title} ({issue_obj.state})")


@cli.command()
def config() -> None:
    """Print the current configuration summary."""
    click.echo(f"LLM provider: {settings.llm_provider}")
    click.echo(f"LLM model: {settings.llm_model}")
    click.echo(f"Base branch: {settings.base_branch}")


@cli.command()
def test() -> None:
    """Smoke test API access for GitHub and the LLM provider."""
    repo = f"{settings.github_repo_owner}/{settings.github_repo_name}"
    github = create_github_client(settings, repo=repo)
    llm = create_llm_client(
        settings.llm_provider,
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        base_url=settings.openai_base_url,
        referer=settings.openrouter_referer,
        title=settings.openrouter_title,
    )

    try:
        _ = github._get_repo(f"{settings.github_repo_owner}/{settings.github_repo_name}")
        click.echo("GitHub token: OK")
    except Exception as exc:  # noqa: BLE001
        click.echo(f"GitHub token failed: {exc}")

    try:
        _ = llm.generate("ping")
        click.echo("LLM API: OK")
    except Exception as exc:  # noqa: BLE001
        click.echo(f"LLM API failed: {exc}")


if __name__ == "__main__":
    cli()
