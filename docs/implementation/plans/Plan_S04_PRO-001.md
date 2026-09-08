# Plan for Story PRO-001 — Create My Business or Freelancer Listing

**Sprint:** 04 (Provider Storefront) | **Epic:** ML4-EP01 | **Priority:** Critical | **Depends On:** AUTH-004, CUS-002 (both complete, merged to `main`)

---

## Story

As a user who wants to offer a service, I want to choose whether I'm a Business or a Freelancer and enter my core details, so that I can list my business or service on the platform for free.

This is the first story of Sprint 4 and the first story of a genuinely new domain (`provider`) — no `backend/app/modules/provider/` or mobile `features/provider/` code exists yet. It builds the Provider aggregate root plus the first half of the onboarding flow (`14_USER_FLOWS.md` Flow 2, steps 1–5): type selection (immutable — a Provider is exactly one subtype, never both) and subtype-specific details. It deliberately reuses the caller's existing Account (from AUTH-001/002) rather than creating a new one — the "no re-registration" rule from Flow 2 step 1 and the dual-role model in `03_DOMAIN_MODEL.md`.

**Scope boundary:** does **not** include portfolio/availability management (`portfolios`, `provider_availability`, `service_areas` — PRO-002) or the Verification gate (`verification_records`, document upload, OCR — VER-001, Flow 2 steps 6–8). A Provider created by this story is not yet discoverable to customers — `is_discoverable` stays `false` until VER-001 ships and approves it. Does not include the Category domain/taxonomy (still an open decision, `13_OPEN_DECISIONS.md` item 1) — see Decision 4 for how AC4's "category" field is handled instead. Does not include the Provider Dashboard, Storefront/Edit Profile screen (S-25), Claim-Your-Listing flow (Flow 3), or any Google-seeded-unclaimed-listing behavior — `providers.user_id` is built nullable to support that later story, but every row this story creates always has a non-null `user_id`.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`)

1. `providers`, `business_profiles`, and `freelancer_profiles` tables exist via migration; `providers.user_id` is nullable (to support Google-seeded unclaimed listings in a later story) but non-null for self-registered providers created here.
2. A user with an existing Account can start "List Your Business" and the resulting Provider is linked to that same Account — no new registration/OTP/OAuth step is triggered.
3. Provider type (Business or Freelancer) is selected via a dedicated screen and cannot be changed after this step completes.
4. Basic info (display name, phone, WhatsApp, category, description) is captured before type-specific details.
5. Business path captures address/map location, weekly operating hours, optional delivery radius, and optional trade license number.
6. Freelancer path captures base location, service radius, skill tags, and years of experience.
7. A newly created Provider defaults to `verification_status=pending` and `is_discoverable=false` — it must not appear in any customer-facing search or directory result.
8. A user cannot create a second Provider on the same Account (one Provider per Account, enforced at the service layer, tested explicitly).
9. Step indicator is visible across the multi-step form; each step is independently completable in under 30 seconds per the UX guideline.
10. Automated tests cover: type immutability, one-provider-per-account enforcement, and correct defaulting of verification/discoverability flags.

---

## Verified Current State (read directly from code, not assumed)

- `docs/AI/04_DATABASE.md` already fully specifies `provider.providers`, `provider.business_profiles`, and `provider.freelancer_profiles` column-by-column, plus the `provider_type`, `listing_source`, and `verification_status` enums — nothing to design at the column level except one genuine, flagged addition (Decision 4). `providers` has no `category` column at all — the Category domain (`category.categories`/`category.category_question_templates`, `provider_categories` join table) does not exist yet, confirmed by `docs/AI/13_OPEN_DECISIONS.md` item 1 and `PROJECT_IMPLEMENTATION_STATE.md` Section 15 ("Category taxonomy... blocks the AI intake work").
- `docs/AI/14_USER_FLOWS.md` Flow 2 steps 1–5 map exactly to this story's scope: authenticate/reuse existing Account (step 1) → choose subtype, immutable (step 2) → shared basic info incl. category (step 3, writes `provider_categories` per the flow doc — not buildable yet, see Decision 4) → subtype-specific details (step 4) → `providers` row created with `listing_source=self_registered`, `is_claimed=true`, `verification_status=pending`, `is_discoverable=false` (step 5). Steps 6–10 (verification documents, admin review, portfolio/availability) are explicitly out of scope.
- `docs/AI/15_SCREEN_INVENTORY.md` names every screen this story builds: **S-15** (List Your Business intro), **S-16** (Choose Provider Type), **S-17** (Basic Info), **S-18a** (Business Details), **S-18b** (Freelancer Details). S-19 (Verification Upload) onward is out of scope. `16_UX_GUIDELINES.md`'s Form & Input UX section is the direct source of AC9's wording: "long onboarding... is broken into short steps with a visible step indicator... each step should feel completable in under 30 seconds."
- `backend/app/modules/customer/` (CUS-001/CUS-002) is the concrete module-layout template to follow: `models.py` → `repositories/*.py` (`BaseRepository[T]` subclasses) → `services/*.py` → `schemas.py` → `api.py` → `dependencies.py`, one Alembic migration per domain (per `04_DATABASE.md`'s Migration Strategy section), `CommonColumnsMixin` on every business table, native Postgres enums colocated in the schema of their first consumer (`_pg_enum`/`_notification_channel_enum`-style helper functions).
- `backend/app/core/authorization.py`'s `ensure_owner_or_not_found` and `backend/app/api/dependencies.py`'s `require_role`/`CurrentUser` (AUTH-004) are directly reusable, unchanged.
- **No existing mechanism grants a role to an already-registered Account from outside `identity`.** `AuthService.verify_otp_and_authenticate`/`authenticate_with_oauth` (AUTH-001/002) assign `ROLE_CUSTOMER` inline, directly against `RoleRepository`/`UserRole`, only at first registration — there is no reusable, importable "assign this role to this user" service method anywhere today. This story is the first to need one from a *different* module (`provider` needs to grant `ROLE_PROVIDER` to an account that is authenticating, not registering) — see Decision 1.
- `backend/app/modules/identity/repositories/role_repository.py`'s `get_role_names_for_user(user_id)` is already re-read by `SessionService.refresh` on every token refresh (confirmed by reading `session_service.py`), so a role granted after a JWT was issued is picked up automatically on the caller's next refresh — no new token-refresh mechanism is needed for the newly-granted `provider` role to eventually appear in `CurrentUser.roles`. This story builds no `require_role(ROLE_PROVIDER)`-gated endpoint itself (that starts with PRO-002/S-25), so this is a forward-compatibility note, not a blocker.
- `backend/app/repositories/base_repository.py`'s generic `update()` will happily overwrite any column, including `provider_type`, if ever called with it — there is no DB-level trigger preventing a type change. Confirms immutability in this story must come from **never exposing a code path that can call it with `provider_type`** (no update endpoint of any kind exists in this story) plus the one-provider-per-account check rejecting any second creation attempt outright (Decision 3) — not a DB constraint on the column itself.
- `docs/AI/12_TECH_STACK.md`'s "Approved Flutter Packages" list still does not include `google_maps_flutter`/`geolocator`/`geocoding` even though CUS-002 shipped code using all three (confirmed: `mobile/pubspec.yaml` already has them; `12_TECH_STACK.md` was never updated). This is a pre-existing documentation gap from CUS-002, not something this story introduces — flagged for `tech-lead` to close alongside this story's own doc updates, since this story is the first to actually *reuse* those packages via the existing `LocationPickerScreen` and will otherwise compound the same gap.
- `mobile/lib/shared/widgets/location_picker/location_picker_screen.dart` and `location_pick_result.dart` (`LocationPickResult { latitude, longitude, addressLine?, city?, region?, countryCode? }`) were built generic and Customer-domain-free specifically so a future Provider screen could reuse them without adaptation (`Plan_S03_CUS-002.md` Decision 7's own stated forward-compatibility note) — confirmed by reading the file directly, zero Customer imports. This story is that reuse.
- `mobile/lib/features/customer/presentation/screens/profile_settings_screen.dart` (CUS-001) has a docstring explicitly stating it deliberately does **not** add a "List Your Business" entry, naming it as a slot for "their own not-yet-built stories" — this story is that story; Profile & Settings gains the CTA now (see Mobile Proposed Changes).
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (CUS-002) already establishes the "small, explicitly-temporary stub button, fully commented as such" pattern (`_onFindService`) for wiring a not-yet-built feature's *gate logic* without building the feature itself — not directly reused here (this story's CTA lives on Profile & Settings, not Home), but confirms the precedent this Plan's Decision 9 follows for keeping `GET /providers/me`'s mobile integration minimal.
- `backend/tests/conftest.py`'s `db_engine` fixture (ADR-013) imports each domain's `models` module explicitly (`import app.modules.customer.models`, `import app.modules.audit.models`, `import app.modules.identity.models`) before `Base.metadata.create_all` — this story adds `import app.modules.provider.models` alongside them, following the exact established pattern, not inventing a new one.
- `backend/app/api/v1/api.py` registers each module's router with `v1_router.include_router(<module>_router, prefix="/<resource>")` — this story adds `v1_router.include_router(provider_router, prefix="/providers")` the same way.

---

## Architecture Decisions

### Decision 1 — Cross-module role-grant trigger: `provider → identity` (the reverse direction of ADR-014)

**Chosen:** a small, new, single-purpose `RoleAssignmentService` lives in `identity` (`backend/app/modules/identity/services/role_assignment_service.py`), exposing exactly one method: `async def ensure_role_assigned(self, user_id: uuid.UUID, role_name: str) -> None` — idempotent (checks `RoleRepository.get_role_names_for_user(user_id)` first; only inserts a new `UserRole` row if the role is not already present), flush only, never commits. `provider`'s `ProviderService` takes this as a constructor dependency (`role_assignment_service: RoleAssignmentService`) and calls `await self.role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)` inside `create_provider`, on the same request-scoped `AsyncSession`, so the `providers` row and the new `user_roles` row either both land or neither does (the endpoint's single, pre-existing `db.commit()` remains the only transaction boundary). Wired via `identity/dependencies.py`'s new `get_role_assignment_service()`, imported into `provider/dependencies.py` exactly the way `customer/dependencies.py`'s `get_customer_service` is imported into `identity/dependencies.py` today — same shape, reversed direction.

**Why this direction, and why it doesn't create a cycle:** ADR-014 established `identity → customer` and `identity → audit` — `identity`'s own registration flow triggering another module's provisioning logic. This story is the mirror image: a *different* module (`provider`) needs to modify `identity`'s own data (`user_roles`) for an *already-authenticated* caller, not at registration time. `RoleAssignmentService` has zero imports from `provider` (it only touches `identity.models`/`identity.repositories`), so this is a second, independent one-directional edge (`provider → identity`) — it does not create a cycle with the existing `identity → customer`/`identity → audit` edges, since those involve entirely different files and different service classes. This does **not** modify `AuthService` at all — `AuthService`'s own inline role-assignment logic during registration is untouched; `RoleAssignmentService` is a new, narrower, reusable capability `AuthService` could later be refactored to call too, but that refactor is not part of this story (avoiding unrelated changes to an already-shipped, tested module).

**Alternatives considered and rejected:**
- **`ProviderService` importing `RoleRepository`/`UserRole` directly** (rejected — this is exactly the "Module → Another Module's Repository" pattern `02_ARCHITECTURE.md` explicitly prohibits; modules communicate through services only).
- **`provider` depending on the full `AuthService`** (rejected — `AuthService` orchestrates OTP verification, OAuth claims, and session/device issuance; pulling all of that into `provider`'s dependency graph for one idempotent role-grant call is a far heavier coupling than needed, and violates "small, focused services").
- **A domain event (`ProviderRegistered`) via an in-process event bus** (rejected for the same reason ADR-014 rejected it for `CustomerRegistered`: no event-bus infrastructure exists anywhere in this codebase; building one for a single call site is premature abstraction).

This should be recorded as an ADR (next available: **ADR-016**, since ADR-015 is already in use) once the user signs off on the story, per the tech-lead's standing responsibility.

**Token-refresh consequence (not a gap, but worth stating explicitly):** the caller's *current* JWT was issued before `ROLE_PROVIDER` existed on their account, so `CurrentUser.roles` won't reflect it until their next token refresh (`SessionService.refresh` already re-reads `get_role_names_for_user` on every refresh, per Verified Current State above — no new mechanism needed). This story builds no `require_role(ROLE_PROVIDER)`-gated endpoint, so nothing in this story is blocked by this; it's simply the expected, already-supported behavior a future story (PRO-002/S-25) will rely on.

### Decision 2 — Endpoint shape: `/providers/me`, a singleton per ADR-015, one `POST` submitted once at the end of the wizard

`GET /api/v1/providers/me` and `POST /api/v1/providers/me` — both resolve/act on the caller's own Provider exclusively from `CurrentUser.id`, never a client-supplied `{id}`. Per ADR-015's rule, this is the correct shape because a Provider is inherently 1:1 with an Account (AC8: "a user cannot create a second Provider on the same Account") — there is no route shape through which a caller could even attempt to address a different Provider. No `ensure_owner_or_not_found` call is needed or appropriate here, mirroring `/customers/me` exactly rather than the `/customers/me/addresses/{id}` collection shape.

**Single `POST`, not incremental per-step `PATCH`es:** the mobile wizard (S-16 → S-17 → S-18a/b) collects every field in-memory across screens and submits exactly one `POST /providers/me` call at the end, containing the type, basic info, and subtype-specific details together. Rejected alternative: create a partial `providers` row after S-16 (type only) and `PATCH` it after each subsequent step. This was rejected because `providers.display_name` is `NOT NULL` (per `04_DATABASE.md`) — a row created after type-selection alone cannot satisfy the schema's own constraints, forcing either a "draft" table/state design (a real, unrequested feature — no AC asks for cross-session draft persistence) or nullable-then-backfilled columns (weakening the schema for every other consumer). A single end-of-wizard `POST` needs neither, keeps the API surface minimal (one endpoint, not four), and is the same shape CUS-002's own `AddressFormScreen` already uses for a single (simpler) form.

### Decision 3 — One-Provider-per-Account and type immutability: service-layer check first, DB partial unique index as backstop; no update path for `provider_type` exists anywhere in this story

**Primary mechanism:** `ProviderService.create_provider` calls `ProviderRepository.get_by_user_id(user_id)` before doing anything else; if a row already exists (regardless of its `provider_type`), it raises a new `ProviderAlreadyExistsError` (409 Conflict — this is the caller's own resource being duplicated, not a privacy-sensitive cross-account lookup, so a plain 409 is appropriate and reveals nothing that isn't already true of the caller's own account, unlike `SavedAddressNotFoundError`'s deliberately non-revealing 404 for a *different* owner's data).

**Defense-in-depth:** `04_DATABASE.md` already specifies `uq_providers_user_id` (partial unique index, `WHERE user_id IS NOT NULL`) — included as-is in the migration, mirroring CUS-002 Decision 2's transactional-primary/index-secondary pattern exactly.

**Type immutability is structural, not a separate mechanism:** this story builds no `PATCH`/`PUT` endpoint for `providers` at all (editing belongs to the future Storefront screen, S-25, a separate story) — there is therefore no code path in this story's surface that could ever change `provider_type` after creation. AC10's "type immutability" test proves this concretely by attempting a **second** `create_provider` call for the same account with a **different** `provider_type` than the first (e.g. Business, then Freelancer) and asserting it is rejected by the same one-provider-per-account check — proving a caller cannot "switch" subtype via a second creation attempt, not merely that duplicates of the same type are blocked. A separate test proves the same-type duplicate case (AC8). Together these are the two distinct "automated tests" AC10 asks for, plus a third for defaulting (Decision 5).

### Decision 4 — Category field: a flagged, temporary free-text column on `providers`, not a `provider_categories` relationship

The Category domain (`category.categories`, `category.category_question_templates`, `provider_categories` join table) does not exist — confirmed in Verified Current State. AC4 nonetheless requires capturing "category" as part of basic info, before type-specific details.

**Decision:** add `providers.category_label VARCHAR(100) NOT NULL` — a genuine, flagged addition beyond `04_DATABASE.md`'s literal `providers` table spec (mirroring CUS-002 Decision 2's precedent of flagging a beyond-doc schema addition explicitly rather than silently improvising). It stores the user's free-text category entry (e.g. "Plumbing," "AC Repair") exactly as typed, with no validation against a taxonomy that doesn't exist yet. When the Category domain ships (`13_OPEN_DECISIONS.md` item 1), a follow-up story is expected to: (a) build `categories`/`provider_categories`, (b) either migrate `category_label` values into real `Category` rows (fuzzy-matched or admin-reconciled) and populate `provider_categories`, or retain `category_label` as a free-text fallback/search-boost field alongside the real relationship — that migration design is explicitly deferred, not decided here.

**Alternatives considered and rejected:**
- **Silently drop the field / capture it in the UI but never persist it** — rejected: violates AC4's plain reading ("captured... before type-specific details" implies it is saved, not merely displayed and discarded); would also misrepresent to the user that their input was recorded.
- **A generic JSONB `metadata` catch-all column** — rejected: this codebase's convention for a genuinely known, single-purpose string field is a plain typed column (see `business_profiles.trade_license_number`, `freelancer_profiles.skills` as a typed `TEXT[]`, not a JSON blob); a JSONB catch-all would be weaker typing for no benefit here.

**Follow-up required at story close (flagged for `tech-lead`, not `backend`):** `04_DATABASE.md`'s `providers` table section needs a documentation update noting this column and its documented temporary nature, mirroring the CUS-002 partial-index precedent.

### Decision 5 — Defaulting: `verification_status=pending`, `is_discoverable=false`, unconditionally, regardless of subtype

Both fields are set exactly once, at creation, inside `ProviderService.create_provider`, never derived from any request input (no `CreateProviderRequest` field can influence either) — this satisfies AC7 by construction rather than by validation. The dedicated third AC10 test asserts both flags on a freshly created row for **both** the Business and Freelancer paths (two assertions, since a subtle bug could set the right default for one subtype and the wrong one for the other).

### Decision 6 — `slug` and `country_code`: server-generated, never client-supplied

- **`slug`** (`VARCHAR(220)`, unique, "used in shareable profile deep links" per `04_DATABASE.md`) is not in AC4's field list and shareable deep links are an MVP Stage 5 feature (`11_MVP_SCOPE.md`), not this story's. `ProviderService` generates it server-side: a slugified `display_name` plus a short random suffix, with a small bounded retry loop on a uniqueness collision (mirrors no existing precedent exactly, but is the simplest correct approach for a field no AC asks the user to control). Not exposed as a request field; included in the response for the future deep-link story to consume already.
- **`country_code`** (`CHAR(2)` `NOT NULL` on `providers`) is derived from whichever subtype location the mobile client already reverse-geocodes via the reused `LocationPickerScreen`/`LocationPickResult.countryCode` (exactly CUS-002's established pattern for `saved_addresses.country_code` — no new backend geocoding capability is introduced, consistent with CUS-002's own "Explicitly Out of Scope" item on this point). It travels as a plain request field inside `business_details`/`freelancer_details` (see Backend schemas below) and `ProviderService` copies it up onto the `providers` row itself — `freelancer_profiles` does not persist its own `country_code` column (not in `04_DATABASE.md`'s spec for that table), it only flows through the request to populate `providers.country_code`.

### Decision 7 — Reuse `LocationPickerScreen` unmodified for both Business address and Freelancer base-location capture

Per the explicit task instruction and the Verified Current State confirmation that `LocationPickerScreen`/`LocationPickResult` are already generic and Customer-domain-free, S-18a's "address/map pin" and S-18b's "base location/map pin" both launch the existing shared widget with no changes to it. Zero new mobile dependencies are introduced by this story — `google_maps_flutter`/`geolocator`/`geocoding` are already in `pubspec.yaml` from CUS-002.

### Decision 8 — Mobile wizard state: one in-memory Riverpod draft, no cross-session persistence, no server-side partial state

A single `ProviderOnboardingController` (Riverpod, feature-scoped to `features/provider/`) holds a mutable draft object across S-16 → S-17 → S-18a/b. Each screen reads/writes into it via the controller; navigation between steps carries no `extra` payload (state lives in the provider, not route params). Only the final step's "Submit" action calls the repository, which issues the single `POST /providers/me` (Decision 2).

**No cross-app-restart resumability in this story** — flagged explicitly against `16_UX_GUIDELINES.md`'s "Provider onboarding... should let a user stop and resume later without losing progress; verification is a multi-step, sometimes multi-day process." That guidance is aimed at the *overall* onboarding process, whose genuinely multi-day step is Verification (VER-001, not built here) — this story's sub-flow is three to four short screens completable in well under a minute end-to-end. Building cross-restart persistence for a sub-minute in-memory flow is unrequested scope; if a future usability finding shows users frequently abandon mid-wizard, that's a follow-up enhancement to raise then, not a blocker for this story. `architect` should weigh in on whether this reasoning holds.

### Decision 9 — A minimal `GET /providers/me` (404 if none), to support graceful "already have a listing" UX and the Profile & Settings CTA

Not explicitly named by any AC, but needed for AC8's duplicate-prevention to feel intentional rather than a raw error: without it, a caller who already has a Provider would only discover that by getting a 409 from `POST /providers/me` mid-wizard, after re-entering everything. `GET /providers/me` returns the caller's existing Provider (200) or a new `ProviderNotFoundError` (404, plain — not privacy-sensitive, it's the caller's own account) if none exists yet. The Profile & Settings "List Your Business" CTA checks this first: if a Provider already exists, show a plain "You already have a business listing" message (no Storefront/Dashboard screen exists yet — S-23/S-25 are separate, future stories) instead of entering the wizard; otherwise, navigate to S-15. This mirrors ADR-015's `/me` singleton shape and keeps the endpoint's response payload intentionally minimal (the same `ProviderResponse` `POST` returns — no dashboard/analytics data).

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration, `provider_domain` (down-revision = current head — confirm via `alembic heads` at implementation time; last known head is `9f47869ca8bb`, the CUS-002 `saved_addresses` migration). Creates the `provider` Postgres schema, three enums scoped to `provider` (`provider_type`: `business`/`freelancer`; `listing_source`: `self_registered`/`google_seeded_unclaimed`; `verification_status`: `pending`/`under_review`/`approved`/`rejected` — colocated here as its first consumer, flagged in a code comment for the future Verification-domain story to reuse via `create_type=False, schema="provider"` rather than duplicating, mirroring CUS-001 Decision 2's `notification_channel` precedent), and three tables:
   - `providers` — every column from `04_DATABASE.md`'s spec (`user_id` nullable, `provider_type`, `display_name`, `slug`, `description`, `phone_country_code`, `phone_number`, `whatsapp_number`, `listing_source`, `is_claimed`, `claimed_at`, `google_place_id`, `verification_status`, `is_discoverable`, `average_rating`, `review_count`, `country_code`) **plus** `category_label VARCHAR(100) NOT NULL` (Decision 4). Constraints: `uq_providers_slug`, `uq_providers_user_id` (partial), `uq_providers_google_place_id` (partial), `chk_providers_claimed_has_owner`. Indexes: `idx_providers_provider_type`, `idx_providers_is_discoverable`, `idx_providers_verification_status`, `idx_providers_country_code`.
   - `business_profiles` — exactly per spec (`provider_id` unique FK, `trade_license_number`, `address_line`, `city`, `region`, `latitude`, `longitude`, `operating_hours` JSONB, `delivery_radius_meters`).
   - `freelancer_profiles` — exactly per spec (`provider_id` unique FK, `base_latitude`, `base_longitude`, `service_radius_meters`, `skills` TEXT[], `years_experience`).
   - Does **not** create `provider_availability`, `portfolios`, or `service_areas` — PRO-002 scope, explicitly excluded per the task brief.
2. Verify upgrade and downgrade both work cleanly against a disposable scratch database (per ADR-013's continued distinction between the test suite's own `metadata.create_all` and a real Alembic-migrated database).

### Models (`backend/app/modules/provider/models.py`)
3. `ProviderType(StrEnum)`, `ListingSource(StrEnum)`, `VerificationStatus(StrEnum)` plus a `_pg_enum`-style helper mirroring `identity/models.py`'s pattern. `Provider(CommonColumnsMixin, Base)`, `BusinessProfile(CommonColumnsMixin, Base)`, `FreelancerProfile(CommonColumnsMixin, Base)`, schema `"provider"`.

### Repositories (`backend/app/modules/provider/repositories/`)
4. `provider_repository.py`: `ProviderRepository(BaseRepository[Provider])` with `get_by_user_id(user_id) -> Provider | None` (the AC8/Decision 3 existence check; also backs `GET /providers/me`), `get_by_id_with_details(provider_id)` if needed for eager-loading the subtype profile in the response.
5. `business_profile_repository.py`: `BusinessProfileRepository(BaseRepository[BusinessProfile])`.
6. `freelancer_profile_repository.py`: `FreelancerProfileRepository(BaseRepository[FreelancerProfile])`.

### Service (`backend/app/modules/provider/services/provider_service.py`)
7. `ProviderService(provider_repository, business_profile_repository, freelancer_profile_repository, role_assignment_service)` with:
   - `get_my_provider(user_id) -> Provider | None` — thin wrapper over `get_by_user_id` (no get-or-create here, unlike `CustomerService` — a missing Provider is a legitimate, expected state, not a backfill case).
   - `create_provider(user_id, *, payload: CreateProviderRequest) -> Provider` — (a) raises `ProviderAlreadyExistsError` if `get_by_user_id` returns non-null (Decision 3); (b) generates a unique `slug` (Decision 6); (c) creates the `providers` row with `listing_source=self_registered`, `is_claimed=True`, `claimed_at=now()`, `verification_status=pending`, `is_discoverable=False`, `country_code` derived from the subtype payload (Decision 6); (d) creates the matching `business_profiles` or `freelancer_profiles` row; (e) calls `role_assignment_service.ensure_role_assigned(user_id, ROLE_PROVIDER)` (Decision 1); all on the same session, flush only — the endpoint's single `db.commit()` remains the only transaction boundary, so a partial write (e.g. `providers` row without its subtype profile) can never be committed.
   - Private `_generate_unique_slug(display_name) -> str`.

### Identity module additions (new capability, no edits to existing `AuthService` code)
8. `backend/app/modules/identity/services/role_assignment_service.py`: `RoleAssignmentService(role_repository)` with `ensure_role_assigned(user_id, role_name) -> None` (Decision 1).
9. `backend/app/modules/identity/dependencies.py`: add `get_role_assignment_service()`, mirroring `get_customer_service`'s existing shape exactly (no changes to any existing function in this file).

### Schemas (`backend/app/modules/provider/schemas.py`)
10. `CreateBusinessDetailsRequest { address_line (required), city?, region?, country_code (required, 2-letter, same pattern as `CreateSavedAddressRequest`), latitude (required, -90..90), longitude (required, -180..180), operating_hours?: dict[str, {"open": "HH:MM", "close": "HH:MM"} | None] keyed by lowercase weekday name, delivery_radius_meters? (int, >0), trade_license_number? (max 100) }`.
11. `CreateFreelancerDetailsRequest { base_latitude (required), base_longitude (required), country_code (required, same pattern — flows to `providers.country_code` only, not persisted on `freelancer_profiles`), service_radius_meters (required, int, >0), skills?: list[str], years_experience?: int (>=0) }`.
12. `CreateProviderRequest { provider_type (required), display_name (required, max 200), phone_country_code (required), phone_number (required), whatsapp_number? , category_label (required, max 100), description? (max lengths per `04_DATABASE.md`), business_details: CreateBusinessDetailsRequest | None = None, freelancer_details: CreateFreelancerDetailsRequest | None = None }` with a `model_validator(mode="after")` enforcing exactly one of `business_details`/`freelancer_details` is present and matches `provider_type` — rejected at the Pydantic layer (422) before ever reaching `ProviderService`, per `05_API_GUIDELINES.md`'s four-layer validation model.
13. `BusinessProfileResponse`, `FreelancerProfileResponse`, `ProviderResponse { id, provider_type, display_name, phone_country_code, phone_number, whatsapp_number, category_label, description, slug, verification_status, is_discoverable, country_code, business_profile: BusinessProfileResponse | None, freelancer_profile: FreelancerProfileResponse | None }`.

### Exceptions (`backend/app/core/exceptions/exceptions.py` + `__init__.py`)
14. `ProviderAlreadyExistsError(BusinessException)` — 409, plain message (Decision 3). `ProviderNotFoundError(BusinessException)` — 404, plain message (Decision 9; not the non-revealing-ownership pattern, since this is always the caller's own account).

### API (`backend/app/modules/provider/api.py`)
15. `GET /providers/me` and `POST /providers/me`, both behind `get_current_user` only (bare authentication — deliberately not `require_role(ROLE_CUSTOMER)`: becoming a Provider is not conceptually gated on already holding the Customer role, even though every real account today has it; Decision 2). `POST` returns `201` with `SuccessResponse[ProviderResponse]`.

### Dependencies (`backend/app/modules/provider/dependencies.py`)
16. `get_provider_repository`, `get_business_profile_repository`, `get_freelancer_profile_repository`, `get_provider_service` (the last one importing `get_role_assignment_service` from `app.modules.identity.dependencies`, per Decision 1).

### App wiring
17. `backend/app/api/v1/api.py`: register `provider_router` at prefix `/providers`. `backend/tests/conftest.py`: add `import app.modules.provider.models` alongside the existing three (ADR-013 pattern).

### Tests
18. `backend/tests/modules/provider/test_provider_service.py`: creates a Business provider with correct defaults (verification_status=pending, is_discoverable=false — AC7/AC10); creates a Freelancer provider with correct defaults (same assertions, separate test — Decision 5); a second `create_provider` call for the same `user_id` with the **same** `provider_type` raises `ProviderAlreadyExistsError` (AC8/AC10); a second call with a **different** `provider_type` also raises `ProviderAlreadyExistsError` (AC10's type-immutability test, Decision 3); `ROLE_PROVIDER` is present in `RoleRepository.get_role_names_for_user` after creation, and calling `ensure_role_assigned` a second time for an account that already has the role is a no-op (idempotency); slug uniqueness across two providers sharing the same `display_name`.
19. `backend/tests/modules/provider/test_provider_endpoints.py`: `POST /providers/me` happy path for both subtypes, asserting the response's `provider_type`/nested subtype profile and that `providers.user_id` equals the caller's own id with **no** new `/auth/*` call involved in the test (AC2); a second `POST` for the same authenticated caller → 409; `GET /providers/me` → 404 before creation, 200 with the created row after; unauthenticated → 401; a `CreateProviderRequest` with `provider_type=business` but `freelancer_details` populated (or neither/both details present) → 422 (schema cross-validation).
20. `backend/tests/modules/identity/test_role_assignment_service.py`: `ensure_role_assigned` grants a missing role; is a no-op for an already-held role; grants a role independent of the account's existing roles (a Customer gains Provider without losing Customer).

---

## Mobile — Proposed Changes

### Shared (`mobile/lib/shared/widgets/`)
21. `step_indicator.dart` — a new, generic step-indicator widget (`currentStep`, `totalSteps`, optional `stepLabels`), no domain coupling, satisfying AC9's "step indicator visible across the multi-step form." This codebase's first multi-step-form indicator — flagged for `architect` review as a new reusable pattern, per `07_UI_GUIDELINES.md`'s "reusable components" rule (mirrors `LocationPickerScreen`'s own precedent of building generic from day one).

### Feature: Provider (new — `mobile/lib/features/provider/`)
22. `domain/models/provider_type.dart`, `domain/models/provider.dart`, `domain/models/create_provider_request.dart` (mirrors the backend request/response shapes).
23. `domain/models/provider_exception.dart` — mirrors `saved_address_exception.dart`'s never-leak-raw-Dio-error convention.
24. `data/provider_repository.dart` — `getMyProvider()` (returns `null` on 404, not an exception — mirrors how `SavedAddressRepository` treats "not found" as a normal, expected state where appropriate), `createProvider(CreateProviderRequest)` against `/providers/me`.
25. `state/provider_onboarding_controller.dart` — Riverpod controller holding the in-memory wizard draft across all steps (Decision 8): selected type, basic-info fields, and whichever subtype-details sub-object is relevant; exposes a `submit()` that calls the repository once.
26. `presentation/screens/provider_intro_screen.dart` (S-15) — value-prop copy, single "Get Started" CTA into S-16.
27. `presentation/screens/choose_provider_type_screen.dart` (S-16) — two cards (Business / Freelancer); selecting one sets the controller's type and is the **only** place `provider_type` is ever set client-side (AC3).
28. `presentation/screens/provider_basic_info_screen.dart` (S-17) — display name, phone/country code, WhatsApp number (with a "same as phone number" convenience toggle, not a hard requirement), category free-text field, description (optional); step indicator visible; routes to S-18a or S-18b based on the controller's stored type.
29. `presentation/screens/business_details_screen.dart` (S-18a) — "Pick on map" launcher into the reused `LocationPickerScreen` (Decision 7), a simple weekly operating-hours editor (7 rows, open/closed toggle + time pickers, mapping directly to the JSONB shape in schema item 10), an optional delivery-radius slider, an optional trade-license-number field. Submit calls `provider_onboarding_controller.submit()`.
30. `presentation/screens/freelancer_details_screen.dart` (S-18b) — "Pick on map" launcher into `LocationPickerScreen` for base location, a service-radius slider, a skill-tags chip input, an optional years-of-experience field. Submit calls `provider_onboarding_controller.submit()`.
31. `presentation/utils/provider_error_copy.dart` — mirrors `saved_address_error_copy.dart`'s pattern, including a specific, plain-language message for the "you already have a listing" 409 case.

### Registration/Profile integration
32. `profile_settings_screen.dart` (CUS-001): add the "List Your Business" list tile (the exact slot CUS-001's own docstring named and deferred). On tap: `getMyProvider()` — if non-null, show a plain "You already have a business listing" snackbar (Decision 9); if `null`, navigate to `AppRoutes.providerIntro` (S-15).
33. New routes in `app_routes.dart`: `providerIntro`, `chooseProviderType`, `providerBasicInfo`, `businessDetails`, `freelancerDetails`.

### Tests
34. `mobile/test/features/provider/choose_provider_type_screen_test.dart`, `provider_basic_info_screen_test.dart`, `business_details_screen_test.dart`, `freelancer_details_screen_test.dart` — each asserts the step indicator renders with the correct step number, and that only the minimal required fields per AC5/AC6 gate the "Continue"/"Submit" action (optional fields never block progress — supporting AC9's "completable in under 30 seconds" intent).
35. `mobile/test/features/provider/provider_onboarding_flow_test.dart` — full wizard integration test: type selection persists across screen navigation and is never re-askable (AC3); completing the Business path submits exactly one `createProvider` call with both basic info and business details merged; same for the Freelancer path; a second attempt to start the wizard when `getMyProvider()` already returns a Provider short-circuits to the "already have a listing" message without entering S-16 (mobile-side mirror of AC8).
36. `mobile/test/features/provider/fakes/fake_provider_repository.dart` mirroring `fake_saved_address_repository.dart`'s pattern.
37. `mobile/test/shared/widgets/step_indicator_test.dart`.

---

## Explicitly Out of Scope (do not implement in this story)

- `provider_availability`, `portfolios`, `service_areas` tables and any UI for them — PRO-002.
- `verification_records`, `verification_documents`, document upload/OCR, and any admin verification review UI — VER-001 (Flow 2 steps 6–8, Flow 6).
- The Category domain (`categories`, `category_question_templates`, `provider_categories`) — `category_label` (Decision 4) is a deliberate, temporary stand-in, not a preview of the real feature.
- Claim-Your-Listing (Flow 3), Google-seeded-unclaimed provider rows, and any code path that creates a `providers` row with `user_id IS NULL` — this story's only creation path always sets `user_id` to the caller's own id.
- Provider Dashboard (S-23), Leads (S-24), Storefront/Edit Profile (S-25), Visibility Analytics (S-26) — no `PATCH`/`PUT /providers/me` of any kind exists in this story.
- Any refactor of `AuthService`'s existing inline role-assignment logic to use the new `RoleAssignmentService` — a legitimate future cleanup, not part of this story.
- Cross-app-restart persistence of in-progress wizard state (Decision 8).
- Any Quote/messaging/payment functionality — permanently excluded per `11_MVP_SCOPE.md`.

---

## Delegation & Execution Sequence

1. **backend** — Migration, models, repositories, `ProviderService`, the new `RoleAssignmentService`/identity dependency addition, schemas, exceptions, API, dependencies, app wiring, conftest import (items 1–20 above). ACs to satisfy: 1, 2 (backend half), 3 (backend half — no update path exists), 4, 5, 6, 7, 8, 10.
2. **frontend** — Shared step indicator, Provider feature module, registration/Profile integration, routes, tests (items 21–37 above), once the backend endpoints exist (or in parallel against a fake repository, then wired to the real one). ACs to satisfy: 2 (mobile half — reuses the existing session, no new auth step), 3 (mobile half — type screen only sets it once), 9.
3. **tester** — Verify all 10 ACs individually. Particular attention to: AC2 (confirm the test reuses an already-issued JWT and never calls any `/auth/*` endpoint mid-test); AC3/AC10 (both the same-type and different-type second-creation-attempt tests exist and are distinct); AC7/AC10 (defaults asserted for **both** subtypes, not just one); AC8 (the service-layer check is exercised directly, not just trusted via the DB constraint — read the actual service code, per the CUS-002 precedent); AC9 (step indicator present on every step screen; optional fields never block progress).
4. **architect** — Review the new `provider → identity` cross-module direction (Decision 1) against ADR-014's precedent and `02_ARCHITECTURE.md`'s module-communication rule; the `category_label` schema addition (Decision 4) as a flagged, temporary deviation from `04_DATABASE.md`; the single-`POST`-at-end-of-wizard endpoint design (Decision 2) against ADR-015; and the new `StepIndicator` shared widget (item 21) for genuine reusability.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 1 as **ADR-016** in `09_DECISIONS.md`; update `04_DATABASE.md` (the new `category_label` column, Decision 4) and `12_TECH_STACK.md` (backfill the still-missing `google_maps_flutter`/`geolocator`/`geocoding` entries from CUS-002, plus confirm no new packages were added by this story).

---

## Verification Plan (mapped to the 10 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade; `\d provider.providers` / `\d provider.business_profiles` / `\d provider.freelancer_profiles` show every column/type/nullability in `04_DATABASE.md` plus `category_label`; `providers.user_id` is nullable at the column level but every row this story's code path creates has it non-null. |
| 2 | Integration test: an already-authenticated caller (existing JWT from a prior registration, no new OTP/OAuth call in the test) calls `POST /providers/me`; the resulting `providers.user_id` equals that same caller's id. |
| 3 | Widget/integration test: the type-selection screen is the only screen that writes `provider_type` into the wizard controller; unit/integration test: a second `create_provider` call for the same account with a *different* type is rejected (Decision 3). |
| 4 | Schema validation test: `CreateProviderRequest` requires `display_name`/`phone_country_code`/`phone_number`/`category_label` and rejects a payload missing them or containing a mismatched `business_details`/`freelancer_details` pair; widget test confirms S-17 renders before S-18a/b. |
| 5 | Service/integration test: a Business `POST` payload persists `address_line`/`city`/`region`/`country_code`/`latitude`/`longitude`/`operating_hours` on `business_profiles`, with `delivery_radius_meters`/`trade_license_number` both accepted as optional (nullable when omitted). |
| 6 | Service/integration test: a Freelancer `POST` payload persists `base_latitude`/`base_longitude`/`service_radius_meters`/`skills`/`years_experience` on `freelancer_profiles`, with `skills`/`years_experience` both accepted as optional. |
| 7 | Unit test (both subtypes): freshly created `providers` row always has `verification_status=pending` and `is_discoverable=false`, regardless of any request field. |
| 8 | Unit/integration test: a second `create_provider`/`POST` for the same account with the **same** `provider_type` raises `ProviderAlreadyExistsError` / returns 409 — asserted against the service layer directly, not only the DB constraint. |
| 9 | Widget tests: the step indicator widget renders on every wizard screen with the correct current/total step; each screen's "Continue"/"Submit" is enabled once only the required (non-optional) fields for that step are filled, confirming no screen requires more than its minimal field set. |
| 10 | The three tests named above (AC3's different-type test, AC8's same-type test, AC7's defaulting test) are confirmed as three distinct, independently-runnable test cases in `test_provider_service.py`. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md`
- `docs/AI/03_DOMAIN_MODEL.md`
- `docs/AI/04_DATABASE.md`
- `docs/AI/05_API_GUIDELINES.md`
- `docs/AI/06_SECURITY.md`
- `docs/AI/07_UI_GUIDELINES.md`
- `docs/AI/11_MVP_SCOPE.md`
- `docs/AI/13_OPEN_DECISIONS.md`
- `docs/AI/14_USER_FLOWS.md`
- `docs/AI/15_SCREEN_INVENTORY.md`
- `docs/AI/16_UX_GUIDELINES.md`
- `docs/implementation/plans/Plan_S03_CUS-001.md` (cross-module service-injection precedent, ADR-014)
- `docs/implementation/plans/Plan_S03_CUS-002.md` (`LocationPickerScreen` reuse origin, Decision 7; endpoint-shape precedent, ADR-015)
- `docs/implementation/plans/Plan_S02_AUTH-004.md` (`require_role`/`ensure_owner_or_not_found` origin)
