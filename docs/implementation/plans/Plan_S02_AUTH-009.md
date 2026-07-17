# Plan for Story AUTH-009 - Auth Audit Logging

Wire immutable audit logging for identity/auth events. This story is strictly limited to the `audit` schema and auth-event logging — it does not add audit logging to other domains, which will wire their own events into this same table as they're built.

## Goal Description

Implement `audit.audit_logs` (model + migration — the first table in this schema, since Sprint 1 built no domain schemas) and record every security-sensitive identity event, per `06_SECURITY.md`: login, logout, registration, and (in later stories) verification status changes and admin actions.

## Architecture Decisions

- `audit_logs` has no `updated_at`/`deleted_at`/`is_active`/`version` — it's immutable by design, not a business entity with the Common Columns; rows are never updated or deleted, including by administrators.
- A single `AuditLogger.record(actor_user_id, action, entity_type, entity_id, before_state, after_state, ip_address)` service call, used by AUTH-003/AUTH-004 (registration, login) and AUTH-006 (logout, session revocation) — one write path, not duplicated logging code per story.
- No sensitive values (OTP codes, tokens, password hashes) ever go into `before_state`/`after_state` — audit rows are subject to the same "never log secrets" rule as everything else in `06_SECURITY.md`.
- This is additive to AUTH-003 through AUTH-006, not a rebuild — those stories' endpoints get one extra call each to `AuditLogger.record`, not a refactor.

## Tasks

1. Add `audit_logs` model + Alembic migration (first migration touching the `audit` schema).
2. Implement `AuditLogger.record(...)`.
3. Add the logging call to: mobile/OAuth registration, mobile/OAuth login, logout, session revocation (single and "everywhere").
4. Unit tests: a record is created for each event type with the correct `actor_user_id` and no sensitive values present in `before_state`/`after_state`.
5. Confirm audit rows are excluded from any future soft-delete/cascade logic — they are exempt from normal lifecycle rules.
