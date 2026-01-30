# Repository Guidelines

## Project Structure & Module Organization

- `main.py` contains the current CLI entry point (prints a placeholder message).
- `IMPLEMENTATION_GUIDE.md` is the primary roadmap for building the SDLC agent system.
- `pyproject.toml` defines the Python package metadata.

## Build, Test, and Development Commands

- `python main.py` runs the current entry point locally.
- `python -m pip install -e .` installs the package in editable mode (useful once dependencies are added).
- No build or test scripts are defined yet; add commands here when tooling is introduced.

## Coding Style & Naming Conventions

- Language: Python 3.8+ (see `pyproject.toml`).
- Indentation: 4 spaces; follow PEP 8 naming (`snake_case` for functions/variables, `PascalCase` for classes).
- Keep modules small and focused; prefer explicit imports over wildcard imports.
- If you add formatting or linting tools (e.g., `ruff`, `black`), document the exact command and config.

## Testing Guidelines

- No testing framework is configured yet.
- If you add tests, place them in a top-level `tests/` directory and name files `test_*.py`.
- Document the test command (e.g., `python -m pytest`) once tooling exists.

## Commit & Pull Request Guidelines

- Git history is empty; no commit convention is established.
- Suggested default: short, imperative commit subjects (e.g., "Add review agent skeleton").
- Pull requests should include a concise summary, a list of key changes, and any manual verification steps.

## Architecture & Planning Notes

- Follow `IMPLEMENTATION_GUIDE.md` for the intended multi-agent workflow, phases, and checkpoints.
- If you deviate from the guide, note the rationale in the PR description.
