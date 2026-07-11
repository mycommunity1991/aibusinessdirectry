**Active Story:** Sprint 1 | BF-017 | Code Quality Tools Configuration

**Story:**
As a developer, I want automated Python code quality tooling configured so that coding standards are enforced consistently across the project and code quality issues are detected before changes are merged.

## Technical Context & Architecture Constraints

This story is strictly limited to configuring project-wide linting.

Follow the existing project architecture, Coding Standards, Engineering Playbook, Technology Stack, and AI documentation.

Requirements:

- Use Ruff as the project's official Python linter.
- Do not introduce any additional linting, formatting, or type-checking tools.
- Do not modify application behavior or business logic.
- Do not refactor unrelated code solely to satisfy personal style preferences.
- Preserve the existing Modular Monolith architecture.
- Keep configuration centralized and maintainable.
- Ensure compatibility with the existing uv-based development workflow.

## Implementation Instructions

1. Configure Ruff using the project's centralized configuration (prefer `pyproject.toml` unless the project already uses another approved configuration location).
2. Configure:
   - Target Python version matching the project.
   - Appropriate line length consistent with project formatting.
   - Recommended Ruff rule set for production FastAPI projects.
   - Exclusions for generated files, virtual environments, cache directories, migration artifacts, and other appropriate non-source directories.
3. Verify import ordering support using Ruff's built-in functionality instead of introducing external tooling.
4. Execute Ruff across the complete backend source tree.
5. Resolve every lint violation without changing application behavior.
6. Update the backend README (or developer documentation) with:
   - How to run Ruff
   - How to automatically fix supported issues
   - Expected lint command
7. Confirm:
   - Ruff completes successfully.
   - Zero lint errors remain.
8. Ensure no architectural layers, APIs, database models, security components, or business modules are modified.
9. Upon successful implementation and verification, commit and push all changes to the remote Git repository using the following commit message:

   `BF-017: Configure Ruff code quality tooling`

## Definition of Done

- Ruff configuration added.
- Project linting succeeds with zero errors.
- Developer documentation updated.
- No functional or architectural changes introduced.
- Changes committed and pushed to the remote repository.
