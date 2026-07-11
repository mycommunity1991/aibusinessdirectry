# Rule: Python & FastAPI Standards

## Python 3.14+ Idioms
* **Modern Typing:** Use standard collections for typing (`list[str]`, `dict[str, int]`, `str | None`) instead of the deprecated `typing` module (`List`, `Dict`, `Union`, `Optional`).
* **Dataclasses & Pydantic:** Use standard `@dataclass` for internal, non-validated data structures. Use Pydantic v2 strictly for external data validation (API boundaries, configuration).

## FastAPI Dependency Injection
* **Explicit Dependencies:** Use FastAPI's `Depends()` exclusively for cross-cutting concerns at the API layer (e.g., extracting the current user from a token, database session injection).
* **Do Not Chain Deeply:** Avoid deep, nested dependency graphs within FastAPI `Depends()`. If a dependency requires multiple sub-services, construct it explicitly in the application registry or composition root.

## State and Configuration
* **No Global State:** Never use global mutable variables. All configurations must be loaded via Pydantic `BaseSettings` and injected where needed.
* **Statelessness:** The backend application must remain completely stateless. Any state must be offloaded to PostgreSQL or Redis.