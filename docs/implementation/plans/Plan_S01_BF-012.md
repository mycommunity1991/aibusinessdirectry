# Base Repository Implementation Plan (Sprint 1 | BF-012)

This plan covers the creation of the generic asynchronous `BaseRepository` that all future business repositories will inherit from, establishing the foundational data access pattern.

## Proposed Changes

### Repository Interfaces
#### [NEW] `app/repositories/interfaces/base.py`
Create `IBaseRepository[ModelType]` Abstract Base Class defining the contract for generic CRUD operations:
- `get_by_id(id: Any) -> ModelType | None`
- `get_all(skip: int = 0, limit: int = 100) -> Sequence[ModelType]`
- `create(obj_in: dict[str, Any] | ModelType) -> ModelType`
- `update(db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType`
- `delete(id: Any) -> bool`
- `exists(id: Any) -> bool`

### Base Repository Implementation
#### [NEW] `app/repositories/base_repository.py`
Implement `BaseRepository[ModelType: Base]` inheriting from `IBaseRepository`.
- Accept `AsyncSession` via constructor.
- Implement async methods using `select`, `delete`, etc. from SQLAlchemy.
- Do not call `session.commit()` inside these methods (delegate to Unit of Work/service layer).
- Use `app.core.database.base.Base` as the generic bound for `ModelType`.
- Let exceptions propagate upwards.

### Tests
#### [NEW] `tests/test_base_repository.py`
- Create an isolated test model (`DummyModel`) extending `Base` purely for testing.
- Write unit tests for `get_by_id`, `get_all`, `create`, `update`, `delete`, and `exists` using a mocked `AsyncSession`.
- Ensure tests verify that exceptions are allowed to propagate and no `commit` is issued by the repository.

### Documentation
- `docs/implementation/prompts/Prompt_S01_BF-012.md`: Store the original prompt.
- `docs/implementation/plans/Plan_S01_BF-012.md`: Store this execution plan.
- `docs/implementation/walkthroughs/Walkthrough_S01_BF-012.md`: Store the walkthrough upon completion.

## Verification Plan
- Run `pytest tests/test_base_repository.py -v` to verify repository methods.
- Run `ruff check` and `ruff format --check` to ensure code style compliance.
- Run `mypy` to check type hinting.
