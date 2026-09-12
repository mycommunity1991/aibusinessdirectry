# Walkthrough S08 CON-001

## Story: Contact a Matched Provider Directly

**Sprint:** 08 | **Story ID:** CON-001 | **Priority:** Critical | **Status:** Done

As a customer, I want to see a matched provider's phone number immediately when I tap Contact, with no quote or
approval step in between, so that reaching out feels as simple as getting a number from a friend. This story
implements the platform's growth-first, direct-contact model and its most safety-critical rule: the self-dealing
guard. Because one Account may hold both Customer and Provider roles, a Contact View must be rejected outright if
the requesting Customer's Account is the same Account that owns the target Provider — otherwise a provider could
inflate their own lead/contact/review numbers by contacting themselves. **Scope boundary:** does not include the
Outcome Tag prompt or reviews (REV-001/002) — this story ends at the phone number being shown.

Full context, the 10 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S08_CON-001.md`.
Implementer notes from backend/frontend/tester/architect were recorded in
`docs/implementation/plans/Checkpoint_S08_CON-001.md`, deleted at the end of this closeout per the Continuity &
Checkpointing rule now that the story is complete and signed off.

All work is committed to branch `claude/provider-storefront-pro-001-qnicuj`, with the architect-required
cross-module wiring fix landing at commit `bed63e8`.

**This story completes Sprint 8 and Milestone ML8 in full** — both `MAT-001` and `CON-001` are now Done.

---

## What was implemented

### Backend (`backend/app/modules/contact/` — new module; `backend/app/modules/provider/`,
`backend/app/modules/notification/` — extended)

- **New migration** (`contact_domain`, on top of `f3a1c9d47b02`) — creates the `contact` Postgres schema and
  `contact_views` table exactly per `04_DATABASE.md`'s pre-existing spec (full `CommonColumnsMixin`,
  `customer_id`/`provider_id` FKs not null, `search_request_id` FK nullable, `viewed_at` default `now()`, the
  three named indexes). No deviation from the spec occurred. Verified end to end against a real Postgres database
  (`upgrade head` / `downgrade -1` / re-`upgrade head`).
- **New module `backend/app/modules/contact/`** — `ContactService.create_contact_view(...)`: resolves the
  caller's `customer_profiles` row, resolves the target Provider, runs the **self-dealing guard**
  (`provider.user_id == current_user_id`, skipped only when `provider.user_id IS NULL` for a still-unclaimed
  listing) **before any row is written**, validates an optional `search_request_id`'s ownership (rejecting a
  mismatched or nonexistent id with 404, never silently dropping it), creates the `contact_views` row (no dedup —
  every tap is a separately meaningful analytics event), and emits a Notification when the provider is claimed.
  `POST /contact-views` (`require_role(ROLE_CUSTOMER)`), 201 on success, documented 403 (self-dealing) and 404
  (provider/search-request not found or not owned) responses.
- **New `SelfDealingContactError`** (403) — a permanent, identity-based authorization rejection, not a timing
  conflict (this codebase's existing 409s, e.g. `ClaimAlreadyClaimedError`, are for race/state-timing conflicts;
  this is neither).
- **`NotificationService.notify_new_contact_view`** — mirrors `notify_verification_status_change`'s existing
  shape exactly; called once, synchronously, on the same request-scoped transaction, only when the target
  provider is claimed (an unclaimed listing has no account to notify).
- **`AvailabilityService.get_availability_for_provider`** — the existing owner-scoped seven-day synthesis loop
  extracted into a shared helper and reused for an arbitrary target provider; `get_my_availability`'s own
  behavior is byte-for-byte unchanged.
- **New customer-facing `GET /providers/{provider_id}`** (`backend/app/modules/provider/public_api.py`) —
  a sibling router registered in `app/api/v1/api.py` **after** the existing owner-scoped `provider_router`, so
  Starlette's registration-order route matching resolves `/me`/`/me/portfolio`/`/me/availability` before the new
  `/{provider_id}` path-parameter route is ever reached. `ProviderService.get_for_public_profile` only requires
  `is_active=True` — deliberately **not** `is_discoverable=True` (a customer who already has a specific
  `provider_id` shouldn't hit a confusing 404 purely because a search-visibility flag changed later).
  `PublicProviderProfileResponse` deliberately excludes `phone_number`/`whatsapp_number` — those are only ever
  revealed through a real, recorded Contact View.
- **Badge precedence** — the server returns raw `is_claimed`/`verification_status` fields unchanged (never a
  pre-computed enum); the client renders exactly one of three states (Unclaimed / Verified / neither),
  since a Google-seeded listing can genuinely be `is_claimed=false` and `verification_status=approved`
  simultaneously.

### Mobile (`mobile/lib/features/provider_profile/` — new feature)

- **Real Provider Profile screen (S-09)** — name, category, description, primary photo, rating + review count
  always shown together (never rating alone), read-only weekly hours, the subtype-specific service-area field,
  the shared `UnclaimedBanner` (extracted from `ProviderResultCard`'s former private widget, now reused by both
  screens with no visual/behavioral change) or the new `VerifiedBadge` per the three-state badge precedence, and
  a sticky bottom Contact CTA.
- **Contact Reveal sheet** — a bottom sheet showing the phone number, a Call button (`tel:`), a WhatsApp button
  (`https://wa.me/...`, shown only if a WhatsApp number is present), and the required "contact happens outside
  the app" note (AC6, localized in both English and Arabic).
- **New dependency `url_launcher`** — added to `mobile/pubspec.yaml`, CTO-approved before frontend implementation
  began (see Decisions Confirmed by the CTO below). Wrapped behind an injectable `ContactLauncher` interface,
  mirroring `PortfolioImagePicker`/`LocationService`'s existing testable-plugin pattern.
- Both former "coming soon" call sites (`SearchResultsScreen._onCardTap`,
  `AiConversationScreen._ResolvedResultsView._onResultTap`) now navigate to the real Provider Profile screen
  instead of showing a snackbar; `providerProfileComingSoonMessage` removed from both `.arb` files after
  confirming it was genuinely unused.

### Decisions Confirmed by the CTO Before Implementation

Three of the Plan's Open Questions were pre-resolved by the orchestrator, on the CTO's behalf, before backend's
session started — all confirmed as proposed, no changes:

1. **`url_launcher` approved** as a new mobile dependency (the standard, Flutter-team-maintained package for
   launching `tel:`/`https://wa.me/...` URLs — no viable alternative exists without it).
2. **Decision 7 confirmed**: no `is_discoverable=True` requirement for viewing or contacting a provider — only
   `is_active=True` is required.
3. **Decision 10 confirmed**: HTTP 403 (not 409) for the self-dealing rejection — a permanent identity-based
   authorization rule, not a timing conflict.

---

## The 10 Architecture Decisions, as actually shipped

All 10 decisions from `Plan_S08_CON-001.md` shipped as planned, with one implementation-time wiring correction
to Decision 1 found during architect review (see Review Process below):

1. **New `contact` module; self-dealing guard enforced by a direct `user_id` comparison inside `ContactService`,
   not a DB constraint** — shipped as planned. The guard fires before any write, before `search_request_id`
   validation, confirmed airtight by both `tester`'s row-count assertion and `architect`'s line-by-line
   re-verification.
2. **New customer-facing `GET /providers/{provider_id}`, a sibling router registered after the existing
   `/me`-scoped router** — shipped as planned; route-registration-order reasoning independently re-verified by
   `architect` as provably correct, not merely "tests happen to pass."
3. **Notification emission mirrors VER-002's `notify_verification_status_change` exactly** — shipped as planned.
4. **`search_request_id`, if supplied, must belong to the calling customer** — shipped as planned (404, never a
   silent drop or a 403 that would leak existence).
5. **No uniqueness constraint on `(customer_id, provider_id)`** — shipped as planned.
6. **`AvailabilityService` gains a second, arbitrary-target read method; synthesis logic extracted once** —
   shipped as planned, confirmed byte-for-byte behavior-preserving for the existing owner-facing method.
7. **The public profile endpoint does not require `is_discoverable=True`** — shipped as planned (CTO-confirmed).
8. **Verified/Unclaimed badge precedence: `is_claimed` first, `verification_status` second, else neither** —
   shipped as planned; the raw fields are returned unchanged, the client computes the display state.
9. **`UnclaimedBanner` extracted to a shared, public widget** — shipped as planned, no visual/behavioral
   regression to the existing search-results card.
10. **Self-dealing rejection uses HTTP 403, a new `SelfDealingContactError`** — shipped as planned (CTO-confirmed).

---

## Review Process — a full, honest account

### `tester` — independent verification against real infrastructure, one coverage gap closed

The tester independently verified all 8 verbatim ACs with real evidence (real DB, real HTTP round trips, real
widget tests) and found **no functional bugs**. It did find one genuine test-coverage gap, not a defect:

- **AC6's Arabic-locale rendering of the Contact Reveal sheet's "outside the app" note had never actually been
  tested** — the existing widget test only ever pumped the sheet under the default English locale. The tester
  added a locale-parameterized Arabic case and confirmed the note renders correctly in Arabic exactly as it does
  in English — a real, already-working feature the test suite simply hadn't exercised yet, not a bug.

Final counts: 195/195 mobile tests pass, 702/702 backend tests pass, `flutter analyze`/`ruff check .` both clean.

### `architect` — one real finding, fixed and re-confirmed clean

The architect's first review returned **APPROVED WITH RECOMMENDATIONS**, with one real, non-blocking finding:

- **`ContactService` was wired with a raw `ProviderRepository` instead of `ProviderService`** — a violation of
  `02_ARCHITECTURE.md`'s "modules communicate through services only" cross-module rule. Concretely, this also
  produced a duplicate-logic instance: `ContactService`'s inline provider-lookup-plus-404 block
  (`get_by_id` + `is_active` check + `ProviderNotFoundError`) duplicated `ProviderService.get_for_public_profile`'s
  identical logic instead of calling it. `contact/dependencies.py`'s own docstring also inaccurately claimed this
  "mirrors `SearchRequestService`'s own multi-module wiring shape" — `SearchRequestService` actually only takes
  cross-module *Services*, never a raw cross-module Repository. The `CustomerProfileRepository`/
  `SearchRequestRepository` raw-repository uses were assessed as more defensible (neither `CustomerService` nor
  `SearchRequestService` expose an equivalent raw-lookup primitive today), but flagged for a documented
  convention going forward.
- **Fix (commit `bed63e8`)**: `ContactService.__init__` now takes `provider_service: ProviderService`;
  `create_contact_view` calls `provider_service.get_for_public_profile(provider_id)` directly, and the duplicate
  inline lookup block is removed entirely — not relocated, genuinely eliminated. The inaccurate docstring claim
  was corrected to state the `provider` edge is a Service specifically because of the services-only rule, while
  explicitly noting `customer`/`search` remain raw Repositories for a documented reason.
- **Architect re-check**: verified the fix line-by-line against the diff (not the commit message) — confirmed no
  leftover `provider_repository` parameter or construction site anywhere in the repo, confirmed the duplicate
  logic is genuinely gone by comparing both code paths byte-for-byte, confirmed no new cross-module cycle
  (`contact → provider` is now a Service-to-Service edge, same direction as before, just through the correct
  layer), and independently re-ran both full suites fresh: **702/702 backend tests pass, unchanged**, `ruff
  check .` clean.

**Final verdict: PASS / fully APPROVED, no remaining findings.**

### Final verdicts

- **`tester`**: all 8 ACs independently verified; no functional bugs found; one genuine test-coverage gap (AC6
  Arabic-locale rendering) closed, confirming a real, already-working feature.
- **`architect`**: one real finding (`ContactService`'s cross-module wiring), fixed and independently re-verified
  clean. **Final verdict: PASS, fully APPROVED.**
- **CTO sign-off** received after both final verdicts were presented, per standing process.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `contact_views` table exists via migration, referencing the customer, the provider, and optionally the originating search request | Pass — real migration, verified against `04_DATABASE.md`'s exact spec, no deviation |
| 2 | Tapping Contact immediately shows the phone number and Call/WhatsApp buttons in a bottom sheet — no quote, approval, or messaging step anywhere | Pass — a single `POST /contact-views` call reveals the number immediately; end-to-end mobile widget test + backend HTTP test confirm no intervening step exists |
| 3 | A Contact View is rejected if the requesting Customer Account is the same Account that owns the target Provider, enforced at creation time | Pass — the self-dealing guard fires before any row write; confirmed line-by-line by `architect` as unbypassable (cannot be skipped via `search_request_id` manipulation) |
| 4 | The self-dealing rejection is tested with an automated test asserting the row is never created | Pass — a direct `contact_views` row-count query, unchanged after the rejected attempt, not merely an exception assertion |
| 5 | Provider Profile screen shows rating with review count together, a Verified badge (or Unclaimed label), and hours/service-area information | Pass — all three Decision 8 badge states, rating+count always together, hours/service-area genuinely rendered, verified at both API and mobile widget-test layers |
| 6 | The Contact Reveal sheet includes a brief "contact happens outside the app" note | Pass — verified in both English and Arabic (the Arabic case was a tester-added coverage gap closure, not a bug fix — it already worked) |
| 7 | Every Contact View creation is a candidate trigger for provider-lead notifications, event emitted here | Pass — a Notification row is genuinely created for a claimed provider's contact, genuinely absent for an unclaimed one |
| 8 | Automated tests cover the happy path and the self-dealing rejection as separate, explicit test cases | Pass — distinct, explicitly named test cases at both the service and API layers |

**8 of 8 Pass.**

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded four new ADRs:
  - **ADR-044** — the self-dealing guard mechanism (Decisions 1 + 10): the direct `user_id` comparison inside
    `ContactService`, skipped only for a still-unclaimed listing, and the 403 status-code choice.
  - **ADR-045** — the new customer-facing `GET /providers/{id}` public endpoint (Decisions 2 + 7): the
    registration-order convention and the deliberately-not-`is_discoverable`-gated posture.
  - **ADR-046** — the raw-field trust-badge precedence pattern (Decision 8), recorded as a reusable precedent for
    future stories (e.g. Reviews).
  - **ADR-047** — the cross-module Services-only wiring convention this story's bug-fix round surfaced and
    reinforced, citing the `ContactService`/`ProviderService` fix (commit `bed63e8`) as the concrete
    precedent-setting example.
- **`docs/AI/04_DATABASE.md`** — `contact.contact_views` marked shipped, cross-referencing ADR-044; no deviation
  from the existing spec.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 8 marked fully complete (both `MAT-001` and `CON-001`
  Done), **Milestone ML8 complete in full**.
- **`docs/CHANGELOG.md`** — a new `[Unreleased]` entry for `CON-001`.
- **`docs/AI/SESSION_HANDOFF.md`** — updated to reflect Sprint 8/ML8 fully complete; ADR numbering advanced to
  ADR-047; next story left as an explicit placeholder pending the orchestrator's tracker lookup (Sprint 9's first
  story is not guessed or fabricated here).

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s `CON-001` row** still needs its Status updated to "Done" and rolled up
  through ML8-EP02/ML8/SP08/the Phase Tracker/the Dashboard — per standing process, handled via the raw-XML-safe
  cell-patching procedure by the orchestrator, not performed by this closeout.
- **`13_OPEN_DECISIONS.md` item 14** (`provider_rating_summaries`) remains genuinely open — unaffected by this
  story; still `REV-001`'s decision to make.
- **Sprint 9's first story** is not identified in this closeout — the orchestrator must look it up in the tracker
  and add it to `SESSION_HANDOFF.md` before the next session can skip the tracker read.

---

## Testing Performed

- `backend` implementation: new `contact` module test suites (`test_contact_service.py`, `test_contact_api.py`),
  extended `test_public_provider_api.py`, `test_availability_service.py`, `test_notification_service.py`. Full
  suite green (702/702) immediately after implementation.
- `frontend` implementation: new `provider_profile` feature test suites (screen, Contact Reveal sheet), extracted
  `UnclaimedBanner`/`VerifiedBadge` widget tests, updated navigation assertions at both former "coming soon" call
  sites. Full mobile suite green (192/192) immediately after implementation.
- `tester` agent: independently verified all 8 ACs against real infrastructure; closed one genuine test-coverage
  gap (AC6 Arabic-locale rendering, confirmed already-working); no functional bugs found. Final: 195/195 mobile,
  702/702 backend.
- `architect` agent: one real finding (`ContactService`'s raw-`ProviderRepository` cross-module wiring violation
  and its accompanying duplicate-logic instance), fixed at commit `bed63e8`, independently re-verified clean at
  the diff level with zero regressions. **Final verdict: PASS, fully APPROVED.**
- User (CTO) sign-off received after both final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_12_1000-024bcc0fbaf8_contact_domain.py` (new migration)
- `backend/app/modules/contact/` (new module — `models.py`, `repositories/contact_view_repository.py`,
  `services/contact_service.py`, `schemas.py`, `api.py`, `dependencies.py`)
- `backend/app/core/exceptions/exceptions.py` (`SelfDealingContactError`, `CustomerProfileNotFoundError`)
- `backend/app/modules/notification/services/notification_service.py` (`notify_new_contact_view`)
- `backend/app/modules/provider/services/availability_service.py` (`get_availability_for_provider`, extracted
  `_synthesize` helper)
- `backend/app/modules/provider/services/provider_service.py` (`get_for_public_profile`)
- `backend/app/modules/provider/public_api.py` (new — `GET /providers/{provider_id}`)
- `backend/app/modules/provider/schemas.py` (`PublicProviderProfileResponse`)
- `backend/app/api/v1/api.py` (router registration, order-sensitive)
- `backend/tests/modules/contact/test_contact_service.py`, `test_contact_api.py` (new)
- `backend/tests/modules/provider/test_public_provider_api.py`, `test_availability_service.py` (extended)
- `backend/tests/modules/notification/test_notification_service.py` (extended)

### Mobile
- `mobile/lib/features/provider_profile/` (new — domain models, repository, controllers, `provider_profile_screen.dart`
  (S-09), `contact_reveal_sheet.dart`, `contact_launcher.dart`)
- `mobile/lib/shared/widgets/unclaimed_banner.dart` (extracted, public)
- `mobile/lib/shared/widgets/verified_badge.dart` (new)
- `mobile/lib/shared/utils/rating_label.dart` (extracted)
- `mobile/lib/core/routing/app_routes.dart`, `app_router.dart` (new `providerProfile` route)
- `mobile/lib/features/search/presentation/screens/search_results_screen.dart`,
  `mobile/lib/features/conversation/presentation/screens/ai_conversation_screen.dart` (rewired navigation)
- `mobile/lib/l10n/app_en.arb`, `app_ar.arb` (new keys, including the AC6 note)
- `mobile/pubspec.yaml` (`url_launcher`, new approved dependency)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-044, ADR-045, ADR-046, ADR-047
- `docs/AI/04_DATABASE.md` — `contact.contact_views` marked shipped
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 8 / Milestone ML8 complete
- `docs/AI/SESSION_HANDOFF.md` — refreshed state, ADR numbering, Sprint 9 placeholder
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 8 and Milestone ML8 are now fully complete** — both `MAT-001` and `CON-001` have shipped and been
  signed off.
- **The next story is Sprint 9's first story** — not identified by this closeout. The orchestrator must look it
  up in `docs/AI/Project_Tracker.xlsx` and record it in `docs/AI/SESSION_HANDOFF.md` before the next session can
  skip the tracker read. This walkthrough deliberately does not guess or name a candidate.
- **`docs/AI/Project_Tracker.xlsx`'s `CON-001` row** still needs its Status flipped to "Done" and rolled up
  through ML8-EP02/ML8/SP08/the Phase Tracker/the Dashboard — handled separately by the orchestrator via the
  raw-XML procedure, not performed by this closeout.
- **The cross-module Services-only wiring convention** (ADR-047) should be checked against at the start of every
  future new module's `dependencies.py` review — this is the first concrete violation-and-fix example to cite,
  not a theoretical rule.
- **`docs/implementation/plans/Checkpoint_S08_CON-001.md` still needs to be deleted** per the Continuity &
  Checkpointing rule — this closeout pass had Read/Write/Edit/Grep/Glob tools only, with no file-deletion
  capability, so the file could not be removed here despite the story being complete and signed off.

---

**End of Document**
