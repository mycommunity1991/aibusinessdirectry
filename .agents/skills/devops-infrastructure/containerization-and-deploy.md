# Rule: Containerization & Deployment

## Docker
* **Multi-Stage Builds:** Build the FastAPI image in a multi-stage Dockerfile (`uv sync` in a build stage, slim runtime stage) to keep the production image minimal and free of dev dependencies.
* **Non-Root Runtime:** The container process runs as a non-root user; never run `uvicorn` as `root` in the production image.

## AWS & Nginx
* **Nginx as the Edge:** Nginx terminates TLS and reverse-proxies to the FastAPI/Uvicorn process — the application itself never handles TLS termination directly.
* **Stateless App Tier:** The FastAPI containers hold no local state (sessions/rate-limits live in Redis, files live in object storage) so the app tier can scale horizontally on AWS without sticky sessions.
