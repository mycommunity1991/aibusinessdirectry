# Plan: S01 BF-017 - Code Quality Tools Configuration

## Objective
Configure Ruff as the official Python linter for the MyCommunity backend project, ensuring consistent code quality, formatting, and import ordering across the codebase without introducing behavioral changes.

## Proposed Changes

### 1. `backend/pyproject.toml`
#### [MODIFY] pyproject.toml
- Add `ruff` to the `dev` dependency-groups.
- Under `[tool.ruff]`:
  - Add `target-version = "py314"` to match project requirements.
  - Add appropriate `exclude` patterns (e.g., `alembic`, `.venv`, `.git`, `__pycache__`).
  - Maintain `line-length = 88`.
- Under `[tool.ruff.lint]`:
  - Keep the recommended rule set (e.g., `E`, `W`, `F`, `I`, `N`, `UP`, `B`, `C4`, `T20`, `SIM`).
- Remove `[tool.black]` and `[tool.isort]` configurations since Ruff will handle import sorting (`I` rule) and formatting.

### 2. Linting and Fixing
- Run `uv run ruff check --fix .` and `uv run ruff format .` (if formatting is enabled, but the story focuses on linting. The story says "Configure Ruff code quality tooling" and "Verify import ordering support using Ruff's built-in functionality"). We'll rely on `ruff check` for import ordering and linting.
- Resolve any remaining lint violations manually if they cannot be auto-fixed, ensuring no application behavior changes.

### 3. `backend/README.md`
#### [MODIFY] README.md
- Add a new section under "Useful Development Commands" or a dedicated "Code Quality" section.
- Document how to run Ruff for linting (`uv run ruff check .`) and how to automatically fix issues (`uv run ruff check --fix .`).

## Verification Plan

### Automated Tests
- Run the full test suite using `uv run pytest` to ensure no behavioral changes have occurred.
- Execute `uv run ruff check .` to verify zero lint errors remain.

### Manual Verification
- Review changes made by `--fix` to ensure no business logic was unintentionally modified.
