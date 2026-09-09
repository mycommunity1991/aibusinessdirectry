# Walkthrough S06 CLM-001

## Story: Claim My Google-Seeded Business Listing

**Sprint:** 06 | **Story ID:** CLM-001 | **Priority:** Medium | **Status:** Done

As a business owner, I want to find my business among Google-seeded listings and verify I own the public phone
number on record, so that I gain edit access to my own storefront instead of a stranger being able to claim it.
This story bootstraps Business supply from public Google listings (so the directory isn't empty at launch) and
implements the claim flow's OTP-against-public-record safeguard. It executes exactly the bulk-import design the
CTO's 09 September 2026 risk-acceptance decision (`13_OPEN_DECISIONS.md` item 3) approved for MVP — it does not
re-litigate that decision or substitute a lower-risk design.

Full context, the 10 Architecture Decisions, and file-by-file scope: `docs/implementation/plans/Plan_S06_CLM-001.md`.
Implementer notes/flagged deviations: `docs/implementation/plans/Checkpoint_S06_CLM-001.md` (deleted at the end of
this closeout, per the Continuity & Checkpointing rule).

All work is committed and pushed to branch `claude/provider-storefront-pro-001-qnicuj`: backend implementation
(`9852545`), mobile implementation (`a021f6d`), and an AC5 bug fix found during review (`0df2e48`).

---

## What was implemented

### Backend (`backend/app/modules/provider/`, `backend/app/modules/administration/`, `backend/app/modules/search/`)

- **New migration** `602bf3c4bea7` (`claim_review_requests`, down-revision `a804c46bf703`) — creates
  `administration.claim_review_requests` exactly per Decision 9. No changes to any existing table — every
  `providers` column this story needs (`listing_source`, `is_claimed`, `claimed_at`, `google_place_id`,
  `user_id`, `verification_status`, `is_discoverable`) already existed, pre-designed for this exact story.
- **Import mechanism** (`backend/scripts/import_google_places.py`) — a manually-invoked CLI script, the same
  `async def main()` / `async_session()` shape as `seed_roles.py`/`grant_admin_role.py`. The same script run is
  both the first bulk seed and every later re-sync; idempotency is keyed on `google_place_id`
  (`ProviderRepository.get_by_google_place_id`).
- **Import-time discoverability** (`ProviderService.create_google_seeded_provider`) — sets
  `listing_source=GOOGLE_SEEDED_UNCLAIMED`, `is_claimed=False`, `verification_status=APPROVED`,
  `is_discoverable=True`, plus a matching `verification.verification_records` row (`status=APPROVED`,
  `reviewed_by=NULL`, `verification_type=BUSINESS_LIGHTWEIGHT`) — see Decision 2 below, this story's most
  consequential decision.
- **Field mapping / skip rules** (`provider_type` always `BUSINESS`; `phone_number`/`operating_hours`/etc. left
  `NULL` rather than fabricated when Google doesn't provide them; a place missing `name`/`geometry.location`/
  `formatted_address` is skipped, not partially imported) and a matching `service_areas` row on every import
  (`ServiceAreaRepository.upsert_for_provider`, without which imported listings would be invisible to DIR-001's
  `search_nearby` query, silently defeating AC2).
- **Claim search** (AC3) — new `ProviderRepository.search_unclaimed` (substring `ILIKE` on name + address/city,
  scoped to `listing_source=GOOGLE_SEEDED_UNCLAIMED AND is_claimed=false`), exposed via
  `GET /claims/search?query=&page=&page_size=`.
- **Claim finalization** (`ClaimService`, `backend/app/modules/provider/services/claim_service.py`) — `request_otp`
  (AC4, structurally accepts no phone-number parameter — the number always comes from the target provider's own
  stored columns; raises `ClaimPublicNumberUnavailableError` without ever calling `OtpService` if the provider has
  no public number), `verify_otp` (AC5), `request_admin_review` (AC6). `_finalize_claim` is a single private
  method shared by both `ClaimService.verify_otp` (OTP-success path) and `AdminClaimService.approve_review_request`
  (admin-approved fallback path), so the two success paths can never silently drift apart — see Decision 6/9 below.
- **Admin fallback** (AC6) — new `administration.claim_review_requests` table (Decision 9, mirrors
  `unmatched_query_reports`'s precedent), `ClaimReviewRequestService`, and `AdminClaimService`
  (`list_open_review_requests`, `approve_review_request`, `reject_review_request`), exposed at
  `/admin/claims` — backend-only, no dashboard UI, per VER-002's established "admin does something, no UI yet"
  precedent.
- **Backfill-only-once-claimed** (AC7) — `ProviderService.backfill_google_seeded_provider`: while
  `is_claimed=False`, a re-sync fully overwrites mapped fields with fresh Google data; once `is_claimed=True`, a
  re-sync writes only fields whose current stored value is `NULL`/empty, leaving every owner-edited non-empty
  field untouched regardless of what fresh Google data says.
- **`GooglePlacesClient` Protocol** (Decision 10) — `HttpxGooglePlacesClient` (real, `httpx`-based) and
  `FakeGooglePlacesClient` (test-only), mirroring the `FileStorage`/`DocumentOcrService` swappable-Protocol
  precedent (ADR-017/018) for a third time, since automated tests cannot call a real, billed third-party API.
- **`search` module extension** (Decision 8) — `SearchResultProviderResponse` gains one additive field,
  `is_claimed: bool`, populated from `Provider.is_claimed`.

### Mobile (`mobile/lib/features/claim/`, `mobile/lib/features/search/`)

- `features/search/` extension: `SearchResultProviderResponse` gains `isClaimed`;
  `provider_search_card.dart` renders a full-width, solid `AppColors.warning` banner (locked copy: "Unclaimed —
  Is this your business? Claim it") when `isClaimed == false`, with a separate `onClaimTap` callback that
  navigates straight to the Claim OTP screen for that `providerId`, skipping the Claim Search screen.
- New feature `features/claim/`: `claim_search_screen.dart` (S-21, AC3), `claim_otp_screen.dart` (S-22, AC4/AC5/
  AC6 — an always-visible "This isn't working" link, never conditional on repeated failures), `claim_repository.dart`,
  Riverpod controllers (`claim_search_controller.dart`, `claim_otp_controller.dart`), and error-copy mapping for
  every backend 404/409/429/400.
- Entry point: a secondary "Already listed on Google? Claim your business" action on the Home placeholder screen.
- All new/changed strings added to both `app_en.arb`/`app_ar.arb`.

---

## The 10 Architecture Decisions, as actually shipped

All 10 decisions from `Plan_S06_CLM-001.md` shipped, with one deliberate, tester-caught gap in Decision 2's
claim-time reset (fixed during review — see Review Process below) and one genuine backend-side strengthening of
Decision 6 beyond the Plan's literal text:

1. **Import mechanism: a manually-invoked CLI script, idempotent upsert keyed on `google_place_id`** — shipped
   exactly as planned. No new scheduler/cron infrastructure was introduced.
2. **Import-time synthetic `verification_status=approved`/`is_discoverable=true` + a matching system-generated
   `verification_records` row; claim resets both to `pending`/`false`** — shipped largely as planned, but with a
   genuine gap the tester found and this closeout fixed: the import-time synthetic `verification_records` row
   was never excluded from `VerificationRecordRepository.get_latest_for_provider`, so it silently outlived the
   claim-time reset and blocked the claimant's first real verification submission. See Review Process below for
   the full account — this is the single most significant finding of this story's review.
3. **Import job always creates `provider_type=BUSINESS`; required-but-Google-doesn't-provide fields defaulted,
   never fabricated** — shipped exactly as planned.
4. **Import job also creates a matching `service_areas` row** — shipped exactly as planned; without it, imported
   listings would never appear in DIR-001's `search_nearby` results.
5. **Claim search: a new, dedicated substring `ILIKE` query in the `provider` module, distinct from DIR-001's
   `search` module** — shipped exactly as planned.
6. **Claim finalization: OTP success immediately sets `is_claimed=true`/`user_id`/`claimed_at`, enforces
   one-Provider-per-Account, grants `ROLE_PROVIDER`** — shipped with a genuine strengthening beyond the Plan's
   literal "re-fetch fresh, re-check `is_claimed=false`" text: the backend engineer instead built
   `ProviderRepository.try_claim_for_account`, a single atomic conditional `UPDATE ... WHERE is_claimed = false`,
   directly mirroring VER-002's `try_claim_for_review` optimistic-concurrency pattern (ADR-024) rather than a
   plain read-then-write, which would leave a real race window for two concurrent claim attempts on the same
   listing. Confirmed correct and consistent with existing precedent by the architect. Recorded as part of
   ADR-030 below.
7. **Module placement: both claim endpoints live in the `provider` module** — shipped exactly as planned, per
   `02_ARCHITECTURE.md`'s explicit assignment.
8. **`SearchResultProviderResponse` gains `is_claimed: bool`; mobile renders the banner on `S-08` only** — shipped
   exactly as planned, including the deliberate non-build of `S-09` (doesn't exist yet).
9. **AC6's admin-review fallback: a new `administration.claim_review_requests` table, admin-API-only** — shipped
   exactly as planned, mirroring `unmatched_query_reports`'s precedent.
10. **`GooglePlacesClient` swappable Protocol** — shipped exactly as planned, the third application of the
    `FileStorage`/`DocumentOcrService` Protocol-swappability pattern (ADR-017/018).

---

## Review Process — a full, honest account

### 1. `tester` — independent verification against real Postgres databases and real HTTP round trips, plus one genuine finding

The tester did not simply re-run the existing suite. It independently verified all 8 acceptance criteria against
real infrastructure, not mocks:

- Ran the actual `import_google_places.py` script (against `FakeGooglePlacesClient`, since a real Places API key
  is not available in this environment) and queried the resulting rows directly via raw SQL to confirm
  `listing_source`/`is_claimed`/`google_place_id` are exactly as AC1 specifies, on every created row, never
  `self_registered` under any code path.
- Exercised `GET /claims/search`'s real HTTP round trip to confirm its scoping: a self-registered or
  already-claimed provider matching the same query text never appears.
- Structurally verified AC4's phone-number guarantee via `inspect.signature` on `ClaimService.request_otp` and its
  endpoint — confirming there is no parameter through which a client-supplied phone number could ever reach
  `OtpService`, not merely that a test happened not to exercise one.
- **Found a genuine bug in AC5**: `ClaimService._finalize_claim` correctly reset `providers.verification_status`/
  `is_discoverable` to `pending`/`false` at claim time, but never touched the `verification.verification_records`
  table. The import-time synthetic `APPROVED` record (Decision 2) therefore remained the provider's "latest"
  verification record after claim. `VerificationService.submit`'s resubmission-eligibility check and
  `GET /providers/me/verification`'s status display both read `get_latest_for_provider` directly — so a freshly
  claimed listing's first real verification submission was rejected with a 409 (only a `REJECTED` latest record
  permits a new submission), and its status screen would have shown a dishonest "Approved" despite
  `providers.verification_status` already having been reset to `pending`. This directly contradicted AC5's literal
  "routes through the same Verification gate a self-registered Business would go through" — a self-registered
  Business has no such stale record and submits cleanly on its first attempt.

### 2. `tech-lead` (this session) — diagnosed and fixed the AC5 gap

Excluded the system-generated, never-human-reviewed `APPROVED` record from
`VerificationRecordRepository.get_latest_for_provider`'s query, via a `WHERE NOT (status = APPROVED AND
reviewed_by IS NULL)` clause. This signature — `status=APPROVED AND reviewed_by IS NULL` — was confirmed as the
exact, exclusive signature of CLM-001's import-time synthetic approval: every real admin approval
(`AdminVerificationService.approve`) always sets `reviewed_by=<the acting admin's id>`, confirmed by directly
reading that method; no other code path in this codebase ever writes `VerificationRecord(status=APPROVED,
reviewed_by=None)`. With this record excluded, a freshly claimed listing behaves identically to a freshly
self-registered Business — `get_latest_for_provider` returns `None` until it actually submits — which is the
literal mechanism of AC5's "routes through the same Verification gate." Verified via the tester's own regression
test (`test_claim_verification_gate_integration.py`) going from failing to passing, and the full backend suite
staying green (550/550). Committed as `0df2e48`.

The fix lives inside `verification`'s own repository, not as a new `provider → verification` read the `provider`
module would have to add — `provider → verification` would be a genuinely new cross-module edge in the wrong
direction (an inversion of the existing, correct `verification → provider` edge VER-001 established), and would
have created an architectural cycle. Two other fix locations were considered and rejected: (a) deleting or
mutating the synthetic record at claim time inside `_finalize_claim` — rejected, since `verification_records` is
this codebase's documented source-of-truth audit trail (`04_DATABASE.md`), and destroying or backdating a real
historical row (even a synthetic one) to make a query behave correctly would trade an honest audit trail for a
query-shape convenience; (b) adding a second, parallel "effective latest" query method used only by the claim
path — rejected as needless duplication when a single, correctly-scoped `get_latest_for_provider` serves every
caller identically and correctly.

### 3. `architect` — reviewed the fix specifically, confirmed it is airtight

Returned **APPROVED WITH RECOMMENDATIONS (non-blocking)**:

- Re-verified the exclusion signature is genuinely exclusive by grepping every `VerificationRecord(status=APPROVED)`
  construction site in the codebase — exactly two exist (the admin-approval path, `reviewed_by` always set; the
  import job, `reviewed_by` always `NULL`) — confirming the `WHERE` clause cannot ever misclassify a real,
  human-reviewed approval as synthetic.
- Confirmed zero side effects on VER-001/VER-002's existing behavior by running their full 67-test suite
  unmodified and green.
- Agreed with the reasoning for placing the fix inside `verification`'s own repository rather than either
  rejected alternative above.
- Two non-blocking documentation follow-ups (both acted on at this closeout, see below): add
  `administration.claim_review_requests` to `04_DATABASE.md`'s Administration Domain section (genuinely new
  schema, not previously specified there); record the "a system-generated verification record must carry a
  structurally-provable non-human signature and be excluded from `get_latest_for_provider`" pattern as an
  addendum under Decision 2's ADR, as precedent for any future story introducing another kind of system-generated
  verification record.

### Final test counts

- **Backend: 550 passed** (55 new for CLM-001's own backend implementation, plus the tester's 2 new regression
  tests covering the AC5 gap and its fix). `ruff check` clean.
- **Mobile: 157 passed.** `flutter analyze` clean.

---

## Acceptance Criteria — Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Import job creates `providers` rows with `listing_source=google_seeded_unclaimed`, `is_claimed=false`, a populated `google_place_id` — never `self_registered` | Pass |
| 2 | Unclaimed listings are visually distinct in search/directory results (full-width banner, not a small badge) | Pass |
| 3 | Claim search screen finds a business by name/location among unclaimed listings | Pass |
| 4 | OTP is sent to the public phone number on record — never a client-typed number | Pass |
| 5 | Successful OTP verification sets `is_claimed=true`, populates `user_id`, routes through the same Verification gate a self-registered Business would go through | Pass — after the AC5 gap found by `tester` was fixed (see Review Process) and independently re-verified by `architect` |
| 6 | OTP failure or an unusable public number falls back to an explicit admin-review path | Pass |
| 7 | Post-claim Google Places sync jobs never overwrite owner-edited fields — only backfill genuinely empty ones | Pass |
| 8 | Automated tests cover OTP-goes-only-to-public-number and the admin-fallback-on-failure path | Pass |

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded three new ADRs:
  - **ADR-029** — the import-time synthetic verification-approval pattern (Decision 2), including the
    verification-record-exclusion addendum (the AC5 bug fix).
  - **ADR-030** — the claim finalization pattern (Decision 6/9): the atomic conditional `UPDATE` race-fix
    (`try_claim_for_account`), the shared `_finalize_claim` helper, the new `claim_review_requests` table and its
    backend-only admin-API pattern.
  - **ADR-031** — the `GooglePlacesClient` swappable-Protocol precedent (Decision 10), recorded as the third
    application of the pattern ADR-017/018 already established, not a duplicate pattern.
- **`docs/AI/04_DATABASE.md`** — Administration Domain section gains `claim_review_requests`'s full column list,
  mirroring how `unmatched_query_reports` is documented there.
- **`docs/AI/13_OPEN_DECISIONS.md`** — item 3 updated: stays **Open** (the underlying legal question is
  unresolved), but now reflects that the bulk-import mechanism, OTP claim flow, and admin-review fallback are
  live in the codebase, and that the `listing_source`/`google_place_id` mitigation is now actually operative
  (real rows exist that could need bulk deletion if legal review later forces it, not just a theoretical schema
  affordance).
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 6 marked fully complete (both DIR-001 and CLM-001 done);
  Executive Summary, Sprint 6 table, Section 16 (Overall Progress), and Section 17 (Next Planned Story) updated —
  Section 17 now notes Sprint 6 is complete and the next genuinely unblocked candidate is `AI-001` (Sprint 7,
  unblocked by CTG-001), not planned or started by this closeout.
- **`docs/CHANGELOG.md`** — new `[Unreleased]` entry for CLM-001 (backend + mobile), including the AC5 bug fix.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s Stories sheet** still needs its `CLM-001` row's Status updated from
  "Planned" to "Done" — per standing process, the CTO handles this separately via a raw-XML-safe cell-patching
  procedure. Not performed by this closeout.
- **The underlying Google Places legal question** (`13_OPEN_DECISIONS.md` item 3) remains genuinely open —
  shipping `CLM-001` does not resolve it; it executes the CTO's already-made risk-acceptance decision.
- **The fetch-verify-then-trust later-stage improvement** item 3 names remains unscheduled, not built by this
  story.

---

## Testing Performed

- `backend` implementation, with a new 55-test automated suite across `test_provider_service_claim.py`,
  `test_claim_service.py`, `test_admin_claim_service.py`, `test_claim_api.py`, `test_admin_claim_api.py`,
  `test_google_places_import_script.py`, and `test_claim_review_request_service.py`.
- `frontend` implementation, with a new automated suite covering the banner (AC2), the claim search screen (AC3),
  and the claim OTP screen including the always-visible admin-fallback link (AC6) — full mobile suite 157/157
  passing, `flutter analyze`/`dart format --set-exit-if-changed` both clean.
- `tester` agent: all 8 ACs independently verified against real Postgres databases and real HTTP round trips —
  see Review Process above. One genuine finding (the AC5 verification-gate gap), diagnosed and fixed by
  `tech-lead`, re-verified via the tester's own regression test going from failing to passing.
- `architect` agent: returned **APPROVED WITH RECOMMENDATIONS (non-blocking)** on the fix specifically — both
  recommendations acted on at this closeout.
- User (CTO) sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/2026_09_09_1100-602bf3c4bea7_claim_review_requests.py` (new migration)
- `backend/app/modules/provider/services/claim_service.py` (new — `ClaimService`, `_finalize_claim`)
- `backend/app/modules/provider/services/admin_claim_service.py` (new — `AdminClaimService`)
- `backend/app/modules/provider/services/google_places_client.py` (new — `GooglePlacesClient` Protocol,
  `HttpxGooglePlacesClient`, `FakeGooglePlacesClient`)
- `backend/app/modules/provider/claim_api.py`, `admin_claim_api.py` (new routers)
- `backend/app/modules/provider/repositories/provider_repository.py` (`get_by_google_place_id`,
  `search_unclaimed`, `try_claim_for_account`)
- `backend/app/modules/provider/services/provider_service.py` (`create_google_seeded_provider`,
  `backfill_google_seeded_provider`, `search_unclaimed_listings`)
- `backend/app/modules/administration/models.py`, `repositories/claim_review_request_repository.py`,
  `services/claim_review_request_service.py` (new)
- `backend/app/modules/verification/repositories/verification_record_repository.py`
  (`get_latest_for_provider`'s exclusion clause — the AC5 bug fix, commit `0df2e48`)
- `backend/scripts/import_google_places.py` (new — the idempotent import/re-sync CLI script)
- `backend/tests/modules/provider/test_claim_verification_gate_integration.py` (new — the tester's regression
  test for the AC5 gap)

### Mobile
- `mobile/lib/features/claim/` (new — `claim_search_screen.dart`, `claim_otp_screen.dart`, `claim_repository.dart`,
  `claim_search_controller.dart`, `claim_otp_controller.dart`)
- `mobile/lib/features/search/presentation/widgets/provider_search_card.dart` (unclaimed banner)
- `mobile/lib/features/search/domain/models/search_result_provider.dart` (`isClaimed`)
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (claim entry point)
- `mobile/lib/core/routing/app_router.dart` (new `claimSearch`/`claimOtp` routes)

### Documentation
- `docs/AI/09_DECISIONS.md` — ADR-029, ADR-030, ADR-031
- `docs/AI/04_DATABASE.md` — Administration Domain section, `claim_review_requests`
- `docs/AI/13_OPEN_DECISIONS.md` — item 3 implementation-status update
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` — Sprint 6 complete, Section 17 updated
- `docs/CHANGELOG.md` — new `[Unreleased]` entry

---

## Follow-up Notes for Sprint Planning

- **Sprint 6 (Directory & Listing Claims) is now fully complete.** Both `DIR-001` and `CLM-001` have shipped and
  been signed off.
- **The next genuinely unblocked candidate is `AI-001`** (Conversation/AI Intake, Sprint 7, unblocked by
  `CTG-001`'s real Category domain). This closeout does not plan or start `AI-001` — that remains a separate
  future planning pass, per standing process.
- **`docs/AI/Project_Tracker.xlsx`'s `CLM-001` row** still needs its Status flipped to "Done" — handled separately
  by the CTO's own raw-XML procedure, not performed by this closeout.
- **The Google Places legal review** (`13_OPEN_DECISIONS.md` item 3) remains genuinely open at the legal level —
  now with real, imported production data in play, not just a theoretical future concern. A first-party ToS
  review or legal counsel review should still happen when practical.
