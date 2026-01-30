# IMPLEMENTATION_GUIDE.md

## Automated GitHub SDLC Agent System

### Project Overview

Build an automated agent system that manages the full Software Development Life Cycle (SDLC) on GitHub. The system consists of two main agents:

- **Code Agent**: Analyzes issues, writes code, creates pull requests
- **Review Agent**: Reviews code changes, analyzes CI/CD results, provides feedback

**Final Product**: A CLI tool that receives a repository URL and issue number, then autonomously writes code, creates PRs, and iterates until the issue is resolved.

---

## Progress Checkpoint (Current State)

**Date**: 2026-01-30

**Completed**
- Repo structure aligned to guide (`src/`, `prompts/`, `docker/`, `.github/workflows/`).
- Core components implemented: config (Pydantic), GitHub client, LLM client, git operations.
- Code Agent + Review Agent implemented under `src/agents/`.
- CLI implemented with Click (`src/cli.py`).
- Prompt templates created in `prompts/`.
- Dockerfile + docker-compose added.
- GitHub Actions workflows added:
  - `.github/workflows/code_agent.yml`
  - `.github/workflows/review_agent.yml`
  - `.github/workflows/ci.yml`
- Unit tests added for GitHub/LLM/agents.
- Documentation updated: `README.md`, `user_integration.md`, `.env.example`.

**In Progress / Blocked**
- End-to-end run against `Sapf3ar/main-sdlc-test` fails due to GitHub token lacking write permissions.
  - Errors: 403 on `git push` and `repos/contents` API.
  - Requires PAT with repo write access (classic `repo` scope) and SSO authorization if org enforced.

**Next Steps**
- Fix PAT permissions, then rerun:
  - `uv run python -m src.cli run --repo Sapf3ar/main-sdlc-test --issue 1`
- Verify PR creation, CI run, and review agent output.

---

## Phase 0: Prerequisites & User Setup

### 0.1 GitHub Account & Repositories Setup

**Goal**: Prepare GitHub environment

**🔴 USER ACTION REQUIRED**

- [ ] **Create/prepare main repository** `ai-coding-agent`
    - Action: Create new repository on GitHub
    - Settings: Public repository
    - Initialize: With README (optional)
- [ ] **Create test repository** for validation
    - Action: Create another repository for testing the agent
    - Suggested name: `ai-coding-test-repo`
    - Add some simple Python code to test with

- [ ] **Generate GitHub Personal Access Token**
    - Navigate to: GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
    - Click: "Generate new token (classic)"
    - Scopes to select:
        - ✅ `repo` (full control of private repositories)
        - ✅ `workflow` (update GitHub Actions workflows)
        - ✅ `write:packages` (optional)
    - Copy token immediately (you won't see it again!)
    - Store securely for later use

**✅ READY TO PROCEED WHEN**:

- [ ] Main repository exists and accessible
- [ ] Test repository exists with some code
- [ ] GitHub token generated and saved
- [ ] You have the repository URLs ready

---

### 0.2 LLM API Setup

**Goal**: Get API access for the AI models

**🔴 USER ACTION REQUIRED - Choose ONE option**

**Option A: OpenAI API**

- [ ] Go to: https://platform.openai.com/
- [ ] Create account or log in
- [ ] Navigate to: API Keys section
- [ ] Create new API key
- [ ] Copy key immediately
- [ ] Add credits if needed (usually requires $5-10 minimum)
- [ ] Model to use: `gpt-4o-mini` (cost-effective)

**Option B: YandexGPT**

- [ ] Go to: https://cloud.yandex.com/
- [ ] Create account or log in
- [ ] Navigate to: Yandex Foundation Models
- [ ] Get API key or IAM token
- [ ] Note your folder ID
- [ ] Model to use: `yandexgpt-lite`

**✅ READY TO PROCEED WHEN**:

- [ ] API key obtained and saved securely
- [ ] API access confirmed (test with simple request if possible)
- [ ] Billing/credits set up if required

---

### 0.3 Environment Variables Preparation

**Goal**: Prepare all secrets and configuration

**🔴 USER ACTION REQUIRED**

Please prepare the following values - you'll be prompted to provide them later:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx          # From step 0.1
GITHUB_REPO_OWNER=your-username                # Your GitHub username
GITHUB_REPO_NAME=ai-coding-agent               # Main repo name
TEST_REPO_OWNER=your-username                  # Same or different
TEST_REPO_NAME=ai-coding-test-repo            # Test repo name

# LLM Configuration (choose one)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx     # If using OpenAI
# OR
YANDEX_API_KEY=xxxxxxxxxxxxxxxxxxxxxx          # If using Yandex
YANDEX_FOLDER_ID=xxxxxxxxxxxxxxxxxxxxxx        # If using Yandex

# Agent Configuration
LLM_PROVIDER=openai                            # or "yandex"
LLM_MODEL=gpt-4o-mini                         # or "yandexgpt-lite"
MAX_ITERATIONS=5                               # Max retry attempts
BASE_BRANCH=main                               # Default branch name
```

**✅ READY TO PROCEED WHEN**:

- [ ] All required values are available
- [ ] Values are stored securely (not in a public place)

---

## Phase 1: Project Setup & Architecture

### 1.1 Repository Structure Setup

**Goal**: Create the foundational project structure

- [ ] Clone main repository locally
- [ ] Create the following directory structure:

```
ai-coding-agent/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── code_agent.py
│   │   └── review_agent.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── github_client.py
│   │   ├── llm_client.py
│   │   └── config.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── parsers.py
│   │   └── validators.py
│   ├── __init__.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   ├── test_code_agent.py
│   └── test_review_agent.py
├── .github/
│   └── workflows/
│       ├── code_agent.yml
│       └── review_agent.yml
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── prompts/
│   ├── code_generation.txt
│   ├── code_review.txt
│   └── error_analysis.txt
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── README.md
└── .env.example
```

**Validation**:

- [ ] All directories created
- [ ] All `__init__.py` files present
- [ ] Git repository initialized

---

### 1.2 Dependencies & Environment

**Goal**: Configure Python environment and dependencies

- [ ] Create `requirements.txt` with core dependencies:

```txt
# GitHub Integration
pygithub>=2.1.1
gitpython>=3.1.40

# LLM Providers
openai>=1.0.0
# yandex-cloud-ml-sdk  # Uncomment if using Yandex

# CLI & Config
click>=8.1.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Code Quality Tools
ruff>=0.1.0
black>=23.0.0
mypy>=1.7.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0

# Utilities
requests>=2.31.0
pyyaml>=6.0.0
```

- [ ] Create `pyproject.toml` for project metadata:

```toml
[project]
name = "ai-coding-agent"
version = "0.1.0"
description = "Automated SDLC agent system for GitHub"
requires-python = ">=3.11"
dependencies = [
    # Will be read from requirements.txt
]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] Create `.env.example`:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=ai-coding-agent

# LLM Configuration (OpenAI)
OPENAI_API_KEY=your_openai_key_here
# OR Yandex
# YANDEX_API_KEY=your_yandex_key_here
# YANDEX_FOLDER_ID=your_folder_id

# Agent Settings
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
MAX_ITERATIONS=5
BASE_BRANCH=main
LOG_LEVEL=INFO
```

- [ ] Create `.gitignore`:

```
# Environment
.env
venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp

# Temporary
temp/
*.log
.DS_Store

# Build
dist/
build/
*.egg-info/
```

**🔴 USER ACTION REQUIRED**

- [ ] **Create `.env` file** (copy from `.env.example`)
- [ ] **Fill in your actual values** from Phase 0.3
- [ ] **Verify `.env` is in `.gitignore`** (critical - don't commit secrets!)

**Validation**:

- [ ] Virtual environment creates successfully
- [ ] All dependencies install without errors
- [ ] `.env` file exists with real values
- [ ] `.env` NOT committed to git

---

### 1.3 Docker Configuration

**Goal**: Containerize the application

- [ ] Create `docker/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install git (required for gitpython)
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY prompts/ ./prompts/

# Set Python path
ENV PYTHONPATH=/app

# Entrypoint
ENTRYPOINT ["python", "-m", "src.cli"]
```

- [ ] Create `docker/docker-compose.yml`:

```yaml
version: "3.8"

services:
    agent:
        build:
            context: ..
            dockerfile: docker/Dockerfile
        env_file:
            - ../.env
        volumes:
            - ../src:/app/src
            - ../prompts:/app/prompts
            - agent-data:/app/data
        command: ["--help"]

volumes:
    agent-data:
```

- [ ] Update `.dockerignore`:

```
.env
venv/
__pycache__/
*.pyc
.git/
.github/
tests/
*.md
.DS_Store
```

**Validation**:

- [ ] `docker build -f docker/Dockerfile .` completes successfully
- [ ] `docker-compose -f docker/docker-compose.yml up` works
- [ ] Container runs without errors

---

## Phase 2: Core Components

### 2.1 Configuration Management

**Goal**: Handle configuration and secrets securely

**File**: `src/core/config.py`

- [ ] Implement configuration using Pydantic Settings:

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    # GitHub
    github_token: str = Field(..., env='GITHUB_TOKEN')
    github_repo_owner: str = Field(..., env='GITHUB_REPO_OWNER')
    github_repo_name: str = Field(..., env='GITHUB_REPO_NAME')

    # LLM
    llm_provider: Literal['openai', 'yandex'] = Field('openai', env='LLM_PROVIDER')
    llm_model: str = Field('gpt-4o-mini', env='LLM_MODEL')
    openai_api_key: str | None = Field(None, env='OPENAI_API_KEY')
    yandex_api_key: str | None = Field(None, env='YANDEX_API_KEY')
    yandex_folder_id: str | None = Field(None, env='YANDEX_FOLDER_ID')

    # Agent
    max_iterations: int = Field(5, env='MAX_ITERATIONS')
    base_branch: str = Field('main', env='BASE_BRANCH')
    log_level: str = Field('INFO', env='LOG_LEVEL')

    class Config:
        env_file = '.env'
        case_sensitive = False

# Singleton instance
settings = Settings()
```

**Validation**:

- [ ] Configuration loads from `.env`
- [ ] Missing required values raise clear errors
- [ ] Sensitive values not logged

---

### 2.2 GitHub Client Implementation

**Goal**: Create wrapper for GitHub API operations

**File**: `src/core/github_client.py`

- [ ] Implement `GitHubClient` class with methods:
    - [ ] `__init__(token: str)` - Initialize with auth
    - [ ] `get_issue(repo: str, issue_number: int) -> Issue` - Fetch issue details
    - [ ] `get_issue_comments(repo: str, issue_number: int) -> list` - Get issue discussion
    - [ ] `create_branch(repo: str, base_branch: str, new_branch: str) -> bool`
    - [ ] `create_pull_request(repo: str, head: str, base: str, title: str, body: str) -> PR`
    - [ ] `update_pull_request(repo: str, pr_number: int, title: str, body: str) -> PR`
    - [ ] `add_pr_comment(repo: str, pr_number: int, comment: str) -> Comment`
    - [ ] `create_review(repo: str, pr_number: int, event: str, body: str, comments: list) -> Review`
    - [ ] `get_pr_files(repo: str, pr_number: int) -> list[File]` - Get changed files
    - [ ] `get_pr_diff(repo: str, pr_number: int) -> str` - Get full diff
    - [ ] `get_workflow_runs(repo: str, pr_number: int) -> list[WorkflowRun]` - Get CI results
    - [ ] `get_check_runs(repo: str, commit_sha: str) -> list[CheckRun]` - Get check statuses
    - [ ] `close_issue(repo: str, issue_number: int, comment: str = None)`
    - [ ] `link_pr_to_issue(repo: str, pr_number: int, issue_number: int)`

- [ ] Add error handling:
    - [ ] Rate limiting (sleep and retry)
    - [ ] Network errors (retry with backoff)
    - [ ] Authentication errors (clear message)
    - [ ] Not found errors (helpful message)

- [ ] Add logging for all operations

**Validation**:

- [ ] Unit tests for each method (with mocks)
- [ ] Integration test with real GitHub API
- [ ] Error cases handled gracefully
- [ ] Rate limiting works

---

### 2.3 LLM Client Implementation

**Goal**: Create wrapper for LLM API calls

**File**: `src/core/llm_client.py`

- [ ] Implement base `LLMClient` interface:

```python
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str = None) -> str:
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, system: str = None) -> dict:
        pass
```

- [ ] Implement `OpenAIClient`:
    - [ ] `__init__(api_key: str, model: str)`
    - [ ] `generate(prompt: str, system: str = None) -> str`
    - [ ] `generate_structured(prompt: str, system: str = None) -> dict`
    - [ ] Handle token limits
    - [ ] Add retry logic
    - [ ] Log token usage

- [ ] Implement `YandexGPTClient` (if needed):
    - [ ] Similar methods as OpenAI
    - [ ] Handle Yandex-specific auth
    - [ ] Convert response format

- [ ] Create factory function:

```python
def create_llm_client(provider: str, **kwargs) -> LLMClient:
    if provider == 'openai':
        return OpenAIClient(...)
    elif provider == 'yandex':
        return YandexGPTClient(...)
```

**Validation**:

- [ ] Test with sample prompts
- [ ] Verify response parsing
- [ ] Test error handling
- [ ] Test both providers (if using both)

---

### 2.4 Git Operations Wrapper

**Goal**: Local git operations for code changes

**File**: `src/core/git_operations.py`

- [ ] Implement `GitOperations` class:
    - [ ] `clone_repo(repo_url: str, target_dir: str, branch: str = 'main')`
    - [ ] `create_branch(branch_name: str)`
    - [ ] `checkout_branch(branch_name: str)`
    - [ ] `get_current_branch() -> str`
    - [ ] `stage_files(files: list[str])`
    - [ ] `commit_changes(message: str)`
    - [ ] `push_changes(branch: str, force: bool = False)`
    - [ ] `get_changed_files() -> list[str]`
    - [ ] `get_repo_structure() -> dict` - Tree of files
    - [ ] `read_file(filepath: str) -> str`
    - [ ] `write_file(filepath: str, content: str)`
    - [ ] `cleanup()` - Remove temporary directory

- [ ] Add context manager support:

```python
with GitOperations(repo_url) as git:
    git.create_branch('fix-123')
    # ... operations ...
    git.push_changes()
# Automatic cleanup
```

**Validation**:

- [ ] Test clone operation
- [ ] Test branch creation and switching
- [ ] Test commit and push
- [ ] Verify cleanup works
- [ ] Test context manager

---

### 2.5 Prompt Templates

**Goal**: Create effective prompts for LLM

- [ ] Create `prompts/code_generation.txt`:

```
You are an expert software developer. You need to implement the following requirement:

ISSUE DESCRIPTION:
{issue_description}

REPOSITORY CONTEXT:
{repo_structure}

RELEVANT FILES:
{relevant_files}

REQUIREMENTS:
1. Write clean, maintainable Python code
2. Follow existing code style and patterns
3. Add appropriate error handling
4. Include docstrings and comments
5. Ensure type hints are used

OUTPUT FORMAT:
Provide your response as a JSON object with this structure:
{
  "analysis": "Brief analysis of what needs to be done",
  "files_to_modify": [
    {
      "path": "path/to/file.py",
      "action": "create|modify|delete",
      "content": "Full file content or null if delete"
    }
  ],
  "commit_message": "Descriptive commit message"
}

Think step by step and provide a complete solution.
```

- [ ] Create `prompts/code_review.txt`:

```
You are an expert code reviewer. Review the following pull request:

ORIGINAL ISSUE:
{issue_description}

CHANGES:
{diff}

CI/CD RESULTS:
{ci_results}

REVIEW CHECKLIST:
1. Does the implementation solve the issue requirements?
2. Is the code quality good (style, structure, patterns)?
3. Are there any bugs or logical errors?
4. Are tests adequate?
5. Are there security concerns?
6. Is documentation sufficient?

OUTPUT FORMAT:
Provide your response as a JSON object:
{
  "decision": "APPROVE|REQUEST_CHANGES|COMMENT",
  "summary": "Overall assessment",
  "issues": [
    {
      "file": "path/to/file.py",
      "line": 123,
      "severity": "error|warning|suggestion",
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ],
  "requirements_met": true/false,
  "ci_passed": true/false
}

Be constructive and specific in your feedback.
```

- [ ] Create `prompts/error_analysis.txt`:

```
You are debugging code that failed CI/CD checks.

ORIGINAL ISSUE:
{issue_description}

PREVIOUS CHANGES:
{previous_diff}

ERRORS:
{errors}

REVIEW FEEDBACK:
{review_feedback}

Analyze the errors and provide fixes.

OUTPUT FORMAT:
{
  "root_cause": "What caused the failures",
  "files_to_modify": [
    {
      "path": "path/to/file.py",
      "content": "Fixed file content"
    }
  ],
  "commit_message": "Fix: ..."
}
```

**Validation**:

- [ ] Templates have all required placeholders
- [ ] JSON format is valid
- [ ] Instructions are clear

---

## Phase 3: Code Agent

### 3.1 Code Agent Core Logic

**Goal**: Implement the agent that writes code

**File**: `src/agents/code_agent.py`

- [ ] Implement `CodeAgent` class with main workflow:

```python
class CodeAgent:
    def __init__(self, github_client, llm_client, config):
        self.github = github_client
        self.llm = llm_client
        self.config = config
        self.iteration = 0

    def process_issue(self, repo: str, issue_number: int) -> bool:
        """Main entry point - process an issue end-to-end"""
        # Implementation below
```

- [ ] Implement workflow steps:
    1. [ ] `fetch_issue()` - Get issue description and metadata
    2. [ ] `check_existing_pr()` - See if PR already exists
    3. [ ] `analyze_requirements()` - Parse requirements with LLM
    4. [ ] `clone_repository()` - Clone target repo locally
    5. [ ] `analyze_codebase()` - Understand structure, find relevant files
    6. [ ] `generate_solution()` - Generate code changes with LLM
    7. [ ] `apply_changes()` - Write changes to files
    8. [ ] `validate_changes()` - Basic syntax check
    9. [ ] `commit_and_push()` - Commit to new branch
    10. [ ] `create_or_update_pr()` - Create/update PR on GitHub

- [ ] Implement iteration handling:
    - [ ] `process_review_feedback(pr_number: int)`
    - [ ] `apply_fixes_from_review(feedback: dict)`
    - [ ] Track iteration count
    - [ ] Enforce max iterations limit
    - [ ] Detect infinite loops (same error repeated)

- [ ] Add state management:
    - [ ] Save state to file after each step
    - [ ] Load state to resume from failures
    - [ ] Clean up state on success

- [ ] Add detailed logging:
    - [ ] Log each step with timestamp
    - [ ] Log LLM prompts and responses
    - [ ] Log file changes
    - [ ] Save logs to file

**Validation**:

- [ ] End-to-end test with simple issue
- [ ] Test iteration logic
- [ ] Verify PR creation
- [ ] Test error recovery
- [ ] Test state persistence

---

### 3.2 CLI Interface

**Goal**: Create user-friendly command-line interface

**File**: `src/cli.py`

- [ ] Implement CLI using Click:

```python
import click
from src.core.config import settings
from src.agents.code_agent import CodeAgent

@click.group()
def cli():
    """AI Coding Agent - Automated SDLC for GitHub"""
    pass

@cli.command()
@click.option('--repo', required=True, help='Repository (owner/name)')
@click.option('--issue', required=True, type=int, help='Issue number')
@click.option('--max-iterations', type=int, help='Max iterations')
@click.option('--dry-run', is_flag=True, help='Simulate without changes')
@click.option('--verbose', is_flag=True, help='Verbose output')
def run(repo, issue, max_iterations, dry_run, verbose):
    """Run the code agent on an issue"""
    # Implementation

@cli.command()
@click.option('--repo', required=True)
@click.option('--issue', required=True, type=int)
def status(repo, issue):
    """Check status of an issue"""
    # Implementation

@cli.command()
def config():
    """Show current configuration"""
    # Implementation

@cli.command()
def test():
    """Test API connections and configuration"""
    # Test GitHub token
    # Test LLM API
    # Show status
```

- [ ] Add rich output:
    - [ ] Progress bars for long operations
    - [ ] Colored output (success=green, error=red, info=blue)
    - [ ] Tables for status display
    - [ ] Spinners for API calls

- [ ] Add error handling:
    - [ ] Catch all exceptions
    - [ ] Show user-friendly messages
    - [ ] Suggest fixes for common errors

**Validation**:

- [ ] `python -m src.cli --help` works
- [ ] All commands documented
- [ ] Test each command
- [ ] Error messages helpful

---

## Phase 4: Review Agent

### 4.1 Review Agent Core Logic

**Goal**: Implement automated code reviewer

**File**: `src/agents/review_agent.py`

- [ ] Implement `ReviewAgent` class:

```python
class ReviewAgent:
    def __init__(self, github_client, llm_client, config):
        self.github = github_client
        self.llm = llm_client
        self.config = config

    def review_pull_request(self, repo: str, pr_number: int) -> dict:
        """Main entry point - review a PR"""
```

- [ ] Implement workflow:
    1. [ ] `fetch_pr_context(pr_number)` - Get PR details, author, description
    2. [ ] `fetch_original_issue()` - Find linked issue
    3. [ ] `fetch_pr_diff()` - Get all code changes
    4. [ ] `fetch_pr_files()` - Get list of changed files
    5. [ ] `wait_for_ci()` - Wait for CI/CD to complete (timeout: 10 min)
    6. [ ] `fetch_ci_results()` - Get GitHub Actions results
    7. [ ] `analyze_with_llm()` - Send context to LLM for review
    8. [ ] `parse_review_response()` - Parse LLM JSON response
    9. [ ] `post_review_to_github()` - Submit review to PR

- [ ] Implement review checks:
    - [ ] **Requirements coverage**: Does it solve the issue?
    - [ ] **Code quality**: Style, patterns, structure
    - [ ] **Tests**: Are there tests? Do they pass?
    - [ ] **CI status**: Did all jobs pass?
    - [ ] **Security**: Any obvious vulnerabilities?
    - [ ] **Documentation**: Are changes documented?

- [ ] Implement review outcomes:
    - [ ] **APPROVE**: All checks passed
    - [ ] **REQUEST_CHANGES**: Issues found, needs fixes
    - [ ] **COMMENT**: Minor suggestions, doesn't block

- [ ] Format review output:
    - [ ] Overall summary comment
    - [ ] Line-by-line comments for specific issues
    - [ ] Actionable suggestions
    - [ ] Link back to issue requirements

**Validation**:

- [ ] Test with various PR scenarios
- [ ] Test CI results parsing
- [ ] Test review posting
- [ ] Validate LLM response quality

---

### 4.2 CI/CD Results Parser

**Goal**: Extract meaningful data from GitHub Actions

**File**: `src/utils/ci_parser.py`

- [ ] Implement CI parser:
    - [ ] `get_workflow_status(runs: list) -> str` - overall, success, failure
    - [ ] `extract_failed_jobs(runs: list) -> list` - which jobs failed
    - [ ] `extract_error_messages(run: WorkflowRun) -> list[str]`
    - [ ] `format_ci_summary() -> str` - human-readable summary

- [ ] Handle different CI states:
    - [ ] All passed ✓
    - [ ] Some failed ✗
    - [ ] Still running ⋯
    - [ ] Cancelled/skipped

**Validation**:

- [ ] Test with successful CI runs
- [ ] Test with failed CI runs
- [ ] Test with mixed results
- [ ] Test with no CI configured

---

## Phase 5: GitHub Actions Integration

### 5.1 Code Agent Workflow

**Goal**: Trigger Code Agent on new issues

**File**: `.github/workflows/code_agent.yml`

- [ ] Create workflow:

```yaml
name: Code Agent

on:
    issues:
        types: [opened, labeled]

jobs:
    run-agent:
        runs-on: ubuntu-latest
        # Only run on issues with 'ai-agent' label
        if: contains(github.event.issue.labels.*.name, 'ai-agent')

        steps:
            - name: Checkout repository
              uses: actions/checkout@v4

            - name: Set up Python
              uses: actions/setup-python@v5
              with:
                  python-version: "3.11"

            - name: Install dependencies
              run: |
                  pip install -r requirements.txt

            - name: Run Code Agent
              env:
                  GITHUB_TOKEN: ${{ secrets.AGENT_GITHUB_TOKEN }}
                  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
                  # Add other secrets
              run: |
                  python -m src.cli run \
                    --repo ${{ github.repository }} \
                    --issue ${{ github.event.issue.number }}

            - name: Upload logs
              if: always()
              uses: actions/upload-artifact@v4
              with:
                  name: agent-logs
                  path: logs/
```

**🔴 USER ACTION REQUIRED**

- [ ] **Add GitHub Secrets** to your repository:
    - Navigate to: Repository Settings → Secrets and variables → Actions
    - Add the following secrets:
        - `AGENT_GITHUB_TOKEN` - Your GitHub token from Phase 0.1
        - `OPENAI_API_KEY` - Your OpenAI key from Phase 0.2 (or Yandex equivalent)
        - Any other environment variables needed

**Validation**:

- [ ] Workflow file is valid YAML
- [ ] Secrets are configured
- [ ] Test by creating an issue with `ai-agent` label
- [ ] Check workflow runs in Actions tab
- [ ] Verify agent executes

---

### 5.2 Review Agent Workflow

**Goal**: Trigger Review Agent on PR events

**File**: `.github/workflows/review_agent.yml`

- [ ] Create workflow:

```yaml
name: Review Agent

on:
    pull_request:
        types: [opened, synchronize, ready_for_review]
    workflow_run:
        workflows: ["CI"]
        types: [completed]

jobs:
    review:
        runs-on: ubuntu-latest

        steps:
            - name: Checkout repository
              uses: actions/checkout@v4

            - name: Set up Python
              uses: actions/setup-python@v5
              with:
                  python-version: "3.11"

            - name: Install dependencies
              run: |
                  pip install -r requirements.txt

            - name: Wait for CI
              uses: lewagon/wait-on-check-action@v1.3.1
              with:
                  ref: ${{ github.event.pull_request.head.sha }}
                  running-workflow-name: "review"
                  repo-token: ${{ secrets.GITHUB_TOKEN }}
                  wait-interval: 10

            - name: Run Review Agent
              env:
                  GITHUB_TOKEN: ${{ secrets.AGENT_GITHUB_TOKEN }}
                  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
              run: |
                  python -m src.agents.review_agent \
                    --repo ${{ github.repository }} \
                    --pr ${{ github.event.pull_request.number }}

            - name: Upload review results
              if: always()
              uses: actions/upload-artifact@v4
              with:
                  name: review-results
                  path: review-results.json
```

**Validation**:

- [ ] Workflow triggers on PR creation
- [ ] Workflow waits for CI
- [ ] Review agent runs successfully
- [ ] Review is posted to PR

---

### 5.3 CI/CD Pipeline (Test Repository)

**Goal**: Set up CI checks in test repository

**File**: `.github/workflows/ci.yml` (in test repo)

- [ ] Create basic CI workflow:

```yaml
name: CI

on:
    pull_request:
    push:
        branches: [main]

jobs:
    lint:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
            - uses: actions/setup-python@v5
              with:
                  python-version: "3.11"
            - name: Install dependencies
              run: |
                  pip install ruff black mypy
                  pip install -r requirements.txt
            - name: Run ruff
              run: ruff check .
            - name: Run black
              run: black --check .
            - name: Run mypy
              run: mypy src/

    test:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4
            - uses: actions/setup-python@v5
              with:
                  python-version: "3.11"
            - name: Install dependencies
              run: pip install -r requirements.txt pytest pytest-cov
            - name: Run tests
              run: pytest tests/ --cov=src --cov-report=xml
            - name: Upload coverage
              uses: codecov/codecov-action@v3
              with:
                  file: ./coverage.xml
```

**Validation**:

- [ ] CI runs on PRs in test repo
- [ ] All jobs complete
- [ ] Results visible in PR
- [ ] Review agent can access results

---

## Phase 6: Webhook Service (Optional - Bonus Points)

### 6.1 Webhook Server Setup

**Goal**: Create standalone service for GitHub webhooks

**File**: `src/webhook_server.py`

**Note**: This is optional but gives bonus points. Skip if doing basic GitHub Actions approach.

- [ ] Implement Flask/FastAPI server:

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

@app.post("/webhook/github")
async def github_webhook(request: Request):
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(signature, await request.body()):
        raise HTTPException(403)

    payload = await request.json()
    event = request.headers.get('X-GitHub-Event')

    # Route to appropriate handler
    if event == 'issues':
        await handle_issue(payload)
    elif event == 'pull_request':
        await handle_pull_request(payload)

    return {"status": "ok"}
```

- [ ] Implement handlers:
    - [ ] `handle_issue(payload)` - Trigger Code Agent
    - [ ] `handle_pull_request(payload)` - Trigger Review Agent
    - [ ] `handle_workflow_run(payload)` - Process CI results

- [ ] Add job queue (optional but recommended):
    - [ ] Use Redis + RQ or Celery
    - [ ] Queue long-running tasks
    - [ ] Retry failed tasks

**🔴 USER ACTION REQUIRED (if implementing webhook)**

- [ ] **Choose deployment approach**:
    - Option A: Cloud deployment (see Phase 6.2)
    - Option B: Local with ngrok (see below)

**Option B Setup: Local + ngrok**

- [ ] Install ngrok: https://ngrok.com/
- [ ] Run: `ngrok http 8000`
- [ ] Note the HTTPS URL (e.g., `https://abc123.ngrok.io`)
- [ ] This URL will be used for GitHub webhook

**Validation**:

- [ ] Server starts without errors
- [ ] Health check endpoint works
- [ ] Signature verification works
- [ ] Handlers execute correctly

---

### 6.2 Cloud Deployment (Optional - Extra Bonus)

**Goal**: Deploy service to cloud platform

**🔴 USER ACTION REQUIRED - Choose ONE cloud provider**

**Option A: Cloud.ru**

- [ ] **Sign up for Cloud.ru**
    - Go to: https://cloud.ru
    - Create account
    - Activate free tier

- [ ] **Deploy application**:
    - [ ] Create new project
    - [ ] Set up container registry
    - [ ] Push Docker image
    - [ ] Create compute instance
    - [ ] Configure environment variables
    - [ ] Set up logging

- [ ] **Get public URL**:
    - [ ] Configure load balancer
    - [ ] Enable HTTPS
    - [ ] Note the public URL

**Option B: Yandex Cloud**

- [ ] **Sign up for Yandex Cloud**
    - Go to: https://console.yandex.cloud
    - Create account
    - Activate free tier

- [ ] **Deploy using Serverless Containers**:
    - [ ] Create container registry
    - [ ] Push Docker image
    - [ ] Create serverless container
    - [ ] Set environment variables
    - [ ] Configure service account

- [ ] **Get public URL**:
    - [ ] Create API Gateway
    - [ ] Link to container
    - [ ] Enable HTTPS
    - [ ] Note the invoke URL

**For both options:**

**🔴 USER ACTION: Configure GitHub Webhook**

- [ ] Go to your repository Settings → Webhooks
- [ ] Click "Add webhook"
- [ ] Payload URL: `https://your-cloud-url/webhook/github`
- [ ] Content type: `application/json`
- [ ] Secret: Generate a random secret and save it
- [ ] Events: Select "Issues" and "Pull requests"
- [ ] Active: ✓

- [ ] **Add webhook secret to your deployment**:
    - Environment variable: `GITHUB_WEBHOOK_SECRET=your_secret`

**Validation**:

- [ ] Service is accessible via public URL
- [ ] GitHub webhook delivers successfully
- [ ] Events trigger correctly
- [ ] Logs show webhook reception
- [ ] End-to-end flow works

---

### 6.3 GitHub App (Optional - Maximum Bonus)

**Goal**: Package as installable GitHub App

**🔴 USER ACTION REQUIRED**

- [ ] **Create GitHub App**:
    - Navigate to: GitHub Settings → Developer settings → GitHub Apps
    - Click "New GitHub App"
    - Fill in details:
        - Name: "AI Coding Agent" (or unique name)
        - Homepage URL: Your repo URL
        - Webhook URL: Your cloud URL from 6.2
        - Webhook secret: Same as configured
    - **Permissions** (select these):
        - Repository permissions:
            - ✅ Contents: Read & write
            - ✅ Issues: Read & write
            - ✅ Pull requests: Read & write
            - ✅ Workflows: Read & write
            - ✅ Metadata: Read-only
        - Subscribe to events:
            - ✅ Issues
            - ✅ Pull request
            - ✅ Workflow run
    - **Where can this GitHub App be installed?**
        - Select: "Any account"
    - Click "Create GitHub App"

- [ ] **Download private key**:
    - After creation, scroll down
    - Click "Generate a private key"
    - Download the `.pem` file
    - Store securely

- [ ] **Note these values**:
    - App ID (shown at top of settings page)
    - Client ID
    - Private key location

**🔴 USER ACTION: Install the App**

- [ ] Go to your GitHub App page
- [ ] Click "Install App" (in left sidebar)
- [ ] Select your account
- [ ] Choose repositories to install on
- [ ] Click "Install"

- [ ] Implement App authentication in code:

```python
# src/core/github_app_auth.py
import jwt
import time
from github import Github, GithubIntegration

class GitHubAppAuth:
    def __init__(self, app_id: str, private_key_path: str):
        self.app_id = app_id
        with open(private_key_path, 'r') as f:
            self.private_key = f.read()

    def get_installation_token(self, installation_id: int) -> str:
        integration = GithubIntegration(self.app_id, self.private_key)
        return integration.get_access_token(installation_id).token
```

- [ ] Update webhook handler to use App auth
- [ ] Update configuration to support App mode

**Validation**:

- [ ] App can be installed on test repository
- [ ] Webhooks trigger correctly with App
- [ ] App can create PRs and comments
- [ ] Can be installed on multiple repos

---

## Phase 7: Testing & Validation

### 7.1 Unit Tests

**Goal**: Ensure individual components work

- [ ] Test `GitHubClient` (`tests/test_github_client.py`):
    - [ ] Mock all API calls
    - [ ] Test happy paths
    - [ ] Test error cases
    - [ ] Test rate limiting

- [ ] Test `LLMClient` (`tests/test_llm_client.py`):
    - [ ] Mock API responses
    - [ ] Test prompt formatting
    - [ ] Test JSON parsing
    - [ ] Test error handling

- [ ] Test `CodeAgent` (`tests/test_code_agent.py`):
    - [ ] Mock dependencies
    - [ ] Test workflow steps
    - [ ] Test iteration logic
    - [ ] Test state management

- [ ] Test `ReviewAgent` (`tests/test_review_agent.py`):
    - [ ] Mock GitHub API
    - [ ] Mock LLM responses
    - [ ] Test review generation
    - [ ] Test decision logic

**Validation**:

- [ ] Run: `pytest tests/ -v`
- [ ] All tests pass
- [ ] Coverage > 70%: `pytest --cov=src --cov-report=html`
- [ ] No warnings

---

### 7.2 Integration Tests

**Goal**: Test full end-to-end workflows

**🔴 USER ACTION REQUIRED**

- [ ] **Prepare test issues in test repository**:

**Test Issue 1: Simple Bug Fix**

```markdown
Title: Fix division by zero in calculator
Labels: ai-agent

Description:
The `divide` function in `src/calculator.py` crashes when the divisor is zero.

Expected behavior:

- Should raise a `ValueError` with message "Cannot divide by zero"

Acceptance criteria:

- [ ] Function handles zero divisor
- [ ] Error message is clear
- [ ] Tests added for edge case
```

**Test Issue 2: Add New Feature**

```markdown
Title: Add factorial function
Labels: ai-agent

Description:
Add a `factorial` function to `src/calculator.py`

Requirements:

- Function should calculate factorial of a number
- Handle negative numbers (raise ValueError)
- Handle 0 (return 1)
- Include type hints
- Add tests

Acceptance criteria:

- [ ] Function implemented correctly
- [ ] Handles edge cases
- [ ] Tests have 100% coverage
```

**Test Issue 3: Refactoring**

```markdown
Title: Refactor calculator to use class
Labels: ai-agent

Description:
Refactor calculator functions into a Calculator class

Requirements:

- Create Calculator class
- Move all functions as methods
- Maintain backward compatibility
- Update all tests

Acceptance criteria:

- [ ] Calculator class created
- [ ] All functionality preserved
- [ ] Tests pass
- [ ] Code is cleaner
```

- [ ] **Run integration tests**:
    - [ ] Create each issue
    - [ ] Monitor agent execution
    - [ ] Verify PRs created
    - [ ] Check CI passes
    - [ ] Verify reviews posted
    - [ ] Confirm issue resolved

**Validation**:

- [ ] **Test 1**: Simple fix completes in 1-2 iterations
- [ ] **Test 2**: Feature completes in 2-3 iterations
- [ ] **Test 3**: Refactor completes in 3-5 iterations
- [ ] No infinite loops
- [ ] All issues eventually resolved
- [ ] PRs are mergeable

---

### 7.3 Performance & Stability Tests

**Goal**: Ensure system is reliable

- [ ] **Performance metrics**:
    - [ ] Measure time per iteration
    - [ ] Track LLM token usage
    - [ ] Monitor API rate limits
    - [ ] Calculate success rate

- [ ] **Stability tests**:
    - [ ] Test with multiple concurrent issues
    - [ ] Test recovery from failures:
        - [ ] Network timeout
        - [ ] API rate limit
        - [ ] Invalid LLM response
        - [ ] Git conflicts
    - [ ] Test max iterations limit
    - [ ] Test state persistence

- [ ] **Security scan**:
    - [ ] Run: `pip install safety && safety check`
    - [ ] Run: `pip install bandit && bandit -r src/`
    - [ ] Review generated code for:
        - [ ] SQL injection risks
        - [ ] Command injection
        - [ ] Hardcoded secrets
        - [ ] Unsafe deserialization

**Validation**:

- [ ] Average iteration time < 5 minutes
- [ ] Success rate > 80%
- [ ] No crashes during testing
- [ ] Security scans pass
- [ ] API limits respected

---

## Phase 8: Documentation & Delivery

### 8.1 README.md

**Goal**: Complete user-facing documentation

- [ ] Write comprehensive `README.md`:

````markdown
# AI Coding Agent

Automated SDLC agent system for GitHub that writes code, creates PRs, and iteratively fixes issues until resolved.

## Features

- 🤖 Automatically implements code from GitHub issues
- 🔄 Iterative development with code review
- ✅ CI/CD integration
- 📝 Automated code review
- 🐳 Docker support
- ☁️ Cloud deployable (optional)

## Quick Start

### Prerequisites

- Python 3.11+
- GitHub account and token
- OpenAI API key (or Yandex)
- Docker (optional)

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Fill in your credentials
4. Install dependencies: `pip install -r requirements.txt`

### Usage

```bash
# Run agent on an issue
python -m src.cli run --repo owner/repo --issue 123

# Check configuration
python -m src.cli test

# Docker
docker-compose up -d
docker-compose exec agent python -m src.cli run --repo owner/repo --issue 123
```
````

## How It Works

1. User creates issue with `ai-agent` label
2. Code Agent analyzes issue and writes code
3. PR is created automatically
4. CI/CD runs tests
5. Review Agent checks code quality
6. If issues found, cycle repeats
7. When approved, issue is closed

## Configuration

See `.env.example` for all configuration options.

## Architecture

[Include diagram]

## Examples

See [EXAMPLES.md](EXAMPLES.md) for demonstrations.

## Deployment

### Local

```bash
docker-compose up -d
```

### Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md)

## Contributing

[Guidelines]

## License

MIT

````

**Validation**:
- [ ] README is clear and complete
- [ ] All code examples work
- [ ] Links are valid
- [ ] Screenshots/diagrams included

---

### 8.2 SDLC Report
**Goal**: Document system operation and results

**File**: `SDLC_REPORT.md`

- [ ] Write comprehensive report covering:

**1. System Overview**
- Architecture diagram
- Component descriptions
- Tech stack with versions
- Design decisions

**2. Implementation Details**
- Code Agent workflow
- Review Agent workflow
- Iteration mechanism
- State management

**3. Test Results**
- Issues tested (minimum 3)
- Success metrics:
  - Total issues: X
  - Successfully resolved: Y
  - Success rate: Z%
  - Average iterations: N
  - Average time per issue: T minutes
  - Token usage per issue: K tokens

**4. Example Demonstrations**
- Link to Issue #1 and its PR
- Link to Issue #2 and its PR
- Link to Issue #3 and its PR
- Screenshots of reviews
- Explanation of iteration cycles

**5. Performance Analysis**
- Response times
- Resource usage
- Cost analysis (API calls)
- Bottlenecks identified

**6. Limitations & Known Issues**
- Edge cases not handled
- Current limitations
- Known bugs
- Workarounds

**7. Future Improvements**
- Potential enhancements
- Scalability considerations
- Feature ideas

**8. Conclusion**
- Summary of achievements
- Lessons learned

**Validation**:
- [ ] Report is professional
- [ ] Includes real data
- [ ] Has working links
- [ ] Metrics are accurate

---

### 8.3 Additional Documentation

- [ ] Create `DEPLOYMENT.md` (if cloud deployed):
  - Cloud setup steps
  - Configuration
  - Monitoring
  - Troubleshooting

- [ ] Create `EXAMPLES.md`:
  - Walkthrough of test issues
  - Before/after code
  - Review comments
  - Iteration history

- [ ] Create `CONTRIBUTING.md`:
  - How to contribute
  - Code style
  - Testing requirements
  - PR process

**Validation**:
- [ ] All docs are complete
- [ ] Examples are real
- [ ] Instructions are tested

---

## Phase 9: Final Checklist & Submission

### 9.1 Pre-Submission Checklist

**Code Quality**
- [ ] All code formatted: `black src/ tests/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] No hardcoded secrets (double-check!)
- [ ] Logging implemented consistently
- [ ] Error handling comprehensive
- [ ] Comments and docstrings complete

**Testing**
- [ ] Unit tests pass: `pytest tests/`
- [ ] Integration tests completed
- [ ] Test coverage > 70%
- [ ] Manual testing completed
- [ ] All test scenarios work

**Docker**
- [ ] `Dockerfile` builds successfully
- [ ] `docker-compose up -d` works
- [ ] Container runs agent correctly
- [ ] All dependencies included
- [ ] Environment variables configured

**GitHub Integration**
- [ ] Code Agent workflow triggers
- [ ] Review Agent workflow triggers
- [ ] PRs created correctly
- [ ] Reviews posted correctly
- [ ] CI/CD integration works
- [ ] Webhooks working (if applicable)

**Documentation**
- [ ] `README.md` complete
- [ ] `SDLC_REPORT.md` complete
- [ ] Code documented
- [ ] Examples provided
- [ ] Setup instructions tested

**Repository**
- [ ] Repository is public or accessible
- [ ] `.gitignore` configured correctly
- [ ] No sensitive data committed
- [ ] Clean commit history
- [ ] Tags/releases created

---

### 9.2 Deliverables Checklist

**Primary Repository** (`ai-coding-agent`)
- [ ] Complete source code in `src/`
- [ ] Working CLI
- [ ] Docker configuration
- [ ] Tests in `tests/`
- [ ] GitHub Actions workflows
- [ ] Documentation (README, SDLC_REPORT, etc.)
- [ ] Requirements files
- [ ] `.env.example` with all variables

**Test Repository**
- [ ] At least 3 test issues created
- [ ] CI/CD workflow configured
- [ ] Example PRs from agent
- [ ] Demonstrated iteration cycles
- [ ] Closed/resolved issues

**Documentation Deliverables**
- [ ] `README.md` - Setup and usage
- [ ] `SDLC_REPORT.md` - Results and analysis
- [ ] `DEPLOYMENT.md` - If cloud deployed
- [ ] `EXAMPLES.md` - Demonstrations

**Demonstrations Required**
- [ ] At least 3 successful issue→PR→review cycles
- [ ] Example of iteration (review→fix→approve)
- [ ] Example of error handling
- [ ] Screenshots/videos (optional but recommended)

---

### 9.3 Bonus Points Checklist

**Cloud Deployment** (Choose one)
- [ ] Deployed on Cloud.ru with public URL
- [ ] Deployed on Yandex Cloud with public URL
- [ ] Deployment documented
- [ ] Service is stable and accessible

**Advanced Features**
- [ ] Webhook service (not just GitHub Actions)
- [ ] GitHub App implementation
- [ ] Test generation capability
- [ ] Code coverage improvements
- [ ] Smart CI/CD adaptation
- [ ] Advanced error recovery

**Quality Enhancements**
- [ ] Comprehensive logging/monitoring
- [ ] Performance optimizations
- [ ] Security hardening
- [ ] Extensive documentation
- [ ] High test coverage (>80%)

---

## User Assistance Summary

Throughout implementation, you'll need to provide:

**Phase 0 - Setup (REQUIRED)**
1. ✅ GitHub account and repository URLs
2. ✅ GitHub Personal Access Token
3. ✅ LLM API key (OpenAI or Yandex)
4. ✅ Create and fill `.env` file

**Phase 5 - GitHub Actions (REQUIRED)**
5. ✅ Add secrets to GitHub repository
6. ✅ Create test issues with `ai-agent` label

**Phase 6 - Cloud/Webhook (OPTIONAL)**
7. ⭐ Cloud account setup (Cloud.ru or Yandex)
8. ⭐ Configure GitHub webhook
9. ⭐ Create GitHub App (maximum bonus)

**Phase 7 - Testing (REQUIRED)**
10. ✅ Create test scenarios
11. ✅ Monitor and validate results

---

## Success Criteria

### Must Have ✅
1. Python 3.11+ implementation
2. CLI tool for running agent
3. Code Agent writes code from issues
4. Review Agent analyzes PRs and CI
5. Multiple iteration support
6. GitHub Actions workflows
7. Docker deployment (`docker-compose up`)
8. 3+ working examples in test repository
9. Complete documentation

### Should Have ✅
1. No infinite loops (max iterations enforced)
2. Reasonable execution time (<5 min/iteration)
3. Proper error handling
4. Code quality tools integration
5. Test coverage >70%
6. Clean, readable code

### Nice to Have ⭐
1. Cloud deployment (Cloud.ru or Yandex Cloud)
2. Webhook service implementation
3. GitHub App packaging
4. Test generation
5. Advanced error recovery
6. High code quality scores

---

## Quick Reference Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
# Edit .env with your values
````

### Development

```bash
# Run agent
python -m src.cli run --repo owner/repo --issue 123

# Run tests
pytest tests/ -v --cov=src

# Code quality
ruff check src/
black src/
mypy src/
```

### Docker

```bash
# Build
docker build -f docker/Dockerfile -t ai-coding-agent .

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up -d

# Run CLI in container
docker-compose exec agent python -m src.cli run --repo owner/repo --issue 123

# View logs
docker-compose logs -f agent
```

### Testing GitHub Actions

```bash
# View workflows
gh workflow list

# Trigger manually
gh workflow run code_agent.yml

# View runs
gh run list

# View logs
gh run view <run-id> --log
```

---

## Tips for Success

1. **Start Simple**: Get basic issue→code→PR working first
2. **Test Early**: Don't wait - test GitHub integration ASAP
3. **Prompt Engineering**: Good prompts are critical - iterate on them
4. **Error Handling**: APIs fail - plan for it from the start
5. **Rate Limits**: Both GitHub and LLM APIs have limits
6. **Logging**: Essential for debugging - log everything
7. **Iteration Limits**: Always cap iterations to prevent runaway loops
8. **Cost Monitoring**: Track LLM API costs during development
9. **Git Cleanup**: Clean up test branches regularly
10. **Documentation**: Write docs as you go, not at the end

---

## Getting Help

If you encounter issues:

1. **Check logs** - Most problems show up in logs
2. **Review GitHub Actions** - Check workflow runs
3. **Test configuration** - Run `python -m src.cli test`
4. **Verify secrets** - Ensure all environment variables set
5. **Check API status** - GitHub/OpenAI might be down
6. **Rate limits** - You might be hitting API limits

Good luck! 🚀
