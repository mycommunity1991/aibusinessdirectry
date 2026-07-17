# Plan for Story AUTH-001 - Identity Domain Models & Migration

Create the SQLAlchemy models and Alembic migration for the Identity domain's structural tables. This story is strictly limited to schema and seed data — no endpoints, no authentication logic, no token handling.

## Goal Description

Establish the persistence layer for `identity` schema entities defined in `04_DATABASE.md`: `users`, `roles`, `permissions`, `role_permissions`, `user_roles`. This is the first business-domain schema in the project — Sprint 1 shipped zero domain models — so it also establishes the pattern (Common Columns mixin, enum usage, constraint naming) that every later domain migration will follow.

## Architecture Decisions

- Add a reusable `CommonColumnsMixin` (id UUID, created_at/by, updated_at/by, deleted_at, is_active, version) per `04_DATABASE.md` Common Columns — every business table going forward inherits it, not just this one.
- Native PostgreSQL enums for `user_status`, `auth_provider`, `language_code` per `04_DATABASE.md` Enum Types — these are small, stable value sets.
- Partial unique constraints on `users.email`, `(phone_country_code, phone_number)`, and `(auth_provider, external_auth_subject)` — all `WHERE ... IS NOT NULL`, since a user may have only one of the three identifiers at registration.
- `chk_users_has_identifier` CHECK constraint enforcing at least one identifier is present.
- `roles`/`permissions`/`role_permissions`/`user_roles` as plain join/reference tables — `role_permissions` and `user_roles` use composite PKs and only `created_at`, per the Common Columns exception for join tables.
- Seed data (not a migration-embedded fixture, a repeatable seed script): three roles — `customer`, `provider`, `admin` — matching `03_DOMAIN_MODEL.md`.

## Tasks

1. Add `backend/app/models/identity.py` (or `models/identity/` if the module needs to split later) with `User`, `Role`, `Permission`, `RolePermission`, `UserRole` models.
2. Add the `CommonColumnsMixin` under a shared models location so later domains reuse it without duplication.
3. Define the three enums as native Postgres types via SQLAlchemy.
4. Generate the Alembic migration (`identity` schema tables + enums + constraints + indexes per `04_DATABASE.md`).
5. Write a seed script/fixture for the three roles — idempotent, safe to re-run.
6. Unit tests: model construction, constraint violations (duplicate email, missing identifier), enum validity.
7. Verify migration upgrade/downgrade locally.
