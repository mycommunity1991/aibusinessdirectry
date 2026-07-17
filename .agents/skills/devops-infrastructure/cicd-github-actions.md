# Rule: CI/CD with GitHub Actions

## Pipeline Structure
* **Fail Fast:** Order pipeline steps cheapest-first — lint, then type-check, then unit tests, then integration tests — so a trivial style error doesn't wait behind a slow test suite to fail.
* **Pin Tool Versions:** Pin `uv`, Python, and Flutter versions explicitly in the workflow file; never rely on a runner's "latest" default, which can silently change behavior between runs.

## Deployment Gates
* **Manual Approval for Production:** Production deploys require an explicit approval gate in the GitHub Actions workflow — staging deploys on merge to main can be automatic, production must not be.
* **Rollback Path:** Every deploy workflow must have a documented, tested rollback (previous image tag redeploy) — a one-way deploy pipeline is an incomplete pipeline.
