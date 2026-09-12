# Checkpoint — Story CON-001 (Contact a Matched Provider Directly)

**Owner of this checkpoint:** `frontend` (this update)
**Status:** Backend and frontend implementation both complete, all tests green (192 passed, 0 failed --
169 baseline + 23 new). Not yet reviewed by `tester`/`architect`.

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

## Frontend implementation (this update)

Plan's Frontend Proposed Changes items 1–12 are all done, including the Call/WhatsApp launch behavior
(`url_launcher` added to `pubspec.yaml`, pre-approved per the orchestrator's own instructions this session).

- **New feature `mobile/lib/features/provider_profile/`**: domain models (`provider_profile.dart`,
  `provider_profile_args.dart` -- a record typedef `{providerId, searchRequestId}`, `contact_reveal.dart`,
  `provider_profile_exception.dart`, `contact_exception.dart`), `data/provider_profile_repository.dart`
  (`getProviderProfile`, `createContactView`), two separate Riverpod controllers
  (`state/provider_profile_controller.dart`, `state/contact_reveal_controller.dart`),
  `presentation/screens/provider_profile_screen.dart` (S-09 -- name, category, description, primary photo,
  rating+count together, read-only weekly hours, subtype service-area field, the shared `UnclaimedBanner`/new
  `VerifiedBadge` per Decision 8's three-state precedence, sticky bottom Contact CTA),
  `presentation/widgets/contact_reveal_sheet.dart` (loading/phone-number/Call `tel:`/WhatsApp `wa.me` (only if
  present)/AC6 outside-the-app note), `presentation/utils/contact_launcher.dart` (an injectable `ContactLauncher`
  interface wrapping `url_launcher`, mirroring `PortfolioImagePicker`/`LocationService`'s testable-plugin
  pattern), plus error-copy utils.
- **`mobile/lib/shared/widgets/unclaimed_banner.dart`** (Decision 9) -- extracted byte-for-byte from
  `ProviderResultCard`'s former private `_UnclaimedBanner`; `ProviderResultCard` updated to use it (no
  visual/behavioral change, confirmed by its own pre-existing tests still passing unmodified).
- **`mobile/lib/shared/widgets/verified_badge.dart`** (Decision 8) -- `badge-verified` tokens; added
  `AppColors.successContainer`/`onSuccessContainer` and `AppRadius.full` to the theme files (DESIGN.md-derived
  hex/token values that didn't exist yet).
- **`mobile/lib/shared/utils/rating_label.dart`** -- extracted the "No reviews yet" / "{rating} ({count}
  reviews)" formatting out of `ProviderResultCard` so the Provider Profile screen doesn't duplicate it.
- Routing: `AppRoutes.providerProfile` + a new `GoRoute` requiring `ProviderProfileArgs` via `extra`.
- Rewired both former "coming soon" call sites: `SearchResultsScreen._onCardTap` (`searchRequestId: null`) and
  `AiConversationScreen._ResolvedResultsView._onResultTap` (threaded `ConversationSession.searchRequestId` down
  through `_ActiveView`). `providerProfileComingSoonMessage` removed from both arb files (confirmed unused via
  repo-wide grep first).
- l10n: new keys added to both `app_en.arb`/`app_ar.arb` for the profile screen, the sheet (including the AC6
  note, verbatim), the Verified badge, hours/service-area labels, and error copy (including a specific message
  for the 403 self-dealing rejection).

### Tests (all passing)

- `mobile/test/features/provider_profile/provider_profile_screen_test.dart` (11 cases: load error+retry, all
  three Decision 8 badge states plus the claim-tap navigation, rating+count together with/without a rating,
  weekly hours rendered, Business vs. Freelancer service-area fields, Contact CTA opening the sheet).
- `mobile/test/features/provider_profile/contact_reveal_sheet_test.dart` (6 cases: phone+Call button on
  success, WhatsApp button present/absent, the AC6 outside-the-app note, the self-dealing 403 mapped to a clear
  message, a generic failure with a working retry).
- `mobile/test/shared/widgets/unclaimed_banner_test.dart` (new, moved/adapted) and
  `provider_result_card_test.dart` (existing, re-run unmodified) both pass -- no regression from the extraction.
- `mobile/test/shared/widgets/verified_badge_test.dart` (new, 1 case).
- `search_results_screen_test.dart`/`ai_conversation_screen_test.dart` extended with real-navigation assertions
  (via each feature's local test-router stubs) replacing the old snackbar behavior, which itself had no prior
  test coverage to update (confirmed by grep before writing new assertions instead of editing non-existent ones).

Full suite: **192 passed, 0 failed** (169 baseline + 23 new). `flutter analyze`: 0 issues. `dart format
--set-exit-if-changed`: clean.

## What's explicitly next

1. **tester** — verify all 8 verbatim ACs per the Plan's Verification Plan table, now that both backend and
   frontend are complete (AC2/AC5/AC6 now have real mobile UI to verify against; AC1/AC3/AC4/AC7/AC8 are already
   covered by backend tests, but tester should still verify independently, not just trust this checkpoint).
2. **architect** — review Decision 1's guard, Decision 2's route-registration-order reasoning, Decision 4's
   ownership-validation posture, Decision 8's badge precedence (now implemented client-side exactly as
   specified), and the `contact` module's cross-module edge count, per the Plan's own Delegation section item 4.

## Open questions / blockers

None. All three of the Plan's Open Questions were pre-resolved by the orchestrator before backend's session
started: `url_launcher` approved (now added and used), no `is_discoverable` requirement confirmed (Decision 7 as
built), 403 for self-dealing confirmed (Decision 10 as built, and mapped to a specific client-side message).

---

## `tester` update (post-frontend)

Verified all 8 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget tests). Closed one
test-coverage gap: the AC6 "outside the app" note test only ever pumped under the default English locale: added
a locale-parameterized Arabic case (commit `259218a`). Confirmed the implementation already rendered correctly
in Arabic — a coverage gap, not a functional bug. No functional bugs found. 195/195 mobile tests pass, 702/702
backend tests pass, `flutter analyze`/`ruff check .` both clean.

## `architect` review (this update)

**Status: reviewed, verdict APPROVED WITH RECOMMENDATIONS.** Full findings relayed to the top-level session/user
directly (not duplicated here) — see that response for the ranked list. Summary for continuity:

- Independently re-verified (not just trusted) all items the orchestrator asked for: the self-dealing guard's
  line-by-line ordering (airtight — guard fires before `search_request_id` validation and before any write),
  the `contact` module's four cross-module edges (`customer`/`provider`/`search`/`notification` — confirmed via
  grep that none of the four import back from `contact`, no cycle), `PublicProviderProfileResponse`'s schema
  (no phone/whatsapp field anywhere in it or its nested types), the migration (matches `04_DATABASE.md` exactly,
  reversible), `AvailabilityService`'s extraction (byte-for-byte behavior-preserving, read the diff directly),
  the mobile `UnclaimedBanner` extraction (no leftover private duplicate) and `ContactLauncher`'s pattern
  (genuinely mirrors `PortfolioImagePicker`/`LocationService`'s abstract-interface + `Device*`-impl +
  Riverpod-provider shape).
- Independently re-ran both suites fresh: backend 702 passed (`uv run pytest -q`), mobile 195 passed
  (`flutter test`), `ruff check .` clean, `flutter analyze` clean (0 issues).
- One real finding, not blocking: `ContactService` is wired with three raw cross-module *Repositories*
  (`CustomerProfileRepository`, `ProviderRepository`, `SearchRequestRepository`) rather than those modules'
  *Service* classes, and `contact/dependencies.py`'s own docstring inaccurately claims this "mirrors
  `search.SearchRequestService`'s own multi-module wiring shape" — `SearchRequestService` actually only takes
  cross-module *Services* (`ProviderService`, `CustomerService`, `SavedAddressService`, etc.), never a raw
  cross-module Repository. Concretely, this also produces one small duplicate-logic instance: `ContactService`'s
  inline provider-lookup-plus-404 block (`get_by_id` + `is_active` check + `ProviderNotFoundError`) duplicates
  `ProviderService.get_for_public_profile`'s identical logic instead of calling it. Recommended fix: have
  `ContactService` depend on `ProviderService` (call `get_for_public_profile`) instead of `ProviderRepository`
  directly, and correct/remove the inaccurate docstring claim. The `CustomerProfileRepository`/
  `SearchRequestRepository` raw-repository uses are more defensible (neither `CustomerService` nor
  `SearchRequestService` expose an equivalent raw-lookup primitve today) but are still worth a short ADR note
  at closeout establishing the convention going forward, since this is the first module with this shape of
  wiring.
- No MVP-scope violation, no undocumented architecture drift beyond the one noted item above, no security gap
  found.

Next: pause for user sign-off per standing process (do not write the Walkthrough or touch
`docs/CHANGELOG.md`/tracker yet).
