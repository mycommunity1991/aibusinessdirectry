# Checkpoint — Sprint 04, PRO-001 (Create My Business or Freelancer Listing)

**Written by:** `backend` agent
**Status:** Backend implementation complete and tested. Mobile (frontend) implementation not started. Not yet reviewed by `tester`/`architect`.

## What's done (backend, items 1-20 of `Plan_S04_PRO-001.md`)

- Alembic migration `6133c77f062e_provider_domain` (down-revision `9f47869ca8bb`), creates `provider` schema, `provider_type`/`listing_source`/`verification_status` enums, and `providers` (+ flagged `category_label` column, Decision 4)/`business_profiles`/`freelancer_profiles` tables. Upgrade and downgrade both verified against a real scratch Postgres database; column/constraint/index layout confirmed via `\d` against `04_DATABASE.md`.
- `backend/app/modules/provider/` module: `models.py`, `repositories/{provider,business_profile,freelancer_profile}_repository.py`, `services/provider_service.py`, `schemas.py`, `api.py`, `dependencies.py`.
- `backend/app/modules/identity/services/role_assignment_service.py` (`RoleAssignmentService.ensure_role_assigned`) + `get_role_assignment_service()` added to `backend/app/modules/identity/dependencies.py`. `AuthService` untouched.
- `ProviderAlreadyExistsError` (409) / `ProviderNotFoundError` (404) added to `backend/app/core/exceptions/`.
- Router registered at `/providers` in `backend/app/api/v1/api.py`. `backend/tests/conftest.py` and `backend/alembic/env.py` updated to import/register `app.modules.provider.models`.
- Tests: `backend/tests/modules/provider/test_provider_service.py` (18 cases), `test_provider_endpoints.py` (13 cases), `backend/tests/modules/identity/test_role_assignment_service.py` (5 cases) — all passing. Full backend suite: 293 passed, 0 failed.
- `ruff check .` / `ruff format --check .` clean project-wide. `mypy` on new/changed files clean (pre-existing, unrelated errors remain in untouched files: `app/core/security.py`, `app/modules/audit/*`, `app/modules/identity/services/id_token_verifier.py` — confirmed via `git status` these were never touched by this story).

## What's next

- `frontend` agent: mobile half of PRO-001 (items 21-37 of the Plan) — `step_indicator.dart`, `features/provider/` module, onboarding wizard screens (S-15/S-16/S-17/S-18a/S-18b), Profile & Settings CTA integration, routes, tests.
- `tester` agent: verify all 10 ACs per the Plan's Verification Plan table once mobile lands (or backend-only verification first, if the chain runs backend review before frontend).
- `architect` agent: review Decision 1 (`provider -> identity` role-grant direction) against ADR-014, Decision 4 (`category_label` flagged column), Decision 2 (single-POST endpoint shape) against ADR-015.
- Deferred to story close (per Plan, not yet done): record ADR-016 for Decision 1 in `09_DECISIONS.md`; update `04_DATABASE.md` for `category_label`; update `12_TECH_STACK.md` for `google_maps_flutter`/`geolocator`/`geocoding`. None of this is `backend`'s doc to touch — flagged for `tech-lead`.

## Environment notes for whoever runs tests next

- This sandbox's `backend/.venv` (built via `uv sync` under Python 3.14.0rc2, per `.python-version`) has a real, pre-existing incompatibility between the pinned `pydantic`/`pydantic-settings` versions and Python 3.14.0rc2's `typing` internals (`_eval_type() got an unexpected keyword argument 'prefer_fwd_module'`) — this affects the **entire** app, not anything from this story; reproduced on `tests/test_health.py` before any PRO-001 change was applied. Verification in this session was instead done via a separate, throwaway Python 3.13 venv (not committed, not part of the repo) with the same dependency versions installed via pip. Flagging this for `tech-lead`/whoever owns CI, since it will block anyone else in this same sandbox from running `uv run pytest` directly until either Python 3.14 is stable-released with a fix, or `pydantic`/`pydantic-settings` are bumped to a version that supports 3.14.0rc2.
- Local Postgres (`ai_marketplace_test`, `ai_marketplace_scratch` scratch DB) and Redis needed to be started (`service postgresql start`, `service redis-server start`) and `pg_hba.conf`'s `host ... 127.0.0.1/32` line needed to be `trust` (it defaulted to `scram-sha-256` on this fresh install) to match what `tests/conftest.py`'s own comment already documents as the expected local setup ("this project's local Postgres requires no password"). This was a local machine-config fix, not a repo change.
