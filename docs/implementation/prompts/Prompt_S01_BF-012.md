# Prompt for BF-012 (Sprint 1)

As a developer, I want a reusable repository layer that isolates database access from business logic, so that services remain focused on business rules and persistence concerns are centralized, consistent, and easily testable.

## Technical Context & Architecture Constraints
This story establishes the repository foundation only.
It must strictly follow the approved backend architecture:
Router -> Service -> Repository -> Database

Repositories are the only layer allowed to communicate directly with SQLAlchemy and the database.

Do NOT implement:
- Authentication
- User repositories
- Community repositories
- Feed repositories
- Any business-specific repositories
- Any business services
- Any API endpoints
- Any database models
- Any migrations

This story prepares infrastructure only.
Follow these architectural principles:
- Async-first implementation
- Strong typing using generics
- Dependency inversion
- SOLID principles
- Repository Pattern
- Clean Architecture
- Production-ready implementation
- No duplicated database access logic
- No business logic inside repositories

The BaseRepository must become the common parent for all future repositories.
Repository interfaces should define contracts only.
The implementation must align with the project Architecture, Coding Standards, Database Design, Security Standards, and Domain Model documentation.

## Implementation Instructions
1. Create a reusable generic asynchronous `BaseRepository`.
2. Use SQLAlchemy AsyncSession injected through the constructor.
3. Implement common reusable operations such as:
   - get_by_id()
   - get_all()
   - create()
   - update()
   - delete()
   - exists()
4. Use Python generics (`TypeVar`, `Generic`) for model typing.
5. Keep the repository independent from any domain model.
6. Create a repository interfaces package containing abstract base contracts using `ABC`.
7. Define a generic repository interface describing common CRUD operations.
8. Ensure repository methods are asynchronous throughout.
9. Do not perform commits inside individual CRUD methods unless this matches the project's Unit of Work approach. Reuse the existing database session lifecycle established in previous stories.
10. Ensure repository methods raise exceptions rather than swallowing them. Existing global exception handling should remain responsible for API responses.
11. Add comprehensive docstrings and type hints.
12. Keep methods small, focused, and production-ready.
13. Add unit tests covering the generic repository behavior where practical using test doubles or isolated test models. Do not require business entities.
14. Update project documentation if repository architecture documentation exists.
