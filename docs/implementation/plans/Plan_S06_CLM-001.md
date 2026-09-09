# Plan for Story CLM-001 — Claim My Google-Seeded Business Listing

**Sprint:** 06 (Directory & Listing Claims) | **Epic:** ML6-EP02 | **Phase:** PH2 | **Priority:** Medium |
**Depends On:** VER-002, DIR-001 (both done)

---

## Story

As a business owner, I want to find my business among Google-seeded listings and verify I own the public phone
number on record, so that I gain edit access to my own storefront instead of a stranger being able to claim it.

This story bootstraps Business supply from public Google listings (so the directory isn't empty at launch) and
implements the claim flow's OTP-against-public-record safeguard. Until claimed, these listings are flagged
internally as unclaimed per the pending Google Places legal/ToS review, and must never be treated as equivalent
to a verified, self-registered provider.

**Scope boundary:** does not change how self-registered providers (PRO-001) are created — this story only handles
the separate unclaimed-listing import and claim path.

---

## Acceptance Criteria (verbatim, from `docs/AI/Project_Tracker.xlsx`)

1. Import job creates providers rows with `listing_source=google_seeded_unclaimed`, `is_claimed=false`, and a
   populated `google_place_id` — never marked as `self_registered`.
2. Unclaimed listings are visually distinct in search/directory results (a clearly visible "Unclaimed" label, not
   a small badge easy to miss).
3. Claim search screen lets a user find their business by name/location among unclaimed listings.
4. An OTP is sent to the public phone number on record for that listing — never to a number the claimant types in
   themselves.
5. Successful OTP verification sets `is_claimed=true`, populates `user_id` with the claimant's Account, and
   routes the listing through the same Verification gate a self-registered Business would go through.
6. If OTP verification fails or the public number is unusable, the flow falls back to an explicit "this isn't
   working" admin-review path.
7. Once claimed, subsequent Google Places sync jobs never overwrite owner-edited fields — imported data only
   backfills genuinely empty fields.
8. Automated tests cover: OTP-goes-only-to-public-number, and the admin-fallback path triggering correctly on
   OTP failure.

---

## Legal/Risk Posture and UX Design — Already Decided, Not Re-Litigated Here

`docs/AI/13_OPEN_DECISIONS.md` item 3: the CTO has made an explicit, informed risk-acceptance decision (09
September 2026) to proceed with `CLM-001` in its **original bulk-import scope** — permanent `providers` rows,
unverified at seed time, `listing_source`/`google_place_id` as the bulk-deletion mitigation if a future legal
review forces it. The underlying legal question (Google Maps Platform ToS, UAE PDPL) stays genuinely open and is
explicitly **not** this Plan's concern to resolve or work around with a different design — live-query-only,
rolling cache, and fetch-verify-then-store were all explicitly considered and declined by the CTO for this story.
This Plan builds exactly what item 3 describes: bulk import into permanent rows, OTP-to-public-number as the
trust gate at claim time.

`docs/AI/13_OPEN_DECISIONS.md` item 4 / `16_UX_GUIDELINES.md` (Trust & Verification UX Patterns): the unclaimed-
listing visual design is locked — a full-width, Warning-color (`#F59E0B`) banner reading "Unclaimed — Is this
your business? Claim it" with an inline CTA, on the provider card (`S-08`) and provider profile (`S-09`). This
Plan implements this exact design on `S-08` (the only one of the two that exists in the codebase today — see
Verified Current State) and does not re-derive it.

---

## Verified Current State (read directly from code and docs, not assumed)

- **Every schema column this story needs already exists — no `providers` migration required.**
  `backend/app/modules/provider/models.py`'s `Provider` model (shipped by PRO-001/PRO-002, unchanged since) already
  has `user_id` (nullable), `listing_source` (`ListingSource` enum: `SELF_REGISTERED` /
  `GOOGLE_SEEDED_UNCLAIMED`), `is_claimed` (default `false`), `claimed_at`, `google_place_id` (unique when set,
  via `uq_providers_google_place_id`), `verification_status`, `is_discoverable`, plus
  `chk_providers_claimed_has_owner` (`is_claimed=false OR user_id IS NOT NULL`) and
  `chk_providers_discoverable_requires_approved` (`is_discoverable=false OR verification_status='approved'`) —
  both already enforced at the DB level, both directly load-bearing for this story's design (see Decision 2).
  `04_DATABASE.md` itself says this schema "was designed for this story from the start" and that's confirmed true
  by direct inspection, not merely asserted.
- **`otp_purpose` already has a `CLAIM_LISTING` member** (`identity/models.py:78`), and
  `identity.otp_verifications`/`OtpService`/`OtpVerificationRepository` are fully generic across purposes
  already — `OtpService.request_otp(phone_country_code, phone_number, purpose)` and
  `.verify_otp(phone_country_code, phone_number, purpose, code)` take a purpose and a phone number as plain
  parameters, with no assumption the phone number belongs to the authenticated caller. **No new OTP mechanism is
  needed or should be built** — this is a direct, unmodified reuse, exactly as `.agents/skills/third-party-
  integrations/oauth-and-otp.md` mandates ("Reuse One OTP Table... do not build a parallel OTP mechanism per
  feature").
- **No scheduler/cron/Celery/APScheduler infrastructure exists anywhere in this codebase** (confirmed by grep —
  zero matches). The only precedent for a standalone, manually-invoked data-affecting operation is
  `backend/scripts/seed_roles.py` / `grant_admin_role.py`: a thin `async def main()` invoked via
  `uv run python -m scripts.<name>`, using `app.database.session.async_session` directly, no HTTP layer involved.
  Introducing a new scheduling framework would be a genuine, unrequested infrastructure/tooling change
  (`.agents/agents.md`'s Architecture Stability Rule: "do not modify... tooling configuration... unless
  explicitly instructed") that no AC asks for.
- **No admin dashboard UI exists, and none is expected by this story.** VER-002 (the direct precedent for
  "admin does something with no UI yet") shipped `admin_api.py` as a backend-only, Postman/API-client-consumed
  surface (`Plan_S05_VER-002.md`), explicitly by design. AC6 only requires the fallback path to exist and be
  reachable, not a dashboard.
- **`ProviderService.apply_verification_outcome(provider_id, *, verification_status, is_discoverable)` already
  exists** (added by VER-002, used by `AdminVerificationService.approve`/`.reject`) — a ready-made, atomic
  "rewrite the cached verification state" primitive this story reuses twice: once (inverted) at import time, once
  at claim time (Decision 2/6).
- **`ProviderService.create_provider`'s existing pattern is the direct template for the import job**:
  slug generation (`_generate_unique_slug`, private but same-class-reusable), `business_profiles` row creation,
  `service_area_repository.upsert_for_provider(...)` (**critical**: DIR-001's actual search query joins
  `provider.service_areas`, not just `providers` — a `providers` row with `is_discoverable=true` but no matching
  `service_areas` row is invisible to any geospatial search, silently defeating AC2 for the exact case that
  matters), and `provider_category_label_repository.replace_all(...)` for a primary category label. All four are
  directly reusable/extendable, not reinvented (Decision 3).
- **`PATCH /providers/me` and `GET /providers/me` are already scoped to `get_by_user_id(current_user.id)`**
  (`provider_repository.py`), which returns `None` for any provider whose `user_id` is still `NULL`. This means
  "cannot be edited... until claimed" (`03_DOMAIN_MODEL.md` line 112) is **already enforced by existing code with
  zero changes** — an unclaimed listing is simply unreachable through the self-service surface until `user_id` is
  populated by a successful claim. No new authorization code is needed for this half of the story.
- **`VerificationService.submit()` resolves the caller's provider via `ProviderService.get_my_provider(user_id)`**
  — i.e. by `user_id`, not by any verification-specific state. Once a claim sets `providers.user_id`, the
  claimant's account can call the *existing, unmodified* `POST /providers/me/verification/*` endpoints and they
  will resolve correctly to the now-claimed provider. **AC5's "routes through the same Verification gate a
  self-registered Business would go through" requires zero new verification-module code** — it only requires
  claim finalization to leave the provider in the same `verification_status=pending`/`is_discoverable=false`
  state a freshly self-registered provider starts in (Decision 2), after which every existing VER-001/VER-002
  screen and endpoint (S-19/S-20, admin approve/reject queue) works unmodified. This is confirmed by reading
  `admin_api.py`: there is no auto-approval path for a "lightweight" Business verification type anywhere in the
  codebase — every Business, self-registered or claimed, goes through the same admin approve/reject queue.
- **`docs/AI/03_DOMAIN_MODEL.md` line 112 states a Provider seeded from Google "starts as Unclaimed and is
  discoverable"** — a literal, present-tense business rule read together with the `chk_providers_discoverable_
  requires_approved` constraint means the import job must set `verification_status=approved` (a synthetic,
  system-granted state, not an admin-reviewed one) alongside `is_discoverable=true` at seed time, or the two
  statements (business rule vs. DB constraint) cannot both be true simultaneously. This is a real design tension
  the existing docs leave implicit; Decision 2 makes it explicit and resolves it the only way consistent with
  both sources.
- **`docs/AI/02_ARCHITECTURE.md` (Core Business Modules → Provider) explicitly lists "Claim flow for Google-seeded
  unclaimed listings" as a Provider-module responsibility** (line 299) — settling module placement directly from
  existing, authoritative architecture text, not left to this Plan's own judgment (Decision 7).
- **`docs/AI/15_SCREEN_INVENTORY.md` already specifies `S-21` (Claim Your Listing — Search) and `S-22` (Claim OTP
  Verification)**, with the exact UI elements this story must build: S-21 = "Search by business name/location" →
  "Select listing"; S-22 = "Code sent to public number on record, 'this isn't working' fallback link" → "Verify".
  **`S-09` (Provider Profile) does not exist in the mobile codebase at all yet** — confirmed via
  `Plan_S06_DIR-001.md`'s own explicit deferral ("The Provider Profile screen (S-09)... this story's result cards
  are tap-stubbed only; a full profile view is a future story's scope"). AC2's literal wording is "visually
  distinct in search/directory results" — satisfied by `S-08` alone; `16_UX_GUIDELINES.md`'s mention of `S-09` is
  the general resolved *design* for whenever that screen is eventually built, not a requirement this story build
  `S-09` itself (no AC asks for it — see Explicitly Out of Scope).
- **DIR-001's `SearchResultProviderResponse` (`search/schemas.py`) does not currently expose `listing_source` or
  `is_claimed`** (confirmed: DIR-001's own Plan explicitly scoped its query to `is_discoverable=true` "regardless
  of `listing_source`" and explicitly flagged unclaimed-listing labeling as **not** its scope, deferred to this
  story). Since the import job will set `is_discoverable=true` on unclaimed rows (Decision 2), they **already
  flow through DIR-001's existing `GET /search/providers` query unmodified** the moment they exist — the only gap
  is that the response payload doesn't yet carry the one field (`is_claimed`) the mobile card needs to decide
  whether to render the banner. This is a small, additive extension of an existing response shape, not new query
  logic (Decision 8).
- **No Google Places API client, SDK, or credential exists anywhere in this codebase.** `httpx>=0.28.1` is
  already an approved dependency (used elsewhere for outbound HTTP); no Google Maps/Places SDK is installed or
  approved. `GOOGLE_OAUTH_CLIENT_ID` exists in `config.py` but is a **different** Google credential (OAuth Sign-
  In audience validation, AUTH-002) — not reusable for Places API calls, which need their own API key
  (Decision 10).
- **This codebase's established pattern for "an external capability with no real implementation confirmed yet"
  is a swappable Protocol + a concrete implementation, never a hardcoded direct call** — `DocumentOcrService`
  (ADR-018) and `FileStorage` (ADR-017) are the two precedents. Decision 10 follows this same shape for the
  Google Places API client, since automated tests (AC8) cannot make real network calls to a paid third-party API.

---

## Architecture Decisions

### Decision 1 — Import/sync mechanism: a manually-invoked CLI script, not a new scheduler; idempotent upsert keyed on `google_place_id` serves both the first bulk seed and every later re-sync

**The problem:** AC7 says "subsequent Google Places sync jobs," implying this runs more than once, but no
scheduling infrastructure exists in this codebase, and introducing one (Celery, APScheduler, a cron container)
is a real tooling/infrastructure change no AC asks for and `.agents/agents.md`'s Architecture Stability Rule
flags as needing explicit instruction first.

**Chosen:** one script, `backend/scripts/import_google_places.py`, following the exact `seed_roles.py`/
`grant_admin_role.py` shape (`async def main()`, `async_session()`, `uv run python -m scripts.import_google_places
...`), accepting CLI arguments for the search target (e.g. a text query and/or lat/lng + radius, per the Google
Places API's own search shape) and `--country-code`. The **same script** run is both "the bulk seed" (first run,
every place is new) and "a subsequent sync job" (later runs, most places already exist) — idempotency is achieved
by looking up each fetched place's `google_place_id` via a new `ProviderRepository.get_by_google_place_id(...)`
before deciding whether to create (Decision 1a) or update-with-backfill-only (Decision 6). Actually running this
script on a recurring cadence (a hosting-platform scheduled task, an ops runbook, or a future dedicated scheduler
story) is explicitly **not** built by this story — the script is idempotent and safe to run on any cadence,
whenever someone or something invokes it.

**Alternatives considered and rejected:**
- **Build a recurring in-app scheduler now (APScheduler/Celery beat)** — rejected: new infrastructure/dependency
  the Architecture Stability Rule requires explicit instruction for, and no AC requires the *app itself* to
  trigger re-syncs autonomously — only that a sync job, however triggered, respects the backfill-only rule.
- **A one-time, non-reusable seed script (no re-sync capability at all)** — rejected: AC7's literal "subsequent...
  sync jobs" wording requires the re-sync behavior to actually exist and be exercised by tests (AC8), not merely
  be a hypothetical future extension.

### Decision 2 — Import-time discoverability: synthetic `verification_status=approved` + `is_discoverable=true` + a matching system-generated `verification_records` row; claim resets both to `pending`/`false`

**The problem, stated precisely:** two authoritative sources must both be true at once. `03_DOMAIN_MODEL.md`
line 112: "A Provider seeded from Google listings starts as Unclaimed and **is discoverable**." The DB constraint
`chk_providers_discoverable_requires_approved`: `is_discoverable=false OR verification_status='approved'`. The
only way both are true is for the import job to set `verification_status=approved` directly — not through the
admin queue, since there is no document, no submitter, and nothing for an admin to review at import time.

**Chosen:**
- **At import (Decision 3):** `providers.verification_status=APPROVED`, `is_discoverable=True`, set directly by
  the import job's own write (mirroring `apply_verification_outcome`'s field pair, not calling that method itself
  since there is no existing provider row yet — this is `create`, not `update`). A matching
  `verification.verification_records` row is created in the same job, `status=APPROVED`, `verification_type=
  BUSINESS_LIGHTWEIGHT` (Google-seeded listings are always Business, Decision 3), `reviewed_by=NULL` (no human
  admin reviewed it — `reviewed_by` is already nullable per `04_DATABASE.md`), `submitted_at`/`reviewed_at` both
  `now()`. This keeps `verification_records` as the honest source of truth (`04_DATABASE.md`: "this table is the
  source of truth") in sync with the cached `providers` columns, exactly the invariant VER-001/VER-002 already
  established — a `providers.verification_status=approved` with **no** corresponding `verification_records` row
  would be a silent, undocumented exception to that invariant.
- **At successful claim (AC5, Decision 6):** immediately after `is_claimed`/`user_id`/`claimed_at` are set, in
  the same transaction, `ProviderService.apply_verification_outcome(provider_id, verification_status=PENDING,
  is_discoverable=False)` is called — the **exact same method** VER-002 built, applied in reverse. This is the
  literal mechanism of "routes through the same Verification gate a self-registered Business would go through"
  (AC5): the claimed provider is left in the identical `pending`/`false` state `create_provider` already puts a
  brand-new self-registered Business into, so every existing verification screen/endpoint picks it up unmodified
  (Verified Current State). The listing becomes temporarily non-discoverable at the moment of claim — an
  intentional, correct trade-off: an unverified Google listing is provisionally trusted as "this business plausibly
  exists, Google agrees," but a *claimed* listing carries a real, individual owner's accountability and must earn
  the same trust a self-registered Business earns, not inherit the pre-claim synthetic approval.

**Alternatives considered and rejected:**
- **Leave unclaimed listings at `verification_status=pending`, `is_discoverable=false` (i.e. hidden until
  claimed)** — rejected: directly contradicts `03_DOMAIN_MODEL.md`'s explicit "is discoverable" business rule and
  would make AC2 ("visually distinct in search/directory results") untestable, since a non-discoverable provider
  never appears in DIR-001's search results at all — there would be nothing to visually distinguish.
  `13_OPEN_DECISIONS.md` item 4's own resolution text ("hidden until claimed" vs. "shown with an unclaimed label"
  is framed as a real choice already made) confirms the chosen path is "shown," not "hidden."
  `13_OPEN_DECISIONS.md` item 4's own text: "`providers.is_claimed`/`is_discoverable` are independent flags...
  the eventual answer here is a query-time filter" — read together with item 4's chosen resolution (a visible
  banner, not hiding), this confirms unclaimed rows are meant to be visible/discoverable, not suppressed.
- **Keep the claimed provider's `verification_status=approved` unchanged through claim (skip re-verification)**
  — rejected outright: this is precisely the outcome the story's own description forbids ("must never be treated
  as equivalent to a verified, self-registered provider") and directly contradicts AC5's literal "routes through
  the same Verification gate" wording.
- **A dedicated `verification_status` value like `google_verified` distinct from `approved`** — rejected: no such
  enum value exists in `04_DATABASE.md`'s locked `verification_status` enum (`pending`/`under_review`/`approved`/
  `rejected`), and adding one is an unrequested schema change with no AC basis; the existing `approved` value,
  applied honestly with its own system-generated `verification_records` row documenting *why* (no reviewer,
  Business-lightweight type), is sufficient and auditable.

### Decision 3 — Import job always creates `provider_type=BUSINESS`; required-but-Google-doesn't-provide fields are defaulted from best-effort mapping, not fabricated

Google Places listings are storefronts/businesses with a public address and (usually) a phone number — nothing in
Google Places' data shape represents an individual Freelancer (no fixed address requirement, no service radius,
no skills list). `14_USER_FLOWS.md` Flow 3's own title ("Claim-Your-Listing (Google-Seeded Unclaimed **Business**)")
and every domain-model/UX reference to this feature say "Business," never "Freelancer."

**Chosen field mapping** (Google Places `Place Details` response → `providers`/`business_profiles`):
| Provider/BusinessProfile field | Source | Notes |
|---|---|---|
| `provider_type` | hardcoded `BUSINESS` | Decision 3's own conclusion |
| `display_name` | `name` | |
| `slug` | generated | reuses `ProviderService`'s existing `_generate_unique_slug` helper unmodified |
| `phone_country_code`/`phone_number` | `international_phone_number`, parsed | **left `NULL` if Google has no public phone number for this place** — never fabricated; AC6's "public number is unusable" case is a direct, expected consequence, not a bug |
| `address_line` | `formatted_address` (full string) | honest, always-present single field; Google's granular `address_components` aren't force-fit into a schema that doesn't ask for that granularity |
| `city` / `region` | `address_components` `locality` / `administrative_area_level_1`, if present | nullable already; left `NULL` if Google doesn't return the component |
| `latitude`/`longitude` | `geometry.location` | always present for a real place; a place missing this is skipped, not imported with fabricated coordinates |
| `country_code` | `address_components` `country` (short_name — already ISO 3166-1 alpha-2) | matches `04_DATABASE.md`'s country-agnostic requirement directly, no hardcoded UAE default |
| `operating_hours` | `opening_hours.periods`, best-effort mapped to this schema's single open/close-per-weekday JSONB shape (first period per day if multiple exist) | left `NULL` if Google provides none — never fabricated "closed all day" |
| `delivery_radius_meters` | not provided by Google | `NULL`; `service_areas.radius_meters` falls back to `0` (Decision 4), mirroring `create_provider`'s own existing fallback for a Business with no delivery radius |
| `trade_license_number` | not provided by Google | `NULL` — a claimant may add it later via the existing `PATCH /providers/me` `business_details` field, unchanged |
| category label | Google Places `types[0]`, humanized via a small lookup table, one best-effort primary `provider_category_labels` row | flagged low-confidence; freely editable post-claim via the existing `PATCH /providers/me` `category_labels` field — no new code needed for that edit path |

A place missing `name`, `geometry.location`, or `formatted_address` (the fields with no nullable column to fall
back to) is **skipped entirely** by the import job (logged, not imported as a partially-fabricated row) — never
a Provider row with an invented address or coordinates.

**Alternatives considered and rejected:**
- **Import Freelancer-subtype rows from Google data** — rejected per the reasoning above; no AC, flow, or domain
  text supports it, and the data shape genuinely doesn't fit.
- **Require a phone number to exist before importing a place at all** — rejected: this would silently shrink
  supply for no benefit (the story's own AC6 explicitly anticipates and designs around "the public number is
  unusable" as a real, expected case) and isn't asked for by any AC.
- **Build the real Category taxonomy mapping now** — rejected: `13_OPEN_DECISIONS.md` item 1 is still the
  critical-path open decision; a best-effort free-text label (mirroring DIR-001 Decision 1's identical interim
  posture) is the only reasonable choice available today.

### Decision 4 — Import job also creates a matching `service_areas` row — omitting this would silently make imported listings invisible to the one search query that actually implements AC2

DIR-001's `ProviderSearchRepository.search_nearby` joins `provider.service_areas`, not `providers` alone. A
`providers` row with `is_discoverable=true` but no `service_areas` row is a legitimate SQL "no match" for every
geospatial search — it would never appear in `GET /search/providers` results regardless of how the origin/radius
are chosen, defeating AC2's "visually distinct in search/directory results" for the exact code path customers
actually use to browse.

**Chosen:** the import job calls the existing, unmodified `ServiceAreaRepository.upsert_for_provider(provider_id,
center_latitude=..., center_longitude=..., radius_meters=business_details.delivery_radius_meters or 0)` —
identical to `create_provider`'s own Business-path call, reused verbatim, no new repository method needed.

**Alternative considered and rejected:** relying on some future story to notice and backfill this — rejected:
this would make CLM-001 ship with a documented AC quietly unsatisfied for its own primary product surface
(directory browsing), which is not an acceptable interim state for a shipped story.

### Decision 5 — Claim search (AC3): a new, dedicated free-text query in the `provider` module, distinct from DIR-001's `search` module — substring `ILIKE` on name, not exact match

**The problem:** DIR-001's `SearchService`/`ProviderSearchRepository.search_nearby` is a category+geo+
discoverability query for the customer-facing directory — it has no name-search capability at all, and (per its
own Plan) is explicitly out of `CLM-001`'s reach as a dependency ("does not touch `CLM-001`... at all"). AC3
needs a genuinely different query shape: "find your own business by name/location among **unclaimed** listings,"
which is scoped by `listing_source`/`is_claimed`, not by discoverability/geo-radius/category.

**Chosen:** a new repository method, `ProviderRepository.search_unclaimed(*, query: str, limit: int, offset:
int) -> tuple[list[Provider], int]`, filtering `listing_source=GOOGLE_SEEDED_UNCLAIMED AND is_claimed=false`,
matching `query` via case-insensitive **substring** `ILIKE` against `display_name` **and** (via a join)
`business_profiles.address_line`/`city`. Substring matching is deliberately chosen here — unlike DIR-001
Decision 1's exact-match category reasoning — because this is a person searching for *their own, specific,
already-known* business name/address, where partial/fuzzy typing is the expected, helpful use case (e.g. "Al
Noor Plumb" should find "Al Noor Plumbing Services LLC"), not an ungoverned free-text taxonomy where false
positives compound (the reasoning that made DIR-001 reject substring matching for categories doesn't apply to a
one-off, self-identifying name search). Exposed via a new `ProviderService.search_unclaimed_listings(...)` thin
pass-through (mirroring `search_nearby`'s existing shape) and a new customer-facing endpoint (Backend Proposed
Changes).

**Alternatives considered and rejected:**
- **Extend DIR-001's `search_nearby`/`SearchService` with an `unclaimed_only` flag** — rejected: conflates two
  genuinely different query intents (proximity-ranked category browsing vs. name-search among a specific,
  narrow subset) into one method, and would force DIR-001's `search` module to depend on `is_claimed`/
  `listing_source`, columns its own Plan explicitly and correctly declined to touch.
- **PostgreSQL Full Text Search (`04_DATABASE.md`'s Phase 1 FTS strategy)** — rejected: FTS is not wired up
  anywhere yet in this codebase (DIR-001 didn't build it either), and a simple `ILIKE` substring match is
  sufficient for a bounded, low-volume claim-search use case; introducing FTS now for one screen would be
  disproportionate, unrequested infrastructure.

### Decision 6 — Claim finalization: OTP success immediately sets `is_claimed=true`/`user_id`/`claimed_at` (AC5's literal ordering), enforces one-Provider-per-Account, grants `ROLE_PROVIDER`

AC5's literal wording: "Successful OTP verification **sets** `is_claimed=true`, populates `user_id`... **and**
routes the listing through the same Verification gate" — three things happening together as the direct
consequence of OTP success, not "waits for a subsequent verification approval before flipping `is_claimed`."

**Chosen:** on `OtpService.verify_otp(...)` success, within one transaction:
1. Re-fetch the target provider fresh (defends against a race: two people attempting to claim the same listing
   concurrently) and re-check `is_claimed=false` — if already claimed by the time this resolves, raise a 409
   (mirrors `create_provider`'s `ProviderAlreadyExistsError` precedent for "someone else already did this").
2. Enforce the existing one-Provider-per-Account rule (PRO-001, AC8): if the claimant's account
   (`ProviderRepository.get_by_user_id(current_user.id)`) already owns a Provider, reject (the same
   `ProviderAlreadyExistsError`, reused, not duplicated) — a claimant cannot already be a Provider under a
   different listing.
3. `providers` update: `is_claimed=True`, `user_id=current_user.id`, `claimed_at=now()`.
4. `ProviderService.apply_verification_outcome(provider_id, verification_status=PENDING, is_discoverable=False)`
   (Decision 2).
5. `RoleAssignmentService.ensure_role_assigned(current_user.id, ROLE_PROVIDER)` — reused unmodified, identical to
   `create_provider`'s own call, since a claimed listing now needs Provider-mode dashboard access (S-23–S-26).

**Alternatives considered and rejected:**
- **Defer setting `is_claimed=true` until an admin/verification approval completes** — rejected: contradicts
  AC5's literal, present-tense wording ("sets... and routes"), and would leave the claimant locked out of even
  starting their verification submission (which itself requires `get_my_provider` to resolve their now-owned
  provider) — a circular blocker.
- **Allow a claimant to already own another Provider (dual-listing account)** — rejected: no AC/domain text ever
  relaxes the existing, hard one-Provider-per-Account rule for the claim path specifically; silently allowing it
  here would be an inconsistent, undocumented carve-out.

### Decision 7 — Module placement: both claim endpoints (customer-facing and admin-facing) live in the `provider` module, per `02_ARCHITECTURE.md`'s explicit assignment

`02_ARCHITECTURE.md` names "Claim flow for Google-seeded unclaimed listings" directly under the Provider module's
responsibilities — this is not left to this Plan's judgment.

**Chosen:** new files inside `backend/app/modules/provider/`:
- `services/claim_service.py` — `ClaimService` (customer-facing: search, request-otp, verify-otp, request-
  admin-review), depending on `ProviderRepository`/`ProviderService` (local), `OtpService` (from
  `identity/dependencies.py` — the same cross-module shape ADR-016 already established for `provider →
  identity`), `RoleAssignmentService` (already a `ProviderService` dependency, reused), and a new
  `ClaimReviewRequestService` (from `administration`, Decision 9 — the same `X → administration` shape VER-002's
  `AdminVerificationService` already established for `verification → administration`).
- `services/admin_claim_service.py` — `AdminClaimService` (admin-facing: list open review requests, approve/
  reject one, which either finalizes the claim via the same logic `ClaimService` uses or leaves it unclaimed with
  a reason) — mirrors `verification`'s existing `VerificationService`/`AdminVerificationService` split exactly
  (a customer-facing service and a sibling admin-facing service in the same module, not one service handling
  both).
- `claim_api.py` (customer-facing router, mounted at `/claims`) and `admin_claim_api.py` (admin-facing router,
  mounted at `/admin/claims`) — mirrors `verification/api.py` + `verification/admin_api.py`'s exact two-router-
  one-module precedent.

**Alternatives considered and rejected:**
- **A new standalone `claim` module** — rejected outright: `02_ARCHITECTURE.md` already assigns this
  responsibility to Provider by name; inventing a new module would contradict existing, authoritative
  architecture text without cause.
- **Put the admin-facing claim endpoints inside `administration` module instead of `provider`** — considered,
  since the underlying review-queue table lives in the `administration` schema (Decision 9) — rejected in favor
  of consistency with VER-002's own precedent (`admin_api.py` lives inside the module that owns the *domain*
  being reviewed, `verification`, even though it depends on `administration`'s `AdminActionLogService` for
  logging) and with `02_ARCHITECTURE.md`'s explicit Provider-module assignment.

### Decision 8 — `SearchResultProviderResponse` (DIR-001) gains one new field, `is_claimed: bool`; mobile renders the Warning banner on `S-08` only (not `S-09`, which doesn't exist yet)

Since Decision 2 makes unclaimed listings `is_discoverable=true`, they already flow through DIR-001's existing
`GET /search/providers` query today, unmodified. The only gap for AC2 is that the response shape doesn't expose
the one field the mobile card needs.

**Chosen:** add `is_claimed: bool` to `search/schemas.py`'s `SearchResultProviderResponse`, populated directly
from `Provider.is_claimed` in `SearchService`'s existing mapping code (a one-field, additive, non-breaking change
— no existing consumer of this response reads a fixed field set that would be broken by an addition). Mobile's
`provider_search_card.dart` (DIR-001) renders the full-width Warning-color banner with the exact locked copy
("Unclaimed — Is this your business? Claim it") when `isClaimed == false`, with the CTA navigating directly to
`S-22` (Claim OTP) for that specific `provider_id` — skipping `S-21`'s search step, since the user has already
found the exact listing by tapping its card.

**Alternatives considered and rejected:**
- **Build `S-09` (Provider Profile) now, so the banner can appear there too, matching `16_UX_GUIDELINES.md`'s
  full description** — rejected: no AC asks for a Provider Profile screen; DIR-001 already explicitly deferred
  `S-09` to a future story, and building it as a side effect of `CLM-001` would be unrequested scope creep. AC2's
  literal wording ("search/directory results") is satisfied by `S-08` alone.
- **A new, separate endpoint just for unclaimed-listing metadata, left to correlate client-side** — rejected:
  unnecessarily indirect; a single additive field on the existing response is simpler and keeps the banner
  decision fully server-driven (no client-side guessing from other signals).

### Decision 9 — AC6's admin-review fallback: a new `administration.claim_review_requests` table, mirroring `unmatched_query_reports`'s existing precedent; admin-API-only, no dashboard UI

`unmatched_query_reports` is `04_DATABASE.md`'s own precedent for exactly this shape: "a physical table (not a DB
view) because admin review status must be writable and durable," `status` `open`/`reviewed`/`actioned`,
`reviewed_by` nullable until acted on. No such table exists today for claim fallbacks (this is genuinely new
schema, not previously specified in `04_DATABASE.md` — flagged for `04_DATABASE.md`'s Administration Domain
section to be updated at story close, per `.agents/agents.md`'s documentation rule).

**Chosen:** new table `administration.claim_review_requests` (full `CommonColumnsMixin`, matching
`admin_action_log`'s own precedent of using the full mixin rather than being exempted like `audit_logs`):

| Column | Type | Nullable | Notes |
|---|---|---|---|
| provider_id | UUID | No | FK → `provider.providers.id` |
| claimant_user_id | UUID | No | FK → `identity.users.id` — who was attempting to claim |
| reason | VARCHAR(30) | No | `otp_failed` \| `no_public_number` — VARCHAR, not enum (small, but mirrors `04_DATABASE.md`'s own stated preference for VARCHAR+app-constant over a DB enum for values expected to grow) |
| status | VARCHAR(20) | No | `open` \| `resolved`. Default `open` |
| resolution | VARCHAR(20) | Yes | `approved` \| `rejected`, set only when `status=resolved` |
| resolution_notes | TEXT | Yes | |
| reviewed_by | UUID | Yes | FK → `identity.users.id` (Admin) |
| reviewed_at | TIMESTAMPTZ | Yes | |

New `ClaimReviewRequestRepository` + `ClaimReviewRequestService` (`administration/services/`), mirroring
`AdminActionLogService`'s "one explicit method per action" convention (`create`, `list_open`, `resolve` — not a
generic CRUD surface). `AdminClaimService` (Decision 7, in `provider`) depends on this service the same way
`AdminVerificationService` already depends on `AdminActionLogService`. `AdminClaimService.approve_review_request`
runs the **identical finalization logic** `ClaimService`'s OTP-success path runs (Decision 6) — extracted as one
shared private helper on `ClaimService` that both the OTP path and the admin-approval path call, so the two
success paths can never silently drift apart.

**Alternatives considered and rejected:**
- **No persistent table — just notify "an admin" generically** — rejected: VER-002's own established pattern for
  admin work items is a durable, listable, writable queue (`unmatched_query_reports`'s stated reasoning applies
  identically here), not a fire-and-forget notification with nothing to act on later; also, `notifications.
  user_id` requires a specific recipient, and there is no "the admin team" recipient concept anywhere in this
  codebase — every existing notification precedent targets one specific user.
  Nowhere in this codebase does any existing flow (Flow 6's verification queue included) proactively notify an
  admin about new queue items — admins pull from a queue (`GET /admin/verification/records`). This story follows
  the same, already-established pull model rather than inventing a push one.
- **Reuse `manual_match_assignments`** — rejected: that table's `assigned_admin_id` is `NOT NULL` at creation,
  requiring a specific admin assigned up front, which doesn't fit "an unclaimed, unassigned queue item any admin
  may pick up" (the `unmatched_query_reports` shape fits this case, not `manual_match_assignments`'s).

### Decision 10 — Google Places API client: a swappable `GooglePlacesClient` Protocol (mirrors `DocumentOcrService`/`FileStorage`), one real `httpx`-based implementation, one fake for tests; new optional `GOOGLE_PLACES_API_KEY` setting

Automated tests (AC8, and the import job's own tests) cannot make real network calls to a billed third-party API.
This codebase's established answer to "an external capability with no live-tested implementation in CI" is a
Protocol + swappable implementation, established twice already (ADR-017, ADR-018).

**Chosen:** `provider/services/google_places_client.py` defines a `GooglePlacesClient` Protocol (`search_places`,
`get_place_details`), with `HttpxGooglePlacesClient` as the real implementation (using the already-approved
`httpx` dependency, no new package) and `FakeGooglePlacesClient` (test-only, returns canned fixture places) —
the import job's own service layer depends on the Protocol, never the concrete class, exactly like
`VerificationService` depends on `DocumentOcrService`. `GOOGLE_PLACES_API_KEY: str | None = None` is added to
`config.py` as **optional** (deliberately unlike `GOOGLE_OAUTH_CLIENT_ID`'s required style) since it is consumed
only by the standalone import script, not by the running API application every request depends on — the script
fails fast with a clear, actionable error if invoked while unset, rather than the whole app refusing to boot in
every environment that never runs the import job.

**Alternatives considered and rejected:**
- **A third-party Google Maps/Places Python SDK dependency** — rejected: `httpx` direct REST calls are
  sufficient (Places API is a plain REST/JSON API), and adding a new SDK dependency needs explicit approval per
  `.agents/agents.md` ("Do not introduce additional frameworks or dependencies without approval") that no AC
  requests.
- **Make `GOOGLE_PLACES_API_KEY` required like `GOOGLE_OAUTH_CLIENT_ID`** — rejected: would force every
  environment (including CI and every developer's local `.env`) to hold a real or dummy Places API key just to
  boot the FastAPI app, for a capability only the standalone script ever touches.

---

## Backend — Proposed Changes

### Migrations
1. `claim_review_requests` — new Alembic migration (down-revision = `a804c46bf703`, `category_domain`, the
   current head). Creates `administration.claim_review_requests` exactly per Decision 9's column table, with
   `idx_claim_review_requests_provider_id`, `idx_claim_review_requests_status`. **No changes to any existing
   table** — every `providers` column this story needs already exists (Verified Current State).

### `provider` module
2. `repositories/provider_repository.py` — new `get_by_google_place_id(place_id) -> Provider | None` (import
   idempotency, Decision 1); new `search_unclaimed(*, query, limit, offset) -> tuple[list[Provider], int]`
   (Decision 5, joins `business_profiles` for address/city matching).
3. `services/provider_service.py` — new `create_google_seeded_provider(*, google_place_id, display_name,
   phone_country_code, phone_number, ..., business_details) -> Provider` (Decision 2/3/4: creates the `providers`
   row with `listing_source=GOOGLE_SEEDED_UNCLAIMED`, `is_claimed=False`, `verification_status=APPROVED`,
   `is_discoverable=True`; creates `business_profiles`, `service_areas`, one best-effort category label; returns
   the created provider so the import job can create the matching `verification_records` row); new
   `backfill_google_seeded_provider(...)` (Decision 6/AC7: given an existing provider + freshly-fetched Google
   data, writes only fields currently `NULL`/empty — see item 4 below for the exact field-write policy); new
   `search_unclaimed_listings(...)` thin pass-through (Decision 5).
4. **AC7's field-write policy, stated precisely (governs both `create_google_seeded_provider`'s re-run behavior
   and `backfill_google_seeded_provider`):** if `provider.is_claimed is False`, a re-sync **fully overwrites**
   every mapped field with fresh Google data (safe — no owner exists yet whose edits could be lost). If
   `provider.is_claimed is True`, a re-sync writes **only** fields whose current stored value is `NULL` or an
   empty string — any field with an existing non-empty value is left untouched, regardless of what Google's
   fresh data says, satisfying AC7's literal "imported data only backfills genuinely empty fields" for the
   post-claim case.
5. `services/claim_service.py` (new, Decision 6/7) — `ClaimService`:
   - `search_unclaimed(query, limit, offset)` → Decision 5.
   - `request_otp(provider_id)` — loads the target provider (must be `listing_source=GOOGLE_SEEDED_UNCLAIMED`,
     `is_claimed=False`, else `ClaimTargetNotFoundError`); if `phone_number is None`, raises
     `ClaimPublicNumberUnavailableError` (AC6's "public number is unusable" case) rather than calling
     `OtpService`; otherwise calls `OtpService.request_otp(provider.phone_country_code, provider.phone_number,
     purpose=OtpPurpose.CLAIM_LISTING)` — **the phone number always comes from the provider row, never from any
     request body field** (AC4's literal, hard requirement — there is no "phone_number" parameter on this method
     or its endpoint at all, by construction, not by validation).
   - `verify_otp(user_id, provider_id, code)` — re-loads the provider, calls `OtpService.verify_otp(provider.
     phone_country_code, provider.phone_number, purpose=OtpPurpose.CLAIM_LISTING, code=code)`; on success, runs
     the shared `_finalize_claim(provider, user_id)` helper (Decision 6/9). `InvalidOtpError`/`OtpLockedError`
     propagate unchanged (AC6 is a distinct, user-initiated action, not an automatic N-failures trigger — see
     next item).
   - `request_admin_review(user_id, provider_id, reason: Literal["otp_failed", "no_public_number"])` — AC6's
     explicit fallback: creates a `claim_review_requests` row via `ClaimReviewRequestService.create(...)`.
   - `_finalize_claim(provider, user_id)` (private, shared with `AdminClaimService`, Decision 9) — Decision 6's
     five-step sequence.
6. `services/admin_claim_service.py` (new, Decision 9) — `AdminClaimService`: `list_open_review_requests(page,
   page_size)`, `approve_review_request(admin_user_id, request_id)` (calls `ClaimService._finalize_claim`, marks
   the request `resolved`/`approved`), `reject_review_request(admin_user_id, request_id, notes)` (marks
   `resolved`/`rejected`, leaves the provider unclaimed).
7. `claim_api.py` (new router, mounted `/claims`, `require_role(ROLE_CUSTOMER)` — becoming a Provider doesn't
   currently require holding another role first per `get_my_provider`'s bare-auth precedent, but *searching for
   and claiming* a listing is a Customer-initiated action in the product sense, mirroring DIR-001 Decision 3's
   reasoning; every registered Account already holds `ROLE_CUSTOMER`, so this imposes no extra friction):
   - `GET /claims/search?query=&page=&page_size=` (AC3) → `CollectionResponse[ClaimSearchResultResponse]`.
   - `POST /claims/{provider_id}/request-otp` (AC4) → `SuccessResponse[RequestOtpResponse]` (reuses identity's
     existing response shape).
   - `POST /claims/{provider_id}/verify-otp` (AC5, body: `{code: str}`) → `SuccessResponse[ClaimResultResponse]`.
   - `POST /claims/{provider_id}/request-admin-review` (AC6, body: `{reason: Literal[...]}`) →
     `SuccessResponse[None]`.
   - Rate-limited identically to `identity/api.py`'s OTP endpoints (`RateLimitDependency`, reusing
     `AUTH_RATE_LIMIT_PER_MINUTE`/`WINDOW_SECONDS`, IP+phone-keyed on the resolved provider's number) — the same
     abuse surface (repeated OTP requests) exists here and deserves the same defense.
8. `admin_claim_api.py` (new router, mounted `/admin/claims`, `require_role(ROLE_ADMIN)` only — mirrors
   `verification/admin_api.py`'s ownerless authorization shape, ADR-023): `GET /admin/claims` (list open),
   `POST /admin/claims/{request_id}/approve`, `POST /admin/claims/{request_id}/reject`.
9. `services/google_places_client.py` (new, Decision 10) — `GooglePlacesClient` Protocol,
   `HttpxGooglePlacesClient`, `FakeGooglePlacesClient`.
10. `dependencies.py` — new providers: `get_claim_service` (depends on `get_provider_repository`,
    `get_provider_service`, `get_otp_service` from `identity/dependencies.py`, `get_role_assignment_service`,
    `get_claim_review_request_service` from the new `administration/dependencies.py` entry — Decision 9);
    `get_admin_claim_service` (depends on `get_claim_service`, `get_claim_review_request_service`).
11. `schemas.py` — `ClaimSearchResultResponse { id, display_name, address_line, city, phone_number_masked:
    str | None }` (AC3 — `phone_number_masked` shows e.g. `+971 5** *** 678` so a searcher can sanity-check
    "is this my number" without the full number being fully exposed pre-claim to anyone who merely searched;
    never the raw number); `ClaimResultResponse { provider_id, is_claimed, verification_status }`.

### `administration` module
12. `models.py` — `ClaimReviewRequest` (Decision 9).
13. `repositories/claim_review_request_repository.py` (new).
14. `services/claim_review_request_service.py` (new) — `create`, `list_open`, `resolve` (mirrors
    `AdminActionLogService`'s explicit-methods convention).
15. `dependencies.py` — `get_claim_review_request_repository`, `get_claim_review_request_service`.

### `search` module (DIR-001 extension, Decision 8)
16. `schemas.py` — `SearchResultProviderResponse` gains `is_claimed: bool`.
17. `services/search_service.py` — one-line addition populating the new field from `Provider.is_claimed`.

### Config (`backend/app/core/config.py`)
18. `GOOGLE_PLACES_API_KEY: str | None = None` (Decision 10).
19. `CLAIM_SEARCH_MAX_PAGE_SIZE: int = 20` (small, bounded — a claim-search result set is expected to be tiny).

### Scripts
20. `backend/scripts/import_google_places.py` (Decision 1) — CLI entry point; constructs `ProviderService`/
    `HttpxGooglePlacesClient` directly (script-level wiring, mirroring `seed_roles.py`'s direct-construction
    style rather than FastAPI's DI container, since there's no request scope here); for each fetched place: skip
    if missing required fields (Decision 3), else look up by `google_place_id`
    (`ProviderRepository.get_by_google_place_id`) → create (`create_google_seeded_provider` + a matching
    `verification_records` row, Decision 2) or backfill (`backfill_google_seeded_provider`, Decision 4's policy).

### API wiring
21. `backend/app/api/v1/api.py` — mount `claim_router` (prefix `/claims`), `admin_claim_router` (prefix
    `/admin/claims`).
22. `backend/tests/conftest.py` — register `ClaimReviewRequest` for `Base.metadata.create_all()` (new ORM model).

### Exceptions
23. `ClaimTargetNotFoundError` (404), `ClaimPublicNumberUnavailableError` (409 — AC6's "unusable" case),
    `ClaimAlreadyClaimedError` (409, reuses `ProviderAlreadyExistsError`'s pattern but distinct message),
    `ClaimReviewRequestNotFoundError` (404).

### Tests
24. `backend/tests/modules/provider/test_provider_service_claim.py` — `create_google_seeded_provider` sets
    exactly `listing_source=google_seeded_unclaimed`/`is_claimed=false`/populated `google_place_id` (AC1), never
    `self_registered`; a companion `service_areas` row exists (Decision 4); `backfill_google_seeded_provider`'s
    field-write policy for both `is_claimed=False` (full overwrite) and `is_claimed=True` (backfill-only: an
    owner-edited non-empty field survives a re-sync with different fresh Google data; a still-empty field gets
    backfilled) — directly covers AC7.
25. `backend/tests/modules/provider/test_claim_service.py`:
    - **AC4, and directly satisfying AC8's first requirement**: `request_otp` calls `OtpService.request_otp` with
      the **provider's own** `phone_country_code`/`phone_number` — verified via a spy/fake `OtpService`,
      asserting the number passed is never influenced by any caller-supplied value (there is no such parameter to
      begin with, but the test still asserts the exact number used matches the fixture provider's stored number,
      not some other value); a provider with `phone_number=None` raises `ClaimPublicNumberUnavailableError`
      without ever calling `OtpService` at all.
    - **AC5**: successful `verify_otp` sets `is_claimed=True`, `user_id`, `claimed_at`; resets
      `verification_status=pending`/`is_discoverable=false` in the same call (Decision 2/6); grants
      `ROLE_PROVIDER`; a second claim attempt against the same now-claimed provider raises a conflict.
    - **AC6, directly satisfying AC8's second requirement**: `verify_otp` raising `InvalidOtpError`/
      `OtpLockedError` from the underlying `OtpService` does **not** silently finalize a claim; a subsequent
      `request_admin_review` call creates a `claim_review_requests` row with `status=open`,
      `reason=otp_failed`; a provider with no public number, calling `request_admin_review` with
      `reason=no_public_number` directly (skipping the OTP step entirely, since it was never attempted), also
      creates a correctly-reasoned row.
    - One-Provider-per-Account enforcement: a claimant who already owns a Provider is rejected before any write.
26. `backend/tests/modules/administration/test_claim_review_request_service.py` — `create`/`list_open`/`resolve`
    basic CRUD-shaped coverage.
27. `backend/tests/modules/provider/test_admin_claim_service.py` — `approve_review_request` finalizes the claim
    identically to the OTP-success path (same assertions as item 25's AC5 coverage, proving the shared
    `_finalize_claim` helper is genuinely shared, not duplicated); `reject_review_request` leaves the provider
    unclaimed.
28. `backend/tests/modules/provider/test_claim_api.py` / `test_admin_claim_api.py` — full HTTP round trips:
    auth/role gating on every route; `GET /claims/search` returns only `google_seeded_unclaimed`/`is_claimed=false`
    rows, matching by name/address substring (AC3); empty result set for a non-matching query.
29. `backend/tests/modules/search/test_search_service.py` (DIR-001 extension) — `is_claimed` appears correctly
    in `GET /search/providers` results for both a claimed and an unclaimed fixture provider (AC2's backend half).
30. `backend/tests/modules/provider/test_google_places_import_script.py` — using `FakeGooglePlacesClient`: a
    fresh import creates providers per Decision 2/3/4; re-running the same script against unchanged fake data is
    idempotent (no duplicate rows, matched by `google_place_id`); a place missing a required field (Decision 3)
    is skipped, not imported.

---

## Mobile — Proposed Changes

### `features/search` (DIR-001 extension, Decision 8)
31. `domain/models/search_result_provider.dart` — add `isClaimed: bool`.
32. `presentation/widgets/provider_search_card.dart` — renders the full-width Warning-color (`#F59E0B`) banner
    ("Unclaimed — Is this your business? Claim it") when `isClaimed == false`, per `16_UX_GUIDELINES.md`'s locked
    copy/design exactly; inline CTA navigates to the new Claim OTP screen for that `providerId`.

### New feature: `mobile/lib/features/claim/`
33. `domain/models/claim_search_result.dart`, `domain/models/claim_result.dart`.
34. `data/claim_repository.dart` — `searchUnclaimed(query, page, pageSize)`, `requestOtp(providerId)`,
    `verifyOtp(providerId, code)`, `requestAdminReview(providerId, reason)`.
35. `presentation/screens/claim_search_screen.dart` (new, `S-21`, AC3) — search field, result list (business
    name, address, masked phone), "Select listing" → navigates to Claim OTP screen with the chosen `providerId`.
36. `presentation/screens/claim_otp_screen.dart` (new, `S-22`, AC4/AC5/AC6) — "Code sent to the number on file"
    copy (never displaying the number itself, matching AC4's spirit — the claimant is proving they already have
    that number, not being told what it is), code input, resend timer (mirrors `S-04`'s existing OTP entry
    pattern), and an always-visible "This isn't working" link (matches `S-22`'s own literal spec) that opens a
    small reason-selection sheet ("I didn't receive a code" / "This isn't my business's number") → calls
    `requestAdminReview` → shows a plain-language "We've flagged this for manual review" confirmation state.
37. `state/claim_search_controller.dart`, `state/claim_otp_controller.dart` (Riverpod, no business logic in
    widgets).
38. `core/routing/app_routes.dart` — new routes for both screens.

### Entry points
39. `features/home/presentation/screens/home_placeholder_screen.dart` or `S-15` (List Your Business Intro,
    `features/provider/`) — add a secondary "Already listed on Google? Claim your business" action opening
    `claim_search_screen.dart` directly (AC3's "find their business" journey, independent of already having
    spotted the card in search results).

### Tests
40. `mobile/test/features/search/provider_search_card_test.dart` — banner renders only when `isClaimed == false`,
    with the exact locked copy, never for a claimed provider (AC2).
41. `mobile/test/features/claim/claim_search_screen_test.dart` — result list renders from a fake repository;
    "Select listing" navigates correctly.
42. `mobile/test/features/claim/claim_otp_screen_test.dart` — the "This isn't working" link is always visible
    (AC6); tapping it and submitting a reason calls the fake repository's `requestAdminReview` and shows the
    confirmation state; a successful `verifyOtp` navigates to a success state.
43. `mobile/test/features/claim/fakes/fake_claim_repository.dart` (new, mirrors the existing fake-repository
    pattern).

---

## Explicitly Out of Scope (do not implement in this story)

- Any resolution of the underlying Google Maps Platform ToS / UAE PDPL legal question (`13_OPEN_DECISIONS.md`
  item 3 stays Open) — this story builds exactly what the CTO's risk-acceptance decision describes; it is not
  this Plan's place to substitute a lower-risk design that was already explicitly considered and declined.
  Attribution/branding requirements Google's terms may impose on displaying Place data ("Powered by Google" etc.)
  are not covered by any of the 8 ACs and are not added here as unrequested scope.
- The future fetch-verify-then-trust improvement `13_OPEN_DECISIONS.md` item 3 names as a later-stage direction
  — explicitly deferred, not scheduled.
- Building `S-09` (Provider Profile screen) — doesn't exist yet, out of DIR-001's scope and this story's scope
  alike (Decision 8).
- Any new scheduler/cron/Celery infrastructure to trigger re-syncs automatically (Decision 1) — the script is
  built idempotent and ready to be scheduled by a future story or an external ops mechanism, not self-triggering.
- The real Category taxonomy domain — the import job's category label is the same free-text, best-effort
  mechanism DIR-001/PRO-002 already established as this codebase's interim posture (`13_OPEN_DECISIONS.md`
  item 1, still Open).
- Reconciling `provider_category_labels` into the real `category.provider_categories` table — a separately
  deferred, unrelated follow-up (item 1).
- Any admin dashboard UI for the new claim-review queue — `admin_claim_api.py` is backend-only, per VER-002's own
  established precedent for "admin does something, no UI yet."
- Freelancer-subtype claiming of any kind (Decision 3).
- PostgreSQL Full Text Search (Decision 5) — substring `ILIKE` is sufficient for this story's bounded use case.
- Editing an unclaimed listing's data before it is claimed — already correctly impossible today via
  `get_by_user_id` scoping (Verified Current State); this story does not add any new pre-claim edit surface.
- Payments, quotes, or any transactional state for the claim itself — the claim flow only ever changes
  `providers`/`verification_records`/`claim_review_requests` state, nothing resembling a billing event.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

**Genuinely blocked pending explicit CTO/user confirmation before backend implementation starts:** none of the
two "obvious-looking" open questions actually block this Plan — the legal/risk posture (item 3) and the
unclaimed-listing visual design (item 4) are both already decided and documented, and are not re-raised here.
The one item worth a light confirmation, flagged for completeness rather than as a hard blocker (every other
decision in this Plan proceeds unaffected either way): **Decision 9's new `claim_review_requests` table is
genuinely new schema not previously specified anywhere in `04_DATABASE.md`** (unlike every column this story
otherwise touches, which was pre-designed for this exact story). It is built by direct analogy to
`unmatched_query_reports`'s already-approved shape, so this Plan proceeds with it as specified — flagged here
only so the tech-lead updates `04_DATABASE.md`'s Administration Domain section at story close (per the
Documentation Rule) rather than this being a silent, undocumented schema addition.

1. **backend** — Everything in Backend Proposed Changes (items 1–30). Build order matters: (a) the
   `claim_review_requests` migration + `administration` module additions first (items 1, 12–15) since `provider`
   depends on them; (b) `provider` module additions (items 2–11, 20, 23) next; (c) the `search` module's one-field
   extension (items 16–17) last, since it's the smallest, most isolated change. **Read Decision 2 and Decision 6
   in full before starting** — the exact `verification_status`/`is_discoverable` state transitions (import-time
   synthetic approval, claim-time reset to pending) are the parts of this story most likely to be gotten subtly
   wrong, and both the `chk_providers_discoverable_requires_approved` DB constraint and AC5's literal ordering
   will surface an error immediately if either transition is written backwards.
2. **frontend** — Mobile items 31–43, once the backend endpoints exist (or in parallel against a fake repository
   per the existing pattern). Particular attention to Decision 8 (the banner is server-driven off one boolean,
   not inferred client-side) and `S-22`'s "this isn't working" link being always-visible, not conditionally
   shown only after repeated OTP failures (matches the literal screen spec).
3. **tester** — Verify all 8 ACs individually (mapping below). Particular attention to: AC1 (read the actual
   import job's write, confirm `listing_source`/`is_claimed`/`google_place_id` are exactly as specified, never
   `self_registered` under any code path); AC4 (confirm, by reading `ClaimService.request_otp`'s actual
   implementation, that the phone number passed to `OtpService` is structurally always the provider's own stored
   number — there is no request parameter through which a different number could ever reach it); AC7 (the
   backfill-only-when-claimed test needs to genuinely prove a non-empty field survives a re-sync with materially
   different fresh Google data, not merely that the field wasn't touched because the fake data happened to match).
4. **architect** — Review Decision 2 (the synthetic `approved`/`is_discoverable=true` import-time state, and its
   reset at claim) against `03_DOMAIN_MODEL.md`'s Provider business rules and the `chk_providers_discoverable_
   requires_approved` constraint's intent; Decision 7 (module placement, both routers inside `provider`) against
   `02_ARCHITECTURE.md`'s explicit assignment and the "modules communicate through services only" rule for the
   new `provider → administration` edge (Decision 9); Decision 9 (the new `claim_review_requests` table) as a
   genuinely new schema addition, confirming it belongs in `administration` per the existing `unmatched_query_
   reports` precedent; Decision 10 (swappable `GooglePlacesClient` Protocol) against ADR-017/ADR-018's precedent
   for consistency.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decision 2
   (import-time synthetic verification state), Decision 6 (claim finalization/one-Provider-per-Account
   enforcement), Decision 9 (new `claim_review_requests` table + admin-API-only pattern), and Decision 10
   (`GooglePlacesClient` Protocol) as new ADRs (next available: **ADR-029** onward — tech-lead finalizes exact
   numbering/grouping at story close); update `04_DATABASE.md` (add the Administration Domain's
   `claim_review_requests` table; confirm the Provider Domain section's existing columns as "now consumed by
   CLM-001," per its own established "shipped exactly per spec" changelog convention); update
   `03_DOMAIN_MODEL.md`/`13_OPEN_DECISIONS.md` if needed (item 3 stays Open, unchanged; note `CLM-001` as
   implemented against its risk-acceptance decision).

---

## Verification Plan (mapped to the 8 ACs)

| AC | Verified by |
|---|---|
| 1 | Unit test on `create_google_seeded_provider` asserts the exact three fields (`listing_source`, `is_claimed`, `google_place_id`) on every created row; a repository-level assertion that no code path in this story ever writes `listing_source=self_registered`; the import-script test (item 30) confirms this end-to-end against fake Google data. |
| 2 | Backend: `SearchResultProviderResponse.is_claimed` present and correct for both claimed/unclaimed fixtures (test 29). Mobile: widget test (40) confirms the full-width Warning-color banner with the exact locked copy renders only when `isClaimed == false`, never a small/easy-to-miss badge (visually, the banner occupies the card's full width per the widget's own layout, reviewed by `architect`/`tester` against `16_UX_GUIDELINES.md`'s literal description). |
| 3 | `GET /claims/search` integration test (28) confirms substring name/address matching, scoped strictly to `listing_source=google_seeded_unclaimed AND is_claimed=false` (a self-registered or already-claimed provider matching the same query text never appears); mobile widget test (41) confirms the search screen renders results and "Select listing" navigates correctly. |
| 4 | Unit test (25) directly asserts, via a spy `OtpService`, that the phone number used is always the target provider's own stored `phone_country_code`/`phone_number` — never any client-supplied value (structurally impossible, since `request_otp`/its endpoint accept no phone-number parameter at all); a provider with no public number never reaches `OtpService` and instead raises `ClaimPublicNumberUnavailableError`. |
| 5 | Unit test (25) confirms `is_claimed=True`, `user_id`, `claimed_at` set atomically with `verification_status=pending`/`is_discoverable=false` and `ROLE_PROVIDER` granted, all in one call; a follow-up integration test confirms the claimed provider can immediately call the existing, unmodified `POST /providers/me/verification/submit` and reach the existing admin approve/reject queue — proving "the same Verification gate," not merely a claim assertion in isolation. |
| 6 | Unit test (25) confirms an OTP failure never finalizes a claim; `request_admin_review` creates a correctly-reasoned `claim_review_requests` row for both the `otp_failed` and `no_public_number` cases; mobile widget test (42) confirms the "this isn't working" link is always visible on the OTP screen (not conditionally shown) and correctly triggers the fallback. |
| 7 | Unit test (24) directly proves the field-write policy: an unclaimed provider's re-sync fully overwrites a changed field; a claimed provider's re-sync leaves an existing non-empty field untouched even when fresh Google data differs, while still backfilling a field that is genuinely still empty. |
| 8 | Tests 25/27/28 collectively satisfy this literally: OTP-goes-only-to-public-number (AC4's own test, reused as AC8's first requirement) and the admin-fallback-on-OTP-failure path (AC6's own tests, reused as AC8's second requirement) — both already covered by items above, cross-referenced here so `tester` confirms neither was accidentally skipped as "someone else's AC to cover." |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md` (Provider module's explicit "Claim flow" responsibility — Decision 7)
- `docs/AI/03_DOMAIN_MODEL.md` (Provider domain, line 112 — "starts as Unclaimed and is discoverable," Decision 2)
- `docs/AI/04_DATABASE.md` (Provider Domain — all columns this story needs already exist; Section 14 — the
  `listing_source`/`google_place_id` bulk-deletion mitigation; `unmatched_query_reports` — Decision 9's precedent)
- `docs/AI/09_DECISIONS.md` (ADR-016 — `provider → identity` cross-module shape this story's `provider →
  administration`/`provider → identity` edges mirror; ADR-017/ADR-018 — swappable Protocol precedent, Decision
  10; ADR-023 — ownerless `require_role(ROLE_ADMIN)` shape, Decision 9's admin API)
- `docs/AI/11_MVP_SCOPE.md` (Claim an unclaimed listing is explicitly in-scope Provider-dashboard functionality)
- `docs/AI/13_OPEN_DECISIONS.md` (item 3 — Google Places legal risk-acceptance, item 4 — Unclaimed Listing UX,
  both already resolved as documented above and not re-litigated by this Plan)
- `docs/AI/14_USER_FLOWS.md` (Flow 3 — Claim-Your-Listing, the intended journey this Plan implements)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-08, S-21, S-22)
- `docs/AI/16_UX_GUIDELINES.md` (Trust & Verification UX Patterns — the locked banner design, Decision 8)
- `.agents/skills/third-party-integrations/oauth-and-otp.md` / `google-places-import.md` (the exact rules this
  Plan implements: reuse one OTP table, never a client-typed number, no silent overwrites once claimed)
- `docs/implementation/plans/Plan_S05_VER-001.md` / `Plan_S05_VER-002.md` (OTP/verification/admin-API-only
  precedents this Plan reuses directly, not reinvents)
- `docs/implementation/plans/Plan_S06_DIR-001.md` (the `search` module this story extends by one field, and the
  explicit "does not touch `CLM-001`" boundary this Plan now crosses, by design, from the `CLM-001` side)
- `docs/implementation/plans/Plan_S04_PRO-001.md` / `Plan_S04_PRO-002.md` (the Provider aggregate,
  `_generate_unique_slug`, `service_areas` sync, `provider_category_labels` mechanisms this story reuses)

---

**End of Document**
