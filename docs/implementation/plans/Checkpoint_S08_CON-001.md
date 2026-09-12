# Checkpoint — Story CON-001 (Contact a Matched Provider Directly)

**Owner of this checkpoint:** `backend` (this update)
**Status:** Backend implementation complete, all tests green. Frontend has not started.

---

## Current task

Backend Proposed Changes items 1–15 of `docs/implementation/plans/Plan_S08_CON-001.md` are done. Full backend
test suite passes (702 passed, 0 failed/errored) and `ruff check .` / `ruff format --check` are clean across the
repo.

## What's done

1. **Migration** `backend/alembic/versions/2026_09_12_1000-024bcc0fbaf8_contact_domain.py` — creates the
   `contact` schema and `contact_views` table exactly per `04_DATABASE.md` (full `CommonColumnsMixin`,
   `customer_id`/`provider_id` FKs not null, `search_request_id` FK nullable, `viewed_at` default `now()`,
   the three named indexes). Verified end-to-end against a real Postgres database: `alembic upgrade head` from
   the pre-existing head (`f3a1c9d47b02`) applies cleanly, `downgrade -1` fully removes the `contact` schema, and
   re-`upgrade head` re-applies cleanly. `backend/alembic/env.py` updated to import
   `app.modules.contact.models` (every new domain module's own established convention).
2. **New module `backend/app/modules/contact/`** — `models.py` (`ContactView`), `repositories/
   contact_view_repository.py`, `services/contact_service.py` (`ContactService.create_contact_view`, the
   self-dealing guard per Decision 1 — resolves customer profile, resolves+404s the provider, guards on
   `provider.user_id == current_user_id` **before** any row is written, validates an optional
   `search_request_id`'s ownership, creates the row (no dedup), notifies the provider's owner if claimed),
   `schemas.py`, `api.py` (`POST /contact-views`), `dependencies.py`.
3. `backend/app/core/exceptions/exceptions.py` + `__init__.py` — new `SelfDealingContactError` (403) and a new
   `CustomerProfileNotFoundError` (404, defensive-only; **deviation from the Plan's literal item 3**, which named
   only `SelfDealingContactError` — see Walkthrough note below).
4. `backend/app/modules/notification/services/notification_service.py` — new `notify_new_contact_view`.
5. `backend/app/modules/provider/services/availability_service.py` — extracted the shared `_synthesize` helper;
   added `get_availability_for_provider`; `get_my_availability` behavior unchanged (covered by existing +3 new
   tests).
6. `backend/app/modules/provider/services/provider_service.py` — new `get_for_public_profile` (404 for
   missing/inactive; does **not** require `is_discoverable=True`, Decision 7).
7. **New file `backend/app/modules/provider/public_api.py`** — `GET /providers/{provider_id}`, registered in
   `backend/app/api/v1/api.py` **after** the existing `provider_router` registration.
8. `backend/app/modules/provider/schemas.py` — new `PublicProviderProfileResponse` (reuses the existing
   `WeekdayAvailabilityResponse`/`CategoryLabelResponse` shapes unchanged, per the Plan's own "no need to
   duplicate a schema that's already an exact match" note).
9. `backend/app/api/v1/api.py` — registered `contact_router` (`/contact-views`) and `provider_public_router`
   (`/providers`, after `provider_router`).

### Tests (all passing)

- `backend/tests/modules/contact/test_contact_service.py` (+ `_helpers.py`) — happy path, self-dealing rejection
  (row-count assertion, not just exception), unclaimed-listing contact (no rejection, no notification), claimed
  provider notification (exactly one row), `search_request_id` validation (own/mismatched/omitted/nonexistent),
  provider-not-found (missing/soft-deleted), defensive customer-profile-missing case.
- `backend/tests/modules/contact/test_contact_api.py` — 201 happy path, 403 self-dealing, 404 provider not
  found, 404 mismatched `search_request_id`, 401 unauthenticated, 403 wrong role.
- `backend/tests/modules/provider/test_public_provider_api.py` — business/freelancer happy paths (rating+count
  together, hours, subtype service-area fields, phone numbers absent), three badge-precedent fixtures, 404
  nonexistent/soft-deleted, Decision 7 non-discoverable-but-active regression, route-registration-order proof
  (`/me` still resolves to the owner-only router).
- `backend/tests/modules/provider/test_availability_service.py` — extended with `TestGetAvailabilityForProvider`
  (3 new tests, including a byte-for-byte parity check against `get_my_availability`).
- `backend/tests/modules/notification/test_notification_service.py` — extended with `TestNotifyNewContactView`
  (2 new tests).
- `backend/tests/conftest.py` — registers/creates/drops/truncates the `contact` schema and `ContactView` model
  alongside every other domain, mirroring the existing pattern exactly.
- `backend/tests/modules/category/test_category_migration.py` — **fixed a real regression this story's own
  `contact` module import surfaced**: that file's isolated migration-fixture builds `Base.metadata`'s table list
  by excluding certain schemas (`category`/`conversation`/`search`) by name; since `Base.metadata` is
  process-global, once anything in the test session imports `app.modules.contact.models`, `contact.contact_views`
  (which itself FKs into the already-excluded `search.search_requests`) was swept into that fixture's
  "create everything not excluded" table list and failed with `schema "contact" does not exist`. Fixed by adding
  `"contact"` to that fixture's own `_excluded_schemas` set, mirroring how `conversation`/`search` are already
  handled there. Confirmed via `git stash` that this file's own pre-existing isolated-run fragility (unrelated
  `NoReferencedTableError` when run outside the full suite) already existed before this story and is out of
  scope.

Full suite: **702 passed**, 0 failed, 0 errored. `ruff check .` and `ruff format --check .` both clean on every
file this story touched (two pre-existing, unrelated files elsewhere in the repo are already not
`ruff format`-clean; left untouched, out of scope).

## Explicitly deviated from the Plan (flag for `architect`/`tech-lead` at closeout)

- Added `CustomerProfileNotFoundError` (404), not named in the Plan's item 3 exception list. Needed because
  Decision 1 step 1 says the customer-profile lookup is "checked defensively" but the Plan's prose never names
  what to raise if it's ever `None`. Mirrors `apply_verification_outcome`'s identical defensive-404 precedent for
  a similarly-should-never-happen missing row.

## What's explicitly next

1. **frontend** — Plan's Frontend Proposed Changes items 1–12 (the new `provider_profile` feature, the Contact
   Reveal sheet, the shared `UnclaimedBanner`/`VerifiedBadge` widgets, wiring the two existing "coming soon" tap
   handlers). Not started. Backend's two new endpoints (`POST /contact-views`, `GET /providers/{provider_id}`)
   and response shapes are stable and ready to integrate against. **Do not implement the Call/WhatsApp launch
   behavior** until Open Question 1 (`url_launcher` dependency approval) is resolved — per the orchestrator's own
   instructions this session, it is already approved; flag to `frontend` directly rather than re-asking.
2. **tester** — verify all 8 verbatim ACs per the Plan's Verification Plan table, once frontend's screens exist
   (AC2/AC5/AC6 need the mobile UI; AC1/AC3/AC4/AC7/AC8 are already fully covered by this session's backend
   tests, but tester should still verify independently, not just trust this checkpoint).
3. **architect** — review Decision 1's guard, Decision 2's route-registration-order reasoning, Decision 4's
   ownership-validation posture, Decision 8's badge precedence, and the `contact` module's cross-module edge
   count, per the Plan's own Delegation section item 4.

## Open questions / blockers

None for backend. All three of the Plan's Open Questions were pre-resolved by the orchestrator before this
session started (see the task prompt): `url_launcher` approved, no `is_discoverable` requirement confirmed
(Decision 7 as built), 403 for self-dealing confirmed (Decision 10 as built).
