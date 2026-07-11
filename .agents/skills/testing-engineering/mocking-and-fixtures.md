# Rule: Mocking & Fixtures

## Mocking Boundaries
* **Only Mock I/O:** You may only mock external infrastructure boundaries (e.g., third-party APIs, AWS services, external payment gateways, or time/clock functions).
* **Do Not Mock Domain Entities:** Never mock pure domain models or internal business services. Pass real instances or use Factory builders.
* **Avoid Magic Mocks:** Minimize the use of generic `MagicMock` or `patch`. Prefer creating explicit, lightweight "Fake" classes that implement the same interface/protocol as the real dependency.

## Test Data Management (Fixtures)
* **Pytest Fixtures:** Use `pytest` fixtures extensively for dependency injection within the test suite (e.g., injecting the `AsyncSession`, `TestClient`, or authenticated user headers).
* **Factory Pattern:** Use factories (like `factory_boy` in Python) to generate deterministic, typed test data rather than manually writing large JSON payloads or raw dictionaries.
* **Database State Isolation:** Every test must run in isolation. Use transactional fixtures that roll back all database changes after the test completes, ensuring that one test's data does not pollute another.