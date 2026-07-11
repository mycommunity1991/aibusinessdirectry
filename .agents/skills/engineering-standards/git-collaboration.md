# Rule: Git & Collaboration

## Commit Standards (Conventional Commits)
All commits must strictly follow the Conventional Commits specification to allow for automated semantic versioning and changelog generation.
* **Format:** `<type>(<optional scope>): <description>`
* **Types:**
  * `feat`: A new feature.
  * `fix`: A bug fix.
  * `docs`: Documentation only changes.
  * `style`: Changes that do not affect the meaning of the code (white-space, formatting).
  * `refactor`: A code change that neither fixes a bug nor adds a feature.
  * `perf`: A code change that improves performance.
  * `test`: Adding missing tests or correcting existing tests.
  * `chore`: Changes to the build process or auxiliary tools.

## Pull Request Standards
* **Atomic PRs:** Pull Requests must be small, atomic, and solve a single business problem or technical task.
* **Title:** Must match the Conventional Commits format.
* **Rebasing:** Always rebase feature branches against the `main` branch before submitting a PR to maintain a linear, clean history.