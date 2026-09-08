# Walkthrough S04 PRO-001

## Story: Create My Business or Freelancer Listing

**Sprint:** 04 | **Story ID:** PRO-001 | **Priority:** Critical | **Status:** Done

As a user who wants to offer a service, I want to choose whether I'm a Business or a Freelancer and enter my
core details, so that I can list my business or service on the platform for free.

This is the first story of Sprint 4 ("Provider Storefront") and the first story of a genuinely new domain
(`provider`) — no `backend/app/modules/provider/` or mobile `features/provider/` code existed before this
story. It builds the Provider aggregate root plus the first half of onboarding (`14_USER_FLOWS.md` Flow 2,
steps 1–5): immutable subtype selection and subtype-specific details. Portfolio/availability management
(PRO-002), the Verification gate (VER-001), and the Category domain are explicitly out of scope. Full context,
architecture decisions, and file-by-file scope: `docs/implementation/plans/Plan_S04_PRO-001.md`.

---

## What was implemented

### Backend (`backend/app/modules/provider/`, `backend/app/modules/identity/`)

- **New `provider` domain module**, following the established per-domain layout (`models.py` →
  `repositories/` → `services/` → `schemas.py` → `api.py` → `dependencies.py`): `Provider` (the aggregate
  root), `BusinessProfile`, and `FreelancerProfile` (all `CommonColumnsMixin`, schema `"provider"`), created via
  a reversible Alembic migration
  (`backend/alembic/versions/2026_09_08_1000-6133c77f062e_provider_domain.py`, down-revision `9f47869ca8bb`).
  Three new Postgres enums scoped to the `provider` schema as their first consumer — `provider_type`
  (business/freelancer), `listing_source` (self_registered/google_seeded_unclaimed), `verification_status`
  (pending/under_review/approved/rejected) — the last explicitly flagged in the migration for the future
  Verification-domain story to reuse via `create_type=False` rather than duplicating, mirroring CUS-001's
  `notification_channel` precedent. Deliberately does **not** create `provider_availability`, `portfolios`, or
  `service_areas` (PRO-002 scope). Upgrade and downgrade both verified against a real, disposable scratch
  Postgres database, with column/constraint/index layout confirmed via `\d` against `04_DATABASE.md`.
- **A new, flagged `providers.category_label VARCHAR(100) NOT NULL` column** — a genuine addition beyond
  `04_DATABASE.md`'s literal `providers` spec (Decision 4 of the Plan). The real Category domain
  (`categories`/`category_question_templates`/`provider_categories`) doesn't exist yet, so this free-text field
  is a deliberate, temporary stand-in capturing the user's typed category (e.g. "Plumbing") verbatim, with no
  taxonomy validation. Documented in `04_DATABASE.md` at story close (see below) with its expected future
  migration path once the Category domain ships.
- **Cross-module role grant, `provider → identity` (the reverse direction of ADR-014)**: a new
  `RoleAssignmentService` (`backend/app/modules/identity/services/role_assignment_service.py`), exposing one
  method, `ensure_role_assigned(user_id, role_name)` — idempotent (checks
  `RoleRepository.get_role_names_for_user` first), flush only, never commits. `ProviderService.create_provider`
  takes it as a constructor dependency and calls it after creating the `providers`/subtype-profile rows, all on
  the same request-scoped session — the endpoint's single `db.commit()` remains the only transaction boundary.
  Wired via a new `get_role_assignment_service()` in `identity/dependencies.py`, imported into
  `provider/dependencies.py`'s `get_provider_service()` — the identical shape ADR-014's
  `identity → customer`/`identity → audit` edges already use, just reversed. `AuthService`'s own inline
  role-assignment logic at registration is untouched. Recorded as **ADR-016** (see below).
- **`ProviderService.create_provider`**: rejects outright with `ProviderAlreadyExistsError` (409) if the caller
  already has a Provider — checked first, before any other work, regardless of the newly-requested
  `provider_type` (this proves both AC8's one-per-account rule and AC10's type-immutability test: a second call
  with a *different* type is rejected exactly like a second call with the *same* type, since there is no update
  path anywhere in this story that could ever change `provider_type` after creation). Generates a unique `slug`
  server-side (slugified `display_name` + a random hex suffix, bounded retry loop on collision — never a
  client-supplied field). Hardcodes `listing_source=self_registered`, `is_claimed=True`, `claimed_at=now()`,
  `verification_status=pending`, `is_discoverable=false` unconditionally (AC7/AC10) — no request field can
  influence either default. `country_code` is derived from whichever subtype's request payload the mobile
  client already reverse-geocoded, copied onto the `providers` row.
- **Endpoints — `GET`/`POST /api/v1/providers/me`**, both a `/me` singleton per ADR-015 (a Provider is
  inherently 1:1 with an Account), resolved exclusively from `CurrentUser.id`, gated by bare authentication only
  (deliberately not `require_role(customer)` — becoming a Provider isn't conceptually gated on already holding
  another role). `POST` returns `201` and accepts the entire wizard payload (type, basic info, and
  subtype-specific details) in one call — not incremental per-step `PATCH`es — since `providers.display_name`
  is `NOT NULL` and a partial pre-type-selection row would need either a draft-state design or nullable-then-
  backfilled columns, neither of which any AC requests. `GET /providers/me` returns 404
  (`ProviderNotFoundError`) if the caller has no listing yet, letting the mobile Profile & Settings CTA show a
  plain "you already have a listing" message instead of a raw 409 mid-wizard.
- **`CreateProviderRequest`** enforces exactly one of `business_details`/`freelancer_details` matching
  `provider_type` via a `model_validator(mode="after")` — rejected at the Pydantic layer (422) before reaching
  `ProviderService`.
- **New exceptions**: `ProviderAlreadyExistsError` (409, plain message — this is the caller's own resource, not
  a privacy-sensitive cross-account case) and `ProviderNotFoundError` (404, plain — same reasoning).
- **Tests**: `backend/tests/modules/provider/test_provider_service.py` (**11 tests**) and
  `test_provider_endpoints.py` (**12 tests**) — correct defaults for both Business and Freelancer paths
  (AC7/AC10), same-type and different-type second-creation-attempt both rejected (AC8/AC10 as two distinct
  cases), `ROLE_PROVIDER` present after creation and `ensure_role_assigned` idempotent, slug uniqueness across
  two providers sharing a display name, the `POST` happy path for both subtypes confirming `providers.user_id`
  equals the caller's own id with no `/auth/*` call anywhere in the test (AC2), `GET /providers/me` 404-then-200,
  unauthenticated → 401, and schema-level 422s for a mismatched/missing details object. New
  `backend/tests/modules/identity/test_role_assignment_service.py` (**5 tests**) covers granting a missing role,
  no-op on an already-held role, and granting `ROLE_PROVIDER` without disturbing an existing `ROLE_CUSTOMER`.
  **293 backend tests passing** (up from 265 at the end of CUS-002 — 265 + 11 + 12 + 5 = 293), 0 regressions.
  `ruff check`/`ruff format --check` both clean project-wide.

### Mobile (`mobile/lib/shared/widgets/`, `mobile/lib/features/provider/`)

- **New shared `StepIndicator` widget** (`mobile/lib/shared/widgets/step_indicator.dart`) — this codebase's
  first multi-step-form indicator (`currentStep`/`totalSteps`/optional `stepLabels`), zero domain coupling,
  satisfying AC9. Renders `totalSteps` equal-width segments, the first `currentStep` in the theme's primary
  color, with an accessible `Semantics` label.
- **New shared `LocationCaptureField` widget** (`mobile/lib/shared/widgets/location_picker/`) — factored out of
  `AddressFormScreen`'s (CUS-002) established "Pick on map" + "Use current location" pattern so the two new
  Provider detail screens don't duplicate that wiring a second/third time. A deliberate, flagged deviation from
  the Plan's literal item 29/30 text (which named only "Pick on map") — added for UX consistency with the
  existing Customer flow and to keep the screens testable without a real `GoogleMap` platform view, mirroring
  CUS-002's own reasoning.
- **New feature module `mobile/lib/features/provider/`**: domain models (`provider_type`, `provider`,
  `create_provider_request`, `provider_exception`), `ProviderRepository` (`getMyProvider()` returns `null` on
  404 rather than throwing, `createProvider()` against `POST /providers/me`), a Riverpod
  `ProviderOnboardingController` (`autoDispose` `StateNotifierProvider`) holding the in-memory wizard draft
  across all steps — no cross-session persistence, no server-side partial state (Decision 8 of the Plan: the
  sub-flow is a few short screens, well under the multi-day Verification process the UX guideline's
  resumability language is actually aimed at). Five new screens: `provider_intro_screen.dart` (S-15),
  `choose_provider_type_screen.dart` (S-16 — the *only* place `provider_type` is ever set client-side, AC3),
  `provider_basic_info_screen.dart` (S-17), `business_details_screen.dart` (S-18a), and
  `freelancer_details_screen.dart` (S-18b), plus `provider_error_copy.dart` (a specific, plain-language message
  for the "you already have a listing" 409 case).
- **Registration/Profile integration**: `profile_settings_screen.dart` (CUS-001) gained the "List Your
  Business" tile in the exact slot its own docstring had deferred — on tap, calls `getMyProvider()` first; a
  non-null result shows a plain "you already have a listing" snackbar, `null` navigates to the new
  `providerIntro` route. New routes registered in `app_routes.dart`/`app_router.dart`:
  `providerIntro`/`chooseProviderType`/`providerBasicInfo`/`businessDetails`/`freelancerDetails`.
- **~40 new l10n keys** added to both `app_en.arb` and `app_ar.arb`.
- **Tests**: `mobile/test/shared/widgets/step_indicator_test.dart`, and
  `mobile/test/features/provider/{choose_provider_type_screen,provider_basic_info_screen,business_details_screen,freelancer_details_screen,provider_onboarding_flow}_test.dart`
  plus a `fake_provider_repository.dart`/`test_helpers.dart` pair — asserting the step indicator renders
  correctly on every screen, only the minimal required fields per AC5/AC6 gate progress, type selection persists
  across navigation and is never re-askable (AC3), and the full Business/Freelancer wizard paths each submit
  exactly one `createProvider()` call with basic info and subtype details merged. **96 mobile tests passing**
  (up from 64 at the end of CUS-002), `flutter analyze` clean, `dart format --set-exit-if-changed` clean.
- One notable implementation detail: `providerOnboardingControllerProvider` is `autoDispose`, so
  `ChooseProviderTypeScreen`/`ProviderBasicInfoScreen` each keep a `ref.watch(...)` in `build()` purely to keep
  the provider alive across the navigation stack (they otherwise only `ref.read` it in event handlers) —
  without it the in-memory draft was being disposed and reset between wizard steps.

---

## Acceptance Criteria — Verification

All 10 acceptance criteria (from `Plan_S04_PRO-001.md`, sourced from the Tracker) were independently verified
by the `tester` agent — full suites re-run from a clean shell, migration reversibility re-derived against a
disposable scratch database, and both the same-type and different-type second-creation-attempt tests confirmed
as distinct cases by reading the actual service code.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `providers`/`business_profiles`/`freelancer_profiles` exist via migration; `providers.user_id` nullable at the column level, always non-null on rows this story's code path creates | Pass |
| 2 | An already-authenticated caller can start the wizard and the resulting Provider links to their existing Account — no new registration/OTP/OAuth step | Pass |
| 3 | Provider type is selected via a dedicated screen and immutable thereafter | Pass |
| 4 | Basic info (display name, phone, WhatsApp, category, description) captured before type-specific details | Pass |
| 5 | Business path captures address/map location, weekly operating hours, optional delivery radius, optional trade license number | Pass |
| 6 | Freelancer path captures base location, service radius, skill tags, years of experience | Pass |
| 7 | A newly created Provider defaults to `verification_status=pending`/`is_discoverable=false`, never appearing in customer-facing search | Pass |
| 8 | A user cannot create a second Provider on the same Account (service-layer enforced, explicitly tested) | Pass |
| 9 | Step indicator visible across the multi-step form; each step completable in under 30 seconds (no non-required field blocks progress) | Pass |
| 10 | Automated tests cover type immutability, one-provider-per-account, and correct defaulting of verification/discoverability flags | Pass |

---

## Architect Review — Findings and Resolution

The `architect` agent returned **APPROVED** — no must-fix items, no architectural-boundary violation.

1. **`provider → identity` cross-module direction (Decision 1, ADR-016)** — confirmed correct against ADR-014's
   precedent and `02_ARCHITECTURE.md`'s "modules communicate through services only" rule: `RoleAssignmentService`
   has zero imports from `provider`, `ProviderService` never touches `RoleRepository`/`UserRole` directly, and
   the flush-only/same-session/single-commit claim holds up on direct code read. A second, independent
   one-directional edge — no cycle with the existing `identity → customer`/`identity → audit` edges.
2. **`category_label` flagged schema addition (Decision 4)** — confirmed sound as a deliberate, temporary,
   plain-typed stand-in (consistent with this codebase's convention of a typed column over a JSONB catch-all for
   a genuinely known, single-purpose field), not a preview of the real Category domain.
3. **Single-`POST`-at-end-of-wizard endpoint shape (Decision 2, ADR-015)** — confirmed the correct choice per
   ADR-015's 1:1-resource rule; the rejected incremental-`PATCH` alternative would have needed either a draft
   table or nullable-then-backfilled columns, neither requested by any AC.
4. **New `StepIndicator` shared widget** — confirmed genuinely reusable, zero domain coupling, a sound first
   instance of this codebase's multi-step-form pattern.
5. **`LocationCaptureField` extraction / "Use current location" addition** (flagged by `frontend` as a deviation
   from the Plan's literal S-18a/b bullets) — confirmed as a reasonable, low-risk UX-consistency choice matching
   `AddressFormScreen`'s existing pattern, not scope creep.

### Non-blocking polish notes (3)

1. `ProviderService.create_provider`'s `country_code` derivation carries a `# type: ignore[union-attr]` on the
   freelancer branch — the schema's own `model_validator` structurally guarantees exactly one of
   `business_details`/`freelancer_details` is present, but the type checker can't see that invariant. Cosmetic;
   no runtime risk. A small typed helper/overload could remove the suppression in a future pass.
2. The `LocationCaptureField`/"Use current location" addition should be reflected back into
   `Plan_S04_PRO-001.md`'s item 29/30 text at some point so the Plan and the shipped screens don't silently
   diverge for a future reader — not urgent, since this Walkthrough now records the deviation and its rationale.
3. `mypy` still not installed as a runnable dev-tool (`uv run mypy app` cannot spawn) — carried forward from
   every prior story since AUTH-003.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-016**, the `provider → identity` cross-module role-grant
  direction (the reverse edge of ADR-014's `identity → customer`/`identity → audit`).
- **`docs/AI/04_DATABASE.md`** — `providers` table spec now documents `category_label VARCHAR(100) NOT NULL` as
  a flagged, temporary stand-in for the not-yet-built Category domain, with the expected future migration path.
- **`docs/AI/12_TECH_STACK.md`** — backfilled `google_maps_flutter`/`geolocator`/`geocoding` into the Approved
  Flutter Packages list; these were actually added in CUS-002 but never documented there, a pre-existing gap
  this story (the first to newly *reuse* them) closes.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 4 section added, PRO-001 marked done; Executive
  Summary, Current Backend Capabilities, Repository State, Current Limitations, Overall Progress, and Next
  Planned Story sections updated.
- `docs/CHANGELOG.md` — new entry under `[Unreleased]`.

---

## Testing Performed

- `cd backend && uv run pytest -q` — **293/293 passing** (265 at the end of CUS-002 + 11 + 12 + 5 new), 0
  regressions.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` —
  verified against a disposable scratch database (never the shared dev/test DB); columns/constraints/indexes
  confirmed via `psql \d` to match `04_DATABASE.md` plus the flagged `category_label` addition.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — clean.
- `cd mobile && flutter test` — **96/96 passing** (64 at the end of CUS-002 + 32 new).
- `cd mobile && flutter analyze` — no issues found.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test` — clean.
- `tester` agent: all 10 ACs independently verified with direct evidence — see table above.
- `architect` agent: APPROVED, no must-fix items — see findings above.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_08_1000-6133c77f062e_provider_domain.py` (new)
- `backend/app/modules/provider/models.py` — `Provider`, `BusinessProfile`, `FreelancerProfile`
- `backend/app/modules/provider/repositories/{provider_repository,business_profile_repository,freelancer_profile_repository}.py` (new)
- `backend/app/modules/provider/services/provider_service.py` (new)
- `backend/app/modules/provider/schemas.py` — `CreateProviderRequest`/`CreateBusinessDetailsRequest`/`CreateFreelancerDetailsRequest`/`ProviderResponse`/`BusinessProfileResponse`/`FreelancerProfileResponse`
- `backend/app/modules/provider/api.py` — `GET`/`POST /providers/me`
- `backend/app/modules/provider/dependencies.py` (new)
- `backend/app/modules/identity/services/role_assignment_service.py` (new) — `RoleAssignmentService.ensure_role_assigned`
- `backend/app/modules/identity/dependencies.py` — added `get_role_assignment_service()`
- `backend/app/core/exceptions/{exceptions.py,__init__.py}` — `ProviderAlreadyExistsError`, `ProviderNotFoundError`
- `backend/app/api/v1/api.py` — registers `provider_router` at `/providers`
- `backend/tests/modules/provider/{test_provider_service.py,test_provider_endpoints.py}` (new)
- `backend/tests/modules/identity/test_role_assignment_service.py` (new)
- `backend/tests/conftest.py`, `backend/alembic/env.py` — import/register `app.modules.provider.models`

### Mobile
- `mobile/lib/shared/widgets/step_indicator.dart` (new)
- `mobile/lib/shared/widgets/location_picker/location_capture_field.dart` (new)
- `mobile/lib/features/provider/domain/models/{provider_type,provider,create_provider_request,provider_exception}.dart` (new)
- `mobile/lib/features/provider/data/provider_repository.dart` (new)
- `mobile/lib/features/provider/state/provider_onboarding_controller.dart` (new)
- `mobile/lib/features/provider/presentation/screens/{provider_intro,choose_provider_type,provider_basic_info,business_details,freelancer_details}_screen.dart` (new)
- `mobile/lib/features/provider/presentation/utils/provider_error_copy.dart` (new)
- `mobile/lib/features/customer/presentation/screens/profile_settings_screen.dart` — added the "List Your Business" tile
- `mobile/lib/core/routing/{app_routes.dart,app_router.dart}` — `providerIntro`/`chooseProviderType`/`providerBasicInfo`/`businessDetails`/`freelancerDetails`
- `mobile/lib/l10n/{app_en.arb,app_ar.arb}`
- `mobile/test/shared/widgets/step_indicator_test.dart` (new)
- `mobile/test/features/provider/{choose_provider_type_screen,provider_basic_info_screen,business_details_screen,freelancer_details_screen,provider_onboarding_flow}_test.dart` (new)
- `mobile/test/features/provider/{fakes/fake_provider_repository.dart,test_helpers.dart}` (new)

---

## Follow-up Notes for Sprint Planning

- **Sprint 4 (Provider Storefront) is underway** — 1 story done: PRO-001. **PRO-002 ("Manage my provider
  storefront")**, which depends on PRO-001, is now unblocked and ready for planning.
- Non-blocking follow-ups carried forward: the `# type: ignore[union-attr]` mypy suppression in
  `ProviderService.create_provider` (`backend`), reflecting the `LocationCaptureField`/"Use current location"
  addition back into the Plan's literal screen bullets, and `mypy` still not installed (carried forward from
  every prior story since AUTH-003).
- The Category domain (`categories`/`category_question_templates`/`provider_categories`) remains an open
  decision (`13_OPEN_DECISIONS.md` item 1) — `providers.category_label` is a temporary stand-in only; a future
  story is expected to reconcile it with the real taxonomy once that domain ships.
