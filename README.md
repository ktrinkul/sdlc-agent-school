# AI Coding Agent

Automated SDLC agent system for GitHub that writes code, creates PRs, and iteratively
fixes issues until resolved.

## Features

- Automatically implements code from GitHub issues
- Iterative development with code review
- CI/CD integration via GitHub Actions
- Docker support

## Quick Start

### Prerequisites

- Python 3.11+
- GitHub token
- OpenAI API key (or Yandex)
- Docker (optional)

### Installation

1) Clone the repository
2) Copy `.env.example` to `.env`
3) Fill in your credentials
4) Install dependencies:

```bash
pip install -r requirements.txt
```

### Usage

```bash
# Run agent on an issue
python -m src.cli run --repo owner/repo --issue 123

# Check configuration
python -m src.cli test

# Docker
docker-compose -f docker/docker-compose.yml up -d
docker-compose -f docker/docker-compose.yml exec agent python -m src.cli run --repo owner/repo --issue 123
```

## How It Works

1) User creates issue with `ai-agent` label
2) Code Agent analyzes issue and writes code
3) PR is created automatically
4) CI/CD runs tests
5) Review Agent checks code quality
6) If issues found, cycle repeats
7) When approved, issue is closed

## Configuration

See `.env.example` for all configuration options.
Use `GITHUB_AUTH_MODE=app` with `GITHUB_APP_*` values to authenticate via a GitHub App.

## Architecture

- `src/agents/` contains Code and Review agents
- `src/core/` contains GitHub, LLM, and git wrappers
- `prompts/` holds LLM prompt templates

## Deployment

### Local

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Contributing

See `AGENTS.md` for repository guidelines.

## License

MIT
