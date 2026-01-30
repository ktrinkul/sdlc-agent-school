# User Integration Guide

## Overview

This repository implements a two-agent SDLC workflow:
the Code Agent creates PRs from issues, and the Review Agent evaluates them.
Agents run either locally via CLI or automatically via GitHub Actions.

## Setup

1) Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2) Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Keep `.env` out of version control.

### GitHub App Auth (Optional)

To use a GitHub App instead of a PAT, set:

```bash
GITHUB_AUTH_MODE=app
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=123456
```

If `GITHUB_APP_INSTALLATION_ID` is omitted, the CLI will attempt to resolve the
installation from the target repository.

## Run Locally

```bash
python -m src.cli run --repo owner/repo --issue 123
```

Other commands:

```bash
python -m src.cli test
python -m src.cli status --repo owner/repo --issue 123
```

Review Agent (manual):

```bash
python -m src.agents.review_agent --repo owner/repo --pr 1
```

## GitHub Actions

1) Add repository secrets:
   - `AGENT_GITHUB_TOKEN`
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL` (set to `https://openrouter.ai/api/v1` for OpenRouter)

2) Label issues with `ai-agent` to trigger the Code Agent workflow.

## Testing

```bash
pytest tests/ -v
```

Create test issues in a sandbox repo and verify PR creation, CI results,
and review comments match expectations.
