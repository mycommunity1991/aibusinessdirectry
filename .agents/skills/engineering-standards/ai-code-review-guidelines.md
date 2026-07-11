# Rule: AI Code Review Guidelines

## The Review Checklist
When acting as a code reviewer, you must evaluate every Pull Request against these specific failure conditions. Reject the PR if any of the following occur:

### 1. Architecture Violations
* **Boundary Leak:** Domain logic depends on a framework (e.g., FastAPI, SQLAlchemy).
* **Controller Bloat:** Business logic is implemented inside a FastAPI router instead of a Service.
* **Direct Data Access:** A Service queries the database directly instead of using a Repository, or a Repository implements business validation.

### 2. Implementation Violations
* **Typing Missing:** Functions or variables lack explicit Python 3.14+ type hints. `Any` is used without explicit justification.
* **Blocking I/O:** Synchronous blocking calls (e.g., `requests`, `time.sleep()`, heavy CPU loops) are used inside an `async def` context.
* **Lazy Loading:** SQLAlchemy models rely on lazy loading instead of explicit `selectinload` or `joinedload`.

### 3. Testing Violations
* **Missing Coverage:** New business logic is introduced without corresponding Unit Tests.
* **Mocking the Domain:** Domain entities or pure business logic are mocked in tests (only I/O and external dependencies should be mocked).