from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
import hmac
import hashlib
import logging

from src.agents.code_agent import CodeAgent
from src.agents.review_agent import ReviewAgent
from src.core.config import settings
from src.core.github_client import create_github_client
from src.core.llm_client import create_llm_client


logger = logging.getLogger(__name__)
app = FastAPI()


def _verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Validate the GitHub webhook signature."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected}")


def _should_process_issue(payload: dict) -> bool:
    """Return True if the issue event should trigger the code agent."""
    action = payload.get("action")
    if action not in {"opened", "edited", "labeled", "reopened"}:
        return False
    labels = payload.get("issue", {}).get("labels", [])
    return any(label.get("name") == "ai-agent" for label in labels)


def _handle_issue(payload: dict) -> None:
    """Process an issue event in the background."""
    repo = payload["repository"]["full_name"]
    issue_number = payload["issue"]["number"]

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
    agent.process_issue(repo, issue_number)


def _handle_pull_request(payload: dict) -> None:
    """Run a review pass when PR events occur."""
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        return
    repo = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    issue_description = payload["pull_request"].get("body") or payload["pull_request"].get("title", "")

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
    review = agent.review_pr(repo, pr_number, issue_description)
    agent.post_review(repo, pr_number, review)


def _handle_workflow_run(payload: dict) -> None:
    """Run a review pass when a workflow finishes."""
    action = payload.get("action")
    if action != "completed":
        return
    repo = payload["repository"]["full_name"]
    for pr in payload.get("workflow_run", {}).get("pull_requests", []):
        pr_number = pr.get("number")
        if not pr_number:
            continue
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
        pull = github.get_pull(repo, pr_number)
        issue_description = pull.body or pull.title
        review = agent.review_pr(repo, pr_number, issue_description)
        agent.post_review(repo, pr_number, review)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    body = await request.body()
    event = request.headers.get("X-GitHub-Event")
    signature = request.headers.get("X-Hub-Signature-256")

    if settings.github_webhook_secret:
        if not _verify_signature(settings.github_webhook_secret, body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set. Skipping signature verification.")

    payload = await request.json()
    if event == "issues" and _should_process_issue(payload):
        background_tasks.add_task(_handle_issue, payload)
    elif event == "pull_request":
        background_tasks.add_task(_handle_pull_request, payload)
    elif event == "workflow_run":
        background_tasks.add_task(_handle_workflow_run, payload)

    return {"status": "ok"}
