# Plan for Story CON-001 — Contact a Matched Provider Directly

**Sprint:** 08 (Matching / Contact) | **Epic:** ML8-EP02 | **Milestone:** ML8 | **Phase:** PH2 | **Priority:**
Critical | **Depends On:** MAT-001 (done, Sprint 8)

---

## Story (verbatim, `Project_Tracker.xlsx`, `CON-001` row — relayed by the orchestrator this session)

"As a customer, I want to see a matched provider's phone number immediately when I tap Contact, with no quote or
approval step in between, so that reaching out feels as simple as getting a number from a friend. This story
implements the platform's growth-first, direct-contact model and its most safety-critical rule: the self-dealing
guard. Because one Account may hold both Customer and Provider roles, a Contact View must be rejected outright if
the requesting Customer's Account is the same Account that owns the target Provider — otherwise a provider could
inflate their own lead/contact/review numbers by contacting themselves. Scope boundary: does not include the
Outcome Tag prompt or reviews (REV-001/002) — this story ends at the phone number being shown."

## Acceptance Criteria (verbatim, 8 items)

1. `contact_views` table exists via migration, referencing the customer, the provider, and optionally the
   originating search request.
2. Tapping Contact on a matched provider immediately shows the phone number and Call/WhatsApp buttons in a bottom
   sheet — no quote request, approval wait, or in-app messaging step exists anywhere in this flow.
3. A Contact View is rejected if the requesting Customer Account is the same Account that owns the target
   Provider — this is enforced at the point of Contact View creation, not just documented as a rule.
4. The rejection in the self-dealing case is tested explicitly with an automated test asserting the Contact View
   row is never created.
5. Provider Profile screen shows rating together with review count (never rating alone), a Verified badge (or
   Unclaimed label) as applicable, and hours/service-area information.
6. The Contact Reveal sheet includes a brief note that contact happens outside the app.
7. Every Contact View creation is a candidate trigger for provider-lead notifications (wired fully in ENG-001,
   but the event itself must be emitted here).
8. Automated tests cover the happy path (successful contact reveal) and the self-dealing rejection as separate,
   explicit test cases.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **`contact_views` is already fully spec'd in `04_DATABASE.md`** (Contact Domain section, `contact` schema) —
  `customer_id` (FK → `customer.customer_profiles.id`, not null), `provider_id` (FK → `provider.providers.id`,
  not null), `search_request_id` (FK → `search.search_requests.id`, nullable), `viewed_at` (default `now()`),
  plus the three named indexes (`idx_contact_views_customer_id`, `idx_contact_views_provider_id`,
  `idx_contact_views_viewed_at`). No deviation from this spec is needed — this story builds it exactly as
  documented. The spec's own text already names the self-dealing guard's exact mechanism: reject if
  `customer_profiles.user_id` (via `customer_id`) equals `providers.user_id` (via `provider_id`) — enforced at
  the service layer, not a DB constraint, since it requires joining across two tables through `identity.users`.
- **`03_DOMAIN_MODEL.md` v0.8.1 already states the dual-role business rule in full**: "An Account may hold both
  the Customer and Provider roles simultaneously... this is one Account with two optional profiles, not two
  separate accounts," and names the resulting Contact View self-dealing restriction explicitly. Nothing here is
  a new product decision — it is already-approved domain law this story is the first to actually enforce in
  code.
- **How "Account" is actually modeled, confirmed directly against the code**: there is no separate "Account"
  table. `identity.users` is the Account. `customer.customer_profiles.user_id` (unique, not null,
  `CustomerProfileRepository.get_by_user_id`) and `provider.providers.user_id` (unique-when-set, nullable for a
  still-unclaimed Google-seeded listing) both point at the same `identity.users.id`. The exact
  "same Account owns both" comparison this story needs is `providers.user_id == identity.users.id` for the
  currently-authenticated caller (`CurrentUser.id`, `app/api/dependencies.py`) — since `customer_profile` is
  resolved via `CustomerProfileRepository.get_by_user_id(current_user.id)` in the first place,
  `customer_profile.user_id` is definitionally equal to `current_user.id`; comparing `provider.user_id ==
  current_user.id` directly is the same comparison the spec describes, without a redundant re-read of the
  just-fetched customer row.
- **A directly-precedented pattern already exists for "does this account already own a Provider row" checks**:
  `ClaimService._finalize_claim` (CLM-001) already does `provider_repository.get_by_user_id(user_id)` and
  compares against the caller's `user_id` to enforce the one-Provider-per-account rule. This story's self-dealing
  guard is the same shape of check (compare a caller's `user_id` against a `Provider.user_id`), applied to a
  different direction (a Customer contacting, not a claim) — mirrored, not reinvented.
- **No customer-facing "Provider Profile" screen exists anywhere in the codebase today — confirmed, not
  assumed.** `mobile/lib/features/search/presentation/screens/search_results_screen.dart`'s `_onCardTap` and
  `mobile/lib/features/conversation/presentation/screens/ai_conversation_screen.dart`'s
  `_ResolvedResultsView._onResultTap` both currently do nothing but show a
  `providerProfileComingSoonMessage` snackbar, with an explicit code comment: "S-09 (the real Provider Profile
  screen) doesn't exist yet." `15_SCREEN_INVENTORY.md` fully specs S-09 (photo/portfolio carousel, name,
  category, rating, distance, hours/availability, description, Verified Visit badge if present, sticky Contact
  CTA) and the Contact Reveal sheet as a separate sheet entry, both already product-approved. **This story must
  build S-09 and the Contact Reveal sheet as real, new mobile screens** — this is genuinely new frontend work,
  unlike MAT-001's backend-only scope.
- **No `GET /providers/{id}` customer-facing detail endpoint exists.** `backend/app/modules/provider/api.py`
  only exposes `/me`, `/me/portfolio`, `/me/availability` — all owner-scoped. A new, separate, customer-facing
  read endpoint is needed for the Provider Profile screen's data (Decision 2).
- **The Verified/Unclaimed badge cannot be a simple `verification_status == approved` check** — confirmed
  directly in `ProviderService.create_google_seeded_provider`: a still-unclaimed, Google-seeded listing is
  written with `verification_status=APPROVED`/`is_discoverable=True` **and** `is_claimed=False`, purely so it is
  searchable (CLM-001, Decision 2). Treating `verification_status==approved` alone as "Verified" would render a
  contradictory "Verified" badge on a listing nobody has claimed yet. `is_claimed` must be checked first
  (Decision 3).
- **The Notification module (VER-002) already has exactly the "narrow, passive record" shape AC7 needs.**
  `notification.notifications` (`backend/app/modules/notification/models.py`) is a plain, honest "a notification
  of this type was generated for this user" row with no delivery mechanism — `NotificationService.
  notify_verification_status_change` is the one existing writer, called synchronously from
  `AdminVerificationService._notify` on the same request-scoped session/transaction. This is directly reusable:
  a new `notify_new_contact_view` method on the same `NotificationService`, called from the new `ContactService`
  the same way, satisfies AC7's "the event itself must be emitted here, full delivery is ENG-001's job" scope
  boundary without inventing a new mechanism.
- **`url_launcher` (or an equivalent) is not a dependency of this codebase today** — confirmed against
  `mobile/pubspec.yaml`. AC2's Call/WhatsApp buttons require launching a `tel:`/`https://wa.me/...` URL from
  Flutter, which has no built-in SDK mechanism — a plugin is genuinely required, the same shape of gap
  `google_maps_flutter`/`geolocator`/`geocoding` (CUS-002), `image_picker` (PRO-002), and `file_picker`
  (VER-001) each already were, each explicitly flagged and user-approved before use. Flagged in Open Questions
  below — not assumed pre-approved.
- **`RankedProviderResultsList`'s `onTap` callback already passes the tapped result's id** — both call sites
  (`SearchResultsScreen`, `AiConversationScreen`) currently discard it (`onTap: (_) => _onCardTap(context)`).
  Wiring real navigation is a small, contained change at both call sites, not a widget redesign.
- **`AvailabilityService.get_my_availability(user_id)` is owner-scoped (looks up the Provider by the caller's
  own `user_id`)** — not directly reusable for an arbitrary target `provider_id` a customer is viewing. A small
  new method is needed (Decision 6).
- **No migration or module currently exists for `outcome_tags`, `visit_verifications`, or `reviews`** — all
  three are fully spec'd in `04_DATABASE.md` but explicitly out of this story's scope (the story's own stated
  boundary: "does not include the Outcome Tag prompt or reviews"). This story's migration creates the `contact`
  schema and `contact_views` table only — nothing else from that section of `04_DATABASE.md`.
- Current Alembic migration head: `f3a1c9d47b02` (`search_domain_and_manual_match_...`, MAT-001 added no new
  migration). This story adds the first migration since then.

---

## Architecture Decisions

### Decision 1 — New `contact` module; self-dealing guard enforced by direct `user_id` comparison inside `ContactService`, not a DB constraint

**The problem:** AC3/AC4 require the self-dealing rule to be enforced at the point of write, not just documented,
and tested with a real assertion that no row is ever created.

**Chosen:** a new, standalone `backend/app/modules/contact/` module (mirrors `search`'s and `verification`'s own
module shape: `models.py`, `repositories/contact_view_repository.py`, `services/contact_service.py`,
`schemas.py`, `api.py`, `dependencies.py`). `ContactService.create_contact_view(current_user_id, *, provider_id,
search_request_id)`:

1. Resolves the caller's `customer_profiles` row via `CustomerProfileRepository.get_by_user_id(current_user_id)`
   (every authenticated caller already holds `ROLE_CUSTOMER` from registration onward, per DIR-001/MAT-001's own
   established assumption — this lookup is expected to always succeed in practice, but is still checked
   defensively).
2. Resolves the target `Provider` via `ProviderRepository.get_by_id(provider_id)` — 404
   (`ProviderNotFoundError`, reused) if missing or soft-deleted (`is_active=False`).
3. **Self-dealing guard**: if `provider.user_id is not None and provider.user_id == current_user_id`, raises a
   new `SelfDealingContactError` (403) **before any row is written** — this is the literal AC3/AC4 requirement.
   `provider.user_id is None` (a still-unclaimed Google-seeded listing) can never self-deal by construction —
   there is no owning Account yet — so the guard is skipped, and Contact View creation proceeds normally (an
   unclaimed listing is fully contactable today, mirroring CLM-001's own existing design: `ProviderResultCard`
   already lets a customer tap through to an unclaimed listing's card unimpeded).
4. If `search_request_id` is supplied, validates it belongs to the *same* customer (Decision 4) before use.
5. Creates the `contact_views` row (no dedup — Decision 5).
6. If `provider.user_id is not None`, emits a Notification (Decision 3). Skipped for an unclaimed listing —
   there is no account to notify.
7. Returns the Provider's `phone_country_code`/`phone_number`/`whatsapp_number`/`display_name` plus the new
   `contact_views.id`, for the API layer to build the Contact Reveal response (AC2).

**Alternatives considered and rejected:**
- **A database `CHECK` constraint or trigger.** Rejected — `04_DATABASE.md`'s own spec text already states this
  explicitly: the comparison spans two tables (`customer_profiles`, `providers`) joined through a third
  (`identity.users`), which a single-table `CHECK` cannot express, and a cross-table trigger would hide a
  security-critical business rule inside opaque DB logic this codebase's established pattern (every other
  business rule enforced in a `*Service`, e.g. `ClaimService`, `AdminVerificationService`) avoids.
- **Enforcing the guard only in the mobile client (e.g. hiding the Contact button on your own listing).**
  Rejected outright — this is a client-side check an attacker can trivially bypass by calling the API directly;
  AC3's literal wording ("enforced at the point of Contact View creation, not just documented as a rule") rules
  this out as the sole mechanism. (The mobile UI should still not surgically expose a "Contact yourself" button
  where avoidable, but that is a UX nicety, not the enforcement boundary — the backend guard is what AC4's test
  actually exercises.)
- **Folding Contact View creation into the existing `provider` or `search` module instead of a new `contact`
  module.** Rejected — `contact_views` is its own aggregate root per `04_DATABASE.md`'s own schema
  (`contact.contact_views`, a distinct Postgres schema from both `provider`/`search`), and is the anchor future
  `outcome_tags`/`visit_verifications`/`reviews` domains will attach to (per `03_DOMAIN_MODEL.md`) — giving it
  its own module now avoids a later, disruptive extraction once those stories arrive, mirroring how `search`
  was given its own module in AI-002 rather than folded into `conversation`.

### Decision 2 — New customer-facing `GET /providers/{provider_id}` endpoint, in a sibling router registered after the existing `/me`-scoped router

**The problem:** the Provider Profile screen (AC5) needs a real detail endpoint; none exists. The existing
`provider_router` (`provider/api.py`) is entirely `/me`-scoped (owner-only) and gated implicitly by "the caller's
own row" semantics — a public, customer-facing, arbitrary-`provider_id` read is a different concern with
different authorization (any `ROLE_CUSTOMER` caller, any target provider) and should not be interleaved into the
owner-only file.

**Chosen:** a new sibling file `backend/app/modules/provider/public_api.py` (mirrors this module's own existing
`claim_api.py`/`admin_claim_api.py` sibling-router convention), one route: `GET /{provider_id}`, gated by
`require_role(ROLE_CUSTOMER)`. Registered in `app/api/v1/api.py` as a **second**
`v1_router.include_router(provider_public_router, prefix="/providers")` call, placed **after** the existing
`v1_router.include_router(provider_router, prefix="/providers")` line — Starlette matches routes in registration
order, so `/me`/`/me/portfolio`/`/me/availability` (already registered first) continue to match their literal
paths before the new `/{provider_id}` path-parameter route is ever reached. A new `ProviderService.
get_for_public_profile(provider_id)` method does the lookup, raising `ProviderNotFoundError` for a missing or
soft-deleted (`is_active=False`) row — deliberately **not** requiring `is_discoverable=True` (Decision 7).
Returns a new `PublicProviderProfileResponse`: `id`, `display_name`, `provider_type`, `category_labels`,
`description`, `primary_photo_url`, `average_rating`, `review_count`, `is_claimed`, `verification_status`,
weekly hours (Decision 6), and one subtype-specific service-area field (`delivery_radius_meters` for Business,
`service_radius_meters` for Freelancer) plus `city`/`region` for Business — reusing `ProviderService.
get_subtype_profiles`/`get_category_labels` unchanged, the same helpers `/me`'s own `_to_response` already
calls. **Deliberately does not include `phone_number`/`whatsapp_number`** — those are revealed only via the
Contact Reveal flow (AC2), never on the profile screen itself, so a customer cannot get the number without a
real Contact View being recorded.

**Alternatives considered and rejected:**
- **Extending `SearchResultProviderResponse`/`MatchedProviderResponse` with the extra profile fields instead of
  a new endpoint**, so the mobile client could reuse data already fetched in the results list. Rejected — those
  two schemas are paginated list-row shapes (DIR-001/AI-002), and adding hours/service-area/badge fields to
  every row of every search result would bloat a hot, frequently-paginated response for data only needed once a
  customer taps into one specific provider. A dedicated detail fetch on navigation is the standard, already
  precedented shape in this codebase (e.g. `GET /providers/me` itself is a dedicated fetch, not inlined into a
  list).
- **Adding the new route directly into the existing `provider_router` object in `api.py`, ordered after the
  `/me...` routes in the same file.** Considered and viable, but a separate file/router (mirroring
  `claim_api.py`) was chosen for clearer separation of "self-service, owner-only" vs. "public, customer-facing"
  concerns, consistent with this module's own existing convention of splitting `claim_api.py` (customer-facing)
  from `admin_claim_api.py` (admin-facing) rather than one large file.

### Decision 3 — Notification emission mirrors VER-002's `NotificationService.notify_verification_status_change` exactly

**The problem:** AC7 requires "every Contact View creation is a candidate trigger for provider-lead
notifications... the event itself must be emitted here" — without building ENG-001's actual delivery mechanism.

**Chosen:** add `NotificationService.notify_new_contact_view(*, user_id, contact_view_id)` — same signature
shape, same hardcoded plain-language copy pattern, same `type`/`related_entity_type`/`related_entity_id`
convention as the existing `notify_verification_status_change`. Called once, synchronously, from
`ContactService.create_contact_view` on the same request-scoped session (flush only, one `db.commit()` at the
API layer — mirrors `AdminVerificationService`'s transaction-boundary discipline exactly). Only called when
`provider.user_id is not None` (Decision 1, step 6).

**Alternatives considered and rejected:**
- **Building any part of ENG-001's real delivery mechanism (push/SMS/email) now.** Rejected outright — explicitly
  named in the story as "wired fully in ENG-001." This story's job is only to make the in-app record exist so a
  provider's own dashboard/notification bell (already reading `notification.notifications`, per VER-002) has
  something to show, and so ENG-001 has a real row to build delivery on top of later.
- **A new, contact-specific notification table.** Rejected — `notification.notifications`'s existing, generic
  shape (`type`, `title`, `body`, `related_entity_type`/`related_entity_id`) already accommodates a new `type`
  value with zero schema change, exactly as designed.

### Decision 4 — `search_request_id`, if supplied, must belong to the calling customer; otherwise rejected, never silently dropped or trusted blindly

**The problem:** `contact_views.search_request_id` is an optional FK to `search.search_requests`. A customer
calling `POST /contact-views` could supply an arbitrary UUID for this field, including another customer's
`search_request_id`.

**Chosen:** if `search_request_id` is provided, `ContactService` fetches it via `SearchRequestRepository.
get_by_id` and rejects (reusing the existing `SearchRequestNotFoundError`, 404) if it does not exist or its
`customer_id` does not match the calling customer's own `customer_profiles.id` — mirrors ADR-015's "always
404, never 403, for another user's resource" convention (`{id}`-addressable collection pattern) rather than
leaking existence via a 403. If omitted entirely (e.g. a customer reached the Provider Profile screen via the
non-AI structured search path, which creates no `search_requests` row at all — confirmed in MAT-001's Verified
Current State), the column is simply left `NULL` — the honest, already-precedented "nullable column, no
fabrication" posture this codebase uses throughout (`00_PROJECT_CONTEXT.md` §3).

**Alternatives considered and rejected:**
- **Trust the client-supplied `search_request_id` unconditionally.** Rejected — this would let one customer's
  request pollute another customer's search-request-linked analytics/audit trail with no server-side check at
  all, a real (if low-severity) integrity gap for a field this codebase otherwise treats carefully everywhere
  else ownership is checked.
- **Silently drop an invalid/mismatched `search_request_id` to `NULL` instead of rejecting the request.**
  Rejected — silently discarding a client-supplied value that doesn't validate hides a real bug (a stale or
  wrong id from the mobile client) instead of surfacing it; an explicit 404 is more diagnosable and matches this
  codebase's existing "reject, don't silently coerce" posture for a malformed foreign reference elsewhere
  (e.g. `InvalidManualMatchProviderIdsError`).

### Decision 5 — No uniqueness constraint on `(customer_id, provider_id)`; every Contact tap creates a new row

**The problem:** should a customer contacting the same provider twice create two rows, or update/dedupe one?

**Chosen:** no dedup, no unique constraint — every successful call to `POST /contact-views` creates a new row.
`04_DATABASE.md` itself frames `contact_views` as "basis for... provider visibility analytics" — a customer
genuinely re-viewing/re-contacting a provider (e.g. weeks later, for a different job) is a real, separately
meaningful event for that analytics purpose, not a duplicate to collapse.

**Alternatives considered and rejected:**
- **A partial unique index on `(customer_id, provider_id)` (one Contact View per pair, ever).** Rejected — no AC
  or domain-model text asks for this, and it would silently under-count real, repeated visibility/lead events
  that the analytics use case this table exists for explicitly wants to capture.

### Decision 6 — `AvailabilityService` gains a second, arbitrary-target read method; synthesis logic extracted once, not duplicated

**The problem:** `get_my_availability(user_id)` is hard-wired to "the caller's own provider." The new public
detail endpoint needs the same seven-day synthesis for an arbitrary `provider_id` it does not own.

**Chosen:** extract the existing "any weekday without a saved row becomes a closed, not-yet-configured entry"
loop out of `get_my_availability` into a private, provider-id-keyed helper (`_synthesize(provider_id)`), and add
a new public method `get_availability_for_provider(provider_id: uuid.UUID) -> list[WeekdayAvailabilityEntry]`
that calls it directly (no ownership check — the caller has already resolved and authorized viewing this
`provider_id` via `ProviderService.get_for_public_profile`). `get_my_availability(user_id)` is refactored to
resolve the provider via its existing `_get_provider_or_404(user_id)` call and then delegate to the same shared
helper — behavior for the existing owner-facing endpoint is byte-for-byte unchanged.

**Alternatives considered and rejected:**
- **Duplicate the seven-day synthesis loop in a new, separate method.** Rejected outright per `.agents/agents.md`'s
  explicit "never create duplicate code" rule — the synthesis logic is identical in both cases; only how the
  target `Provider` row is resolved differs.

### Decision 7 — The public profile/detail endpoint does not require `is_discoverable=True`

**The problem:** should a customer be able to open a Provider Profile for a provider that has since become
non-discoverable (e.g. verification later rejected)?

**Chosen:** `ProviderService.get_for_public_profile` only requires the row to exist and be `is_active=True`
(not soft-deleted) — it does not additionally require `is_discoverable=True`. No AC or domain-model text
restricts profile viewing/contact eligibility to only-currently-discoverable providers, and a customer who
already has a specific `provider_id` (e.g. from a previous search result, a deep link, or simply re-opening the
Provider Profile screen after search results refreshed) should not hit a confusing 404 purely because the
provider's discoverability flag changed after the fact. `Contact View` creation (Decision 1) uses the same
provider lookup and inherits the same posture.

**Alternatives considered and rejected:**
- **Require `is_discoverable=True`, mirroring the search results' own filter.** Considered, but rejected as an
  unrequested, stricter-than-specified restriction — `is_discoverable` gates *search visibility* per its own
  documented purpose (`04_DATABASE.md`), not contact eligibility for a listing the customer already has a direct
  reference to. Flagged in Open Questions below in case the CTO wants the stricter behavior instead — an easy,
  contained change either way (one boolean check) if the answer differs.

### Decision 8 — Verified/Unclaimed badge precedence: `is_claimed` first, `verification_status` second, else neither

**The problem:** AC5 requires "a Verified badge (or Unclaimed label) as applicable" — but (per Verified Current
State) `is_claimed=False` and `verification_status=APPROVED` can both be true simultaneously for a Google-seeded
listing, so the two fields cannot be checked independently without producing a contradictory result.

**Chosen:** the server returns the two raw booleans/enum (`is_claimed`, `verification_status`) unchanged — the
mobile client (mirrors `ProviderResultCard`'s own existing precedent of computing its unclaimed-banner
visibility client-side off a server-driven boolean, never inferring from other signals) renders exactly one of
three states:
1. `is_claimed == false` → the shared `UnclaimedBanner` widget (Decision 9), regardless of `verification_status`.
2. `is_claimed == true && verification_status == approved` → a new `VerifiedBadge` widget.
3. Otherwise (claimed, but `pending`/`under_review`/`rejected`) → neither badge is shown.

**Alternatives considered and rejected:**
- **Have the backend compute and return a single `trust_badge: "verified" | "unclaimed" | "none"` enum field.**
  Rejected — this codebase's established precedent (`SearchResultProviderResponse.is_claimed`) is to expose the
  raw, honest boolean and let the client render off it, not to pre-compute a display-only enum server-side; a
  new enum here would be the first inconsistent departure from that pattern for no functional gain.

### Decision 9 — Extract `ProviderResultCard`'s private `_UnclaimedBanner` into a shared, public widget reused by the new Provider Profile screen

**The problem:** `16_UX_GUIDELINES.md`'s own resolved pattern explicitly states the full-width Unclaimed banner
applies to **both** the provider card (S-08) and the provider profile (S-09) — but the existing implementation
(`_UnclaimedBanner`) is a private class scoped inside `provider_result_card.dart`.

**Chosen:** extract it to `mobile/lib/shared/widgets/unclaimed_banner.dart` as a public `UnclaimedBanner` widget,
byte-for-byte the same visual implementation (full-width, solid Warning color, chevron, inline CTA callback) —
`ProviderResultCard` is updated to import and use the extracted widget instead of its own private copy (no
visual/behavioral change to S-08's existing card), and the new Provider Profile screen uses the same widget for
its own top-of-screen banner (its CTA navigates to the Claim OTP screen exactly as `SearchResultsScreen._onClaimTap`
already does).

**Alternatives considered and rejected:**
- **Build a second, separate unclaimed-banner widget for the Provider Profile screen.** Rejected per
  `.agents/agents.md`'s "never create duplicate widgets" rule, and directly contrary to `16_UX_GUIDELINES.md`'s own
  explicit instruction that this is the *same* resolved pattern reused across both screens.

### Decision 10 — Self-dealing rejection uses HTTP 403, a new `SelfDealingContactError`

**The problem:** no existing exception class fits "a well-formed request, correctly authenticated, blocked
purely because of who the caller is relative to the target resource."

**Chosen:** a new `SelfDealingContactError(BusinessException)`, `status_code=403`, with a clear, plain-language
message ("You can't contact your own listing."). 403 (Forbidden) was chosen over 409 (Conflict, this codebase's
existing choice for state-timing conflicts like `ClaimAlreadyClaimedError`) because this is not a race or a
timing issue — it is a permanent, identity-based authorization rule: this specific caller may never create this
specific write, regardless of retry timing. No information-leakage concern applies (unlike claim-flow's masked
404s) since the caller already knows they own the target listing.

---

## Backend — Proposed Changes

1. **New Alembic migration** (`contact_domain`, on top of `f3a1c9d47b02`): creates the `contact` Postgres schema
   and `contact_views` table exactly per `04_DATABASE.md`'s spec — full `CommonColumnsMixin` columns
   (soft-delete is the default per `04_DATABASE.md`'s own Soft Delete section, which exempts only
   `audit_logs`/`search_event_log`) plus `customer_id` (FK, not null), `provider_id` (FK, not null),
   `search_request_id` (FK, nullable), `viewed_at` (`TIMESTAMPTZ NOT NULL DEFAULT now()`), and the three named
   indexes.
2. **New module `backend/app/modules/contact/`**:
   - `models.py` — `ContactView(CommonColumnsMixin, Base)`.
   - `repositories/contact_view_repository.py` — thin `BaseRepository` subclass; `create` only (inherited).
   - `services/contact_service.py` — `ContactService.create_contact_view(...)` per Decision 1.
   - `schemas.py` — `CreateContactViewRequest` (`provider_id: uuid.UUID`, `search_request_id: uuid.UUID | None
     = None`), `ContactViewRevealResponse` (`id`, `provider_id`, `provider_display_name`,
     `phone_country_code`, `phone_number`, `whatsapp_number`).
   - `api.py` — `POST /contact-views`, `require_role(ROLE_CUSTOMER)`, 201 on success, documented 403 (self-
     dealing) and 404 (provider or search request not found/not owned) responses.
   - `dependencies.py` — standard DI wiring (`ContactViewRepository`, `CustomerProfileRepository` (reused from
     `customer` module), `ProviderRepository`/`ProviderService` (reused from `provider` module),
     `SearchRequestRepository` (reused from `search` module), `NotificationService` (reused from `notification`
     module), `ContactService`).
3. `backend/app/core/exceptions/exceptions.py` + `__init__.py` — new `SelfDealingContactError` (403, Decision
   10).
4. `backend/app/modules/notification/services/notification_service.py` — new `notify_new_contact_view(*,
   user_id, contact_view_id)` (Decision 3), same hardcoded-copy pattern as `notify_verification_status_change`.
5. `backend/app/modules/provider/services/availability_service.py` — extract shared synthesis helper, add
   `get_availability_for_provider(provider_id)` (Decision 6); `get_my_availability` behavior unchanged.
6. `backend/app/modules/provider/services/provider_service.py` — new `get_for_public_profile(provider_id) ->
   Provider`, raising `ProviderNotFoundError` for missing/inactive (Decision 7).
7. **New file `backend/app/modules/provider/public_api.py`** — `GET /{provider_id}` (Decision 2),
   `require_role(ROLE_CUSTOMER)`, builds `PublicProviderProfileResponse` by reusing `ProviderService.
   get_subtype_profiles`/`get_category_labels` and the new `AvailabilityService.
   get_availability_for_provider`.
8. `backend/app/modules/provider/schemas.py` — new `PublicProviderProfileResponse`,
   `PublicWeeklyAvailabilityResponse` (or reuse the existing `WeekdayAvailabilityResponse` shape directly if
   identical — confirm during implementation; no need to duplicate a schema that's already an exact match).
9. `backend/app/api/v1/api.py` — register `contact_router` at prefix `/contact-views`; register the new
   `provider_public_router` at prefix `/providers`, **after** the existing `provider_router` registration
   (Decision 2's ordering requirement).

### Tests

10. `backend/tests/modules/contact/test_contact_service.py` — **happy path** (creates a row, returns the
    correct phone/whatsapp data, `contact_views` row count increases by exactly one); **self-dealing rejection**
    (AC4: asserts `SelfDealingContactError` is raised **and** directly queries the table to assert row count is
    unchanged — not merely that an exception was thrown); unclaimed-listing contact succeeds with no self-
    dealing rejection and **no** Notification row created; a claimed provider's contact **does** create exactly
    one Notification row addressed to `provider.user_id`; `search_request_id` ownership validation (own request
    accepted, another customer's request rejected with 404, omitted request leaves the column `NULL`).
11. `backend/tests/modules/contact/test_contact_api.py` — full HTTP round trip: 201 happy path, 403 self-
    dealing, 404 provider not found, 404 mismatched `search_request_id`, 401 unauthenticated, 403 wrong role.
12. `backend/tests/modules/provider/test_public_provider_api.py` — `GET /providers/{id}` happy path (rating +
    review_count together, hours, service-area field per subtype); three badge-precedent fixture cases
    (unclaimed → `is_claimed=false`; claimed+approved → `is_claimed=true`/`verification_status=approved`;
    claimed+pending → `is_claimed=true`/`verification_status=pending`, confirming the raw fields returned let the
    client render Decision 8's three states); 404 for a nonexistent/soft-deleted provider; a still-
    non-discoverable-but-active provider is still viewable (Decision 7, explicit regression test for the
    deliberately looser posture).
13. `backend/tests/modules/provider/test_availability_service.py` — extend: new
    `get_availability_for_provider` test (arbitrary target, no ownership check, seven-entry synthesis matches
    `get_my_availability`'s existing behavior for an equivalent fixture).
14. `backend/tests/modules/notification/test_notification_service.py` — extend: `notify_new_contact_view`
    creates the expected row shape (`type`, `related_entity_type`/`id`, plain-language copy).
15. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

**New dependency required — flagged for explicit approval before `frontend` starts (see Open Questions):**
`url_launcher` (the standard, Flutter-team-maintained package for launching `tel:`/`https://wa.me/...` URLs) —
mirrors the exact "new, flagged dependency" precedent already used for `google_maps_flutter`/`geolocator`/
`geocoding`, `image_picker`, and `file_picker`.

1. **New feature `mobile/lib/features/provider_profile/`** (a new sibling feature, not folded into the existing
   owner-facing `features/provider` onboarding/storefront feature, since this is an entirely different concern:
   a customer viewing *someone else's* listing):
   - `domain/models/provider_profile.dart` — parses `GET /providers/{id}`'s response.
   - `domain/models/provider_profile_args.dart` — `{providerId: String, searchRequestId: String?}`, passed via
     `extra` (mirrors `otpEntry`/`addressForm`'s `extra`-required pattern).
   - `domain/models/contact_reveal.dart` — parses `POST /contact-views`'s response.
   - `domain/models/provider_profile_exception.dart` / `contact_exception.dart` — mirrors this codebase's
     existing per-feature exception-mapping convention.
   - `data/provider_profile_repository.dart` — `getProviderProfile(providerId)`, `createContactView(providerId,
     searchRequestId)`.
   - `state/provider_profile_controller.dart` (Riverpod, loads the profile) and
     `state/contact_reveal_controller.dart` (Riverpod, owns the create-contact-view async action's own
     loading/error state, separate from the profile load so the sheet's own in-flight state doesn't couple to
     the screen's).
   - `presentation/screens/provider_profile_screen.dart` (S-09) — name, category, description, primary photo,
     rating+review-count together (never alone, AC5), weekly hours, service-area field, the shared
     `UnclaimedBanner` (Decision 9) or new `VerifiedBadge` (Decision 8) as applicable, sticky bottom Contact CTA.
   - `presentation/widgets/contact_reveal_sheet.dart` — the bottom sheet (`showModalBottomSheet`), per
     `07_UI_GUIDELINES.md`/`DESIGN.md`'s `bottom-sheet` component convention (already named for exactly this use
     case): loading state while the create-call is in flight, then the large phone number, a Call button
     (`tel:`), a WhatsApp button (`https://wa.me/<whatsapp_number>`, only shown if `whatsapp_number` is present),
     and the required "contact happens outside the app" note (AC6, in both `app_en.arb`/`app_ar.arb`).
2. **New shared widget `mobile/lib/shared/widgets/unclaimed_banner.dart`** (Decision 9) — extracted from
   `ProviderResultCard`'s private `_UnclaimedBanner`; `ProviderResultCard` updated to use it.
3. **New shared widget `mobile/lib/shared/widgets/verified_badge.dart`** (Decision 8) — `badge-verified` design
   tokens (`success-container`/`on-success-container`, per `DESIGN.md`), paired icon + "Verified" text label
   (never icon alone, per `16_UX_GUIDELINES.md`).
4. `mobile/lib/core/routing/app_routes.dart` — new `static const String providerProfile = '/provider-profile'`.
5. `mobile/lib/core/routing/app_router.dart` — new `GoRoute` for `providerProfile`, requiring `ProviderProfileArgs`
   via `extra`.
6. `mobile/lib/features/search/presentation/screens/search_results_screen.dart` — `_onCardTap` now navigates to
   `AppRoutes.providerProfile` with the tapped id and `searchRequestId: null` (DIR-001's structured search path
   creates no `search_requests` row, per MAT-001's own Verified Current State) instead of showing the "coming
   soon" snackbar.
7. `mobile/lib/features/conversation/presentation/screens/ai_conversation_screen.dart` — `_onResultTap` now
   navigates to `AppRoutes.providerProfile` with the tapped id and the session's real, already-known
   `searchRequestId` (threaded down from `ConversationController`'s existing polling state — the cleanest
   plumbing path is `frontend`'s implementation call; must not be added to the shared `SearchRequestResult`
   model, which mirrors the backend response shape 1:1 and has no such field).
8. `mobile/lib/l10n/app_en.arb` / `app_ar.arb` — new keys for the Provider Profile screen's labels, the Contact
   Reveal sheet's copy (including AC6's required note), the Verified badge label, hours/service-area labels.
   Remove `providerProfileComingSoonMessage` if it becomes genuinely unused after both call sites are rewired
   (confirm via a repo-wide search before removing).

### Tests

9. `mobile/test/features/provider_profile/` — controller tests (profile load success/error, contact-reveal
   success/error/self-dealing-403-mapped-to-a-clear-message), widget tests for the profile screen (rating+count
   rendered together, each of Decision 8's three badge states, hours/service-area rendered) and the Contact
   Reveal sheet (phone number shown, Call/WhatsApp buttons present, the outside-the-app note present, WhatsApp
   button absent when `whatsapp_number` is `null`).
10. `mobile/test/shared/widgets/unclaimed_banner_test.dart` — moved/adapted from whatever inline coverage
    `provider_result_card_test.dart` (if any) already has for `_UnclaimedBanner`, plus `ProviderResultCard`'s
    own existing tests re-run to confirm no visual/behavioral regression from the extraction.
11. `search_results_screen_test.dart` / the `AiConversationScreen` results-view test — updated to assert real
    navigation (with the correct `ProviderProfileArgs`) instead of the old snackbar assertion.
12. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **The Outcome Tag prompt** (`outcome_tags` table/mechanism) — the story's own explicit scope boundary; this
  story ends at the phone number being shown.
- **Any part of the Review domain** (`reviews`, `provider_rating_summaries`) — `REV-001`/`REV-002`'s job,
  unaffected by this story (still reads `providers.average_rating`/`review_count` exactly as MAT-001 left it).
- **`visit_verifications`** ("Verified Visit" OTP-based confirmation) — a distinct, later concept from this
  story's Decision 8 "Verified" provider-trust badge; not built here, and `15_SCREEN_INVENTORY.md`'s S-09 row's
  own "Verified Visit badge if present" element is deferred along with it (nothing to show yet — no Contact View
  can have a Visit Verification until that mechanism exists).
- **ENG-001's actual notification delivery mechanism** (push/SMS/email, opt-in preferences) — AC7's own explicit
  boundary; this story only emits the in-app `notification.notifications` record.
- **The full portfolio photo carousel** on the Provider Profile screen — AC5's literal wording asks for rating,
  badge, and hours/service-area; this story includes only the primary photo already available from existing
  data, not a new multi-photo carousel UI. Flagged as a deliberate scope trim against `15_SCREEN_INVENTORY.md`'s
  fuller S-09 vision, not an oversight.
- **A customer-facing "distance from me" figure on the Provider Profile screen** — no AC requests it, and adding
  it would require the detail endpoint to accept and geocode a customer origin it does not otherwise need.
- **Retrofitting a "Verified" badge onto the existing search-results `ProviderResultCard`** — no AC requires
  this; only the new Provider Profile screen (S-09) needs it per AC5's literal text.
- **Pay-per-lead billing** — `04_DATABASE.md`'s own note that `contact_views` is also "basis for... future
  pay-per-lead billing (post-MVP)" is explicitly out of scope; this story only creates the row.

---

## Open Questions (flagged for CTO awareness — do not block `backend` from starting; `frontend`'s
Call/WhatsApp work specifically should wait for the dependency approval below)

1. **`url_launcher` as a new mobile dependency** (Verified Current State, Frontend Proposed Changes) — needs
   explicit approval before `frontend` implements the Contact Reveal sheet's Call/WhatsApp buttons, mirroring
   this codebase's established practice for every prior new package (`google_maps_flutter`, `image_picker`,
   `file_picker`, etc.). It is the standard, Flutter-team-maintained package for exactly this use case — no
   viable alternative exists without it (Flutter's SDK has no built-in external-URL-launch mechanism) — but per
   `.agents/agents.md`'s "do not introduce additional frameworks or dependencies without approval," this is not
   assumed pre-approved.
2. **Decision 7 (no `is_discoverable=True` requirement for viewing/contacting a provider).** Confirm this
   deliberately looser posture is correct, or whether a customer should be blocked (404) from viewing/contacting
   a provider that has since become non-discoverable. Either is a contained, one-line change.
3. **Decision 10's status code choice (403 for self-dealing).** A genuinely new precedent (no existing exception
   in this codebase shares its exact shape) — confirm 403 over 409 is the intended semantic, or flag a
   preference; either is a one-line change with no other consequence.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

1. **backend** — Backend Proposed Changes items 1–15. Build order: (a) the migration first (item 1); (b) the new
   `contact` module (items 2–3), with its own tests (items 10–11) written alongside, since Decision 1's guard is
   this story's single most safety-critical piece; (c) the notification extension (item 4, with test 14); (d)
   the `AvailabilityService` extraction (item 5, with test 13) before touching the new public endpoint, since the
   endpoint depends on it; (e) the new public provider endpoint (items 6–8, with test 12) last. Read Decision 1
   in full before starting the `contact` module — it is the story's core safety mechanism.
2. **frontend** — Frontend Proposed Changes items 1–12. Should start once `backend`'s `contact`/public-provider
   endpoints are available to integrate against (or in parallel against the Plan's documented response shapes,
   per this codebase's established parallelization practice, with a final integration pass once both are done).
   **Do not implement the Call/WhatsApp launch behavior itself until Open Question 1 is resolved** — the rest of
   the screen (profile display, badge logic, the sheet's phone-number display and outside-the-app note) has no
   such dependency and can proceed immediately.
3. **tester** — verify all 8 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget
   tests). Particular attention to: AC3/AC4 (the self-dealing rejection, with a direct row-count assertion, not
   just an exception check — construct a real fixture where the same `user_id` owns both a `customer_profiles`
   and a `providers` row); AC2/AC6 (an end-to-end reveal flow confirming no quote/approval/messaging step exists
   anywhere and the outside-the-app note is genuinely rendered); AC5 (the three badge-precedent states, rating+
   count always shown together, hours/service-area genuinely present); AC7 (a Notification row is genuinely
   created for a claimed provider's contact, genuinely absent for an unclaimed one); AC1 (the real migration,
   not just the model).
4. **architect** — review Decision 1's self-dealing guard for genuine correctness and no bypass path (in
   particular: confirm the guard cannot be skipped by omitting/mismatching `search_request_id`, and that the
   `user_id`-equivalence reasoning in Decision 1/Verified Current State actually holds against the real code);
   Decision 2's route-registration-order reasoning (confirm it's provably correct, not just "tests happen to
   pass"); Decision 4's ownership-validation posture against `06_SECURITY.md`; Decision 8's badge-precedence
   logic against `00_PROJECT_CONTEXT.md` §3's anti-fabrication principle (no contradictory or fabricated trust
   signal); confirm no new problematic cross-module edge (the new `contact` module depending on `customer`,
   `provider`, `search`, `notification` is a lot of edges for one module — confirm each is justified and none
   creates a cycle).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decisions 1–10 as new ADRs (next available: **ADR-044** onward) — likely grouped into a smaller
     number of ADR entries where several decisions share one architectural theme (e.g. the self-dealing guard
     mechanism as one ADR, the new public-profile-endpoint/registration-order approach as another), at
     `tech-lead`'s discretion at closeout.
   - Update `04_DATABASE.md` to note `contact_views` is now shipped (cross-reference this Plan/Walkthrough),
     exactly per its existing spec, no deviation.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 8 section and `docs/AI/SESSION_HANDOFF.md` — Sprint 8/
     Milestone ML8 becomes fully Done (both `MAT-001` and `CON-001` complete), advancing the dashboard to
     Sprint 9.

---

## Verification Plan (mapped to the 8 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | The real migration (item 1) plus a direct schema-inspection test confirming `contact_views` and its FKs/indexes exist exactly per `04_DATABASE.md`. |
| 2 | An end-to-end mobile widget test + backend HTTP test confirming the Contact Reveal sheet shows the phone number and Call/WhatsApp buttons immediately on a single `POST /contact-views` call, with no other screen/step/status in between. |
| 3 | `test_contact_service.py`'s self-dealing fixture (same `user_id` owning both a `customer_profiles` and a `providers` row) asserting `SelfDealingContactError` is raised at creation time. |
| 4 | The same test, additionally asserting a direct `contact_views` row-count query is unchanged after the rejected attempt — not merely that an exception was raised. |
| 5 | `test_public_provider_api.py`'s three badge-precedent fixtures (unclaimed / claimed+approved / claimed+pending) plus a rating+review-count-together assertion and hours/service-area field presence, at both the API and mobile widget-test layers. |
| 6 | A mobile widget test asserting the Contact Reveal sheet renders the exact "contact happens outside the app" note, in both English and Arabic fixtures. |
| 7 | `test_notification_service.py`'s `notify_new_contact_view` unit test plus `test_contact_service.py`'s integration assertion that a claimed provider's contact creates exactly one `notification.notifications` row (and an unclaimed provider's contact creates none). |
| 8 | `test_contact_service.py`/`test_contact_api.py`'s happy-path and self-dealing-rejection tests are separate, explicitly named test cases (not one parameterized test conflating both), satisfying AC8's literal wording. |

---

## Related Documents

- `docs/AI/00_PROJECT_CONTEXT.md` §3 (anti-fabrication principle — basis for Decision 8's raw-field-not-computed-
  enum choice and for never showing a contradictory Verified+Unclaimed state)
- `docs/AI/03_DOMAIN_MODEL.md` v0.8.1 (Contact View domain, the dual-role Account rule, the self-dealing
  restriction's exact wording this Plan implements)
- `docs/AI/04_DATABASE.md` (Contact Domain — `contact_views`' full column/index spec and its own stated
  self-dealing guard mechanism; Common Columns/Soft Delete sections — basis for `contact_views` using
  `CommonColumnsMixin`; Provider Domain — `providers.user_id`/`is_claimed`/`verification_status`)
- `docs/AI/06_SECURITY.md` (basis for Decision 4's ownership-validation posture on `search_request_id`)
- `docs/AI/09_DECISIONS.md` (ADR-015 — `{id}`-addressable-collection-always-404 convention this Plan's Decision
  4 reuses; ADR-042/043 — MAT-001's ranking work this story's data flows directly downstream of)
- `docs/AI/13_OPEN_DECISIONS.md` (item 14 — `provider_rating_summaries`, unaffected by this story; this story's
  rating display continues reading `providers.average_rating`/`review_count` exactly as MAT-001 left it)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-09 Provider Profile, the Contact Reveal sheet, S-24 Leads — the provider-
  side view of the same Contact Views this story creates, unaffected/out of scope here)
- `docs/AI/16_UX_GUIDELINES.md` (Trust & Verification UX Patterns — the Unclaimed banner's resolved cross-screen
  reuse this Plan's Decision 9 implements; rating+count-together rule; Notification & Interruption UX — basis
  for AC7's "candidate trigger," not an immediate push)
- `docs/AI/DESIGN.md` (`bottom-sheet`, `badge-verified`, `badge-unclaimed` component tokens this Plan's mobile
  widgets use)
- `docs/implementation/plans/Plan_S06_CLM-001.md` / `Walkthrough_S06_CLM-001.md` (the one-Provider-per-account
  `user_id`-comparison precedent this Plan's Decision 1 mirrors; the Google-seeded `is_claimed=false`/
  `verification_status=approved` combination that drives Decision 8)
- `docs/implementation/plans/Plan_S05_VER-002.md` / `Walkthrough_S05_VER-002.md` (the `notification.notifications`
  module and `NotificationService` pattern this Plan's Decision 3 reuses unchanged)
- `docs/implementation/plans/Plan_S08_MAT-001.md` / `Walkthrough_S08_MAT-001.md` (the ranked-results data this
  story's Provider Profile screen is reached from; confirms the structured-search path creates no
  `search_requests` row, informing Decision 4/Frontend item 6)

---

**End of Document**
