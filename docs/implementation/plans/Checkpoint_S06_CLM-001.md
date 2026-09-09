# Checkpoint — S06 CLM-001 (Claim My Google-Seeded Business Listing)

**Owner of this checkpoint:** `frontend` (Mobile Engineer)
**Status:** Mobile implementation complete, `flutter analyze`/`dart format`/full `flutter test` all clean. Ready for `tester` and `architect` review.
**Backend status:** Already implemented and pushed (commit `9852545`), per the task that launched this work — not touched by this checkpoint.

---

## What's done (Mobile Proposed Changes, Plan items 31–43)

### `features/search` extension (Decision 8)
- `mobile/lib/features/search/domain/models/search_result_provider.dart` — added required `isClaimed: bool`, parsed from `is_claimed`.
- `mobile/lib/features/search/presentation/widgets/provider_search_card.dart` — renders a full-width, solid `AppColors.warning` banner (new `AppColors.onWarning` added for contrast) with the exact locked copy `"Unclaimed — Is this your business? Claim it"` when `isClaimed == false`, never otherwise. Added `onClaimTap` callback (separate from the existing `onTap`), so the banner's CTA and the rest of the card can navigate differently.
- `mobile/lib/features/search/presentation/screens/search_results_screen.dart` — wires `onClaimTap` to `context.push(AppRoutes.claimOtp, extra: provider.id)`, skipping the Claim Search screen entirely (Decision 8's explicit design).

### New feature `mobile/lib/features/claim/`
- `domain/models/claim_search_result.dart`, `claim_result.dart`, `claim_review_reason.dart`, `claim_exception.dart`.
- `data/claim_repository.dart` — `searchUnclaimed`, `requestOtp`, `verifyOtp`, `requestAdminReview`, each mapping backend errors (404/409/429/400) to a plain-language `ClaimException`.
- `presentation/screens/claim_search_screen.dart` (S-21) + `claim_otp_screen.dart` (S-22).
- `presentation/utils/claim_error_copy.dart`.
- `state/claim_search_controller.dart`, `state/claim_otp_controller.dart` (Riverpod `StateNotifier`s, all business logic here, not in widgets).
- `core/routing/app_routes.dart` / `app_router.dart` — new `claimSearch`/`claimOtp` routes; `claimOtp` requires `extra: providerId` (String), mirrors `otpEntry`'s `extra`-required redirect pattern.

### Entry point
- `mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` — added a secondary `TextButton` ("Already listed on Google? Claim your business") opening `claimSearch` directly, independent of stumbling onto a card in search results.

### The no-public-number edge case (AC6)
`ClaimOtpController._requestInitialOtp()` catches `ClaimErrorType.publicNumberUnavailable` specifically (backend 409, raised *before* any OTP is sent) and calls `_submitReview(ClaimReviewReason.noPublicNumber, auto: true)` — skipping the code-entry UI entirely and landing straight on the `reviewConfirmed` state. Covered by `claim_otp_screen_test.dart`'s last test case.

### l10n
All new/changed strings added to both `lib/l10n/app_en.arb` and `lib/l10n/app_ar.arb` (this codebase keeps both fully in sync); `flutter gen-l10n` re-run successfully.

### Tests
- `mobile/test/features/search/provider_search_card_test.dart` (new).
- `mobile/test/features/claim/claim_search_screen_test.dart`, `claim_otp_screen_test.dart` (new).
- `mobile/test/features/claim/fakes/fake_claim_repository.dart`, `mobile/test/features/claim/test_helpers.dart` (new).
- Updated `mobile/test/features/search/search_results_screen_test.dart` fixtures for the new required `isClaimed` field.

**Full suite: 157/157 passing. `flutter analyze`: no issues. `dart format --set-exit-if-changed`: clean.**

---

## Deviations from the Plan / notes for `tester`/`architect`

1. **Banner color:** Plan/Decision 8 says solid Warning (`#F59E0B`), but `docs/AI/DESIGN.md`'s `badge-unclaimed` component uses the softer `warning-container`/`on-warning-container` pair instead. I used the solid `warning`/new `onWarning` (`#3F2E00`, DESIGN.md's own `on-warning` token) pair for the full-width banner specifically, since `16_UX_GUIDELINES.md`'s literal resolved pattern for *this exact banner* says solid Warning, and that document governs the interaction/behavior design here — `badge-unclaimed` remains available for any future smaller unclaimed indicator. Flagged for `architect` to confirm this reading is correct, since it's a case where two docs under `docs/AI/`/`DESIGN.md` could be read as being in tension.
2. **"This isn't working" reason sheet, second option:** the Plan's item 36 names two sheet options ("I didn't receive a code" / "This isn't my business's number"), but the backend's `RequestClaimAdminReviewRequest.reason` only accepts `otp_failed`/`no_public_number`, and `no_public_number` is structurally only reachable via the auto-submit path (a listing with no public number never reaches the code-entry screen at all). Both manual sheet options therefore submit `reason=otp_failed` — documented in `claim_review_reason.dart`'s doc comment. Flagged for `architect`/`tester` to confirm this is the intended reading of AC6, not a gap.
3. Did not add a Provider Profile (S-09) banner — confirmed out of scope (Decision 8 explicitly, S-09 doesn't exist yet).

## Cross-feature import boundary (explicitly checked)

Grepped every import in `features/claim/` and `features/search/` — neither imports the other's internals, and neither imports `features/provider/` internals. The only cross-feature edge either module has is `features/search/state/search_filters_controller.dart` → `features/customer/...` (`SavedAddressRepository`), which is the pre-existing, already-logged exception (`docs/AI/13_OPEN_DECISIONS.md` item 12) — not extended or added to by this story. `core/routing/app_router.dart` is the only file that imports screens from `claim`/`search`/`provider` together, which is expected (it's core routing infrastructure, not a feature).

## Next steps

- `tester`: verify against the 8 ACs' mobile-relevant slices (AC2, AC3, AC4/AC5/AC6's mobile behavior) per the Plan's Verification Plan table; pay particular attention to the two flagged deviations above.
- `architect`: review the banner color reasoning and the reason-sheet/backend-enum mapping; confirm the claim feature's module boundaries.
- Once both report clean, this checkpoint should be deleted per the Continuity & Checkpointing rule once `tech-lead` writes the Walkthrough after user sign-off.
