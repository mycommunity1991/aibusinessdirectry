# Checkpoint — Sprint 05, Story VER-001 (Submit My Provider Verification)

**Owner of this checkpoint:** `frontend` (mobile engineer)
**Status:** Mobile half complete, including the architect-review blocking-coupling fix (see "Architect
blocking-issue fix" below). Backend half already merged (commit `0a306d2`, "Add Verification domain backend
module for VER-001"). Awaiting re-review, then user sign-off, before `tech-lead` writes the Walkthrough and
this checkpoint is deleted.

---

## Current task

Implement the mobile (Flutter) half of VER-001 per `docs/implementation/plans/Plan_S05_VER-001.md`, Mobile —
Proposed Changes items 24–33.

## What's done

- New sibling feature module `mobile/lib/features/verification/` — domain models, repository, two Riverpod
  controllers, three screens (S-19 Upload, the OCR-confirm step, S-20 Status).
- New routes wired into `mobile/lib/core/routing/app_routes.dart`/`app_router.dart`:
  `/verification-upload`, `/verification-confirm` (extra-required), `/verification-status`.
- Onboarding wizard's end-of-flow navigation (`business_details_screen.dart`/`freelancer_details_screen.dart`)
  now goes to `verification-upload` instead of `home-placeholder`.
- `storefront_screen.dart` gained a `_VerificationStatusChip` linking to `verification-status` — the only
  `features/provider/` → `features/verification/` coupling besides the wizard's navigation call.
- New dependency `file_picker: ^11.0.3` (pubspec.yaml) — `image_picker` can't select arbitrary files (a trade
  license PDF); flagged for `12_TECH_STACK.md` at story close. `http_parser: ^4.1.2` also added as a *direct*
  dependency (was already transitive via `dio`) since `verification_repository.dart` imports it directly for
  `MultipartFile`'s `contentType`.
- l10n: new English + Arabic strings added to `app_en.arb`/`app_ar.arb` for all three new screens plus the
  Storefront chip; `flutter gen-l10n` run to regenerate.
- Tests: `mobile/test/features/verification/` (fakes + 3 screen test files, 16 test cases) plus updates to
  4 existing `features/provider/` test files whose assertions/overrides needed to reflect the new destination
  or the new Storefront chip's repository dependency.
- `flutter analyze`: 0 issues. `flutter test` (full suite): 130/130 passing.

## Architect blocking-issue fix (post-review)

The architect review flagged `features/provider/` and `features/verification/` importing each other's
repository/controller/domain-model directly (an import cycle, prohibited by `docs/AI/02_ARCHITECTURE.md`).
Fixed:

- Moved `ProviderType` from `features/provider/domain/models/provider_type.dart` to
  `shared/models/provider_type.dart` (content unchanged); updated every import (7 `lib/` files, 6 test files).
- Added `shared/data/current_provider_type_repository.dart` (`CurrentProviderTypeRepository`, calls
  `GET /providers/me` directly, returns `ProviderType?`). `VerificationUploadController` now depends on this
  instead of `features/provider/data/provider_repository.dart` — no more `ProviderException` import either.
- Added `shared/models/verification_status_summary.dart` (`VerificationStatusSummary` enum) and
  `shared/data/verification_status_summary_repository.dart` (calls `GET /providers/me/verification` directly,
  maps to `VerificationStatusSummary?`). `storefront_screen.dart`'s `_VerificationStatusChip` now watches
  `verificationStatusSummaryProvider` instead of importing `features/verification/`'s controller/model.
- `features/verification/`'s own `VerificationStatusScreen`/`VerificationStatusController` untouched (still use
  the full `VerificationRecord` — the richer detail is genuinely needed there).
- Verified via grep: zero `features/verification` imports remain under `features/provider/`, and zero
  `features/provider` imports remain under `features/verification/`.
- New test fakes: `test/shared/fakes/fake_current_provider_type_repository.dart`,
  `test/shared/fakes/fake_verification_status_summary_repository.dart`. Updated
  `verification_upload_screen_test.dart` and `storefront_screen_test.dart` to use them; added a new 4-case
  group in `storefront_screen_test.dart` covering the chip's not-started/under-review/approved/rejected states.
- `flutter analyze`: 0 issues. `flutter test` (full suite): 134/134 passing (130 prior + 4 new chip-state
  tests).

## Deviations from the Plan worth flagging to `tester`/`architect`

1. **422 sub-type disambiguation on `previewDocument`** — the backend's `ErrorResponse` has no machine-readable
   error code, so distinguishing `VerificationDocumentTooLargeError` vs `VerificationDocumentInvalidTypeError`
   (both 422) required matching the backend's exact, fixed default message text in
   `verification_repository.dart`. Documented in code comments. A future backend improvement (an explicit error
   code field) would be cleaner.
2. ~~`VerificationUploadController` reads `ProviderRepository`/`ProviderType` directly~~ — **superseded**, see
   "Architect blocking-issue fix" above: it now reads the shared `CurrentProviderTypeRepository` instead.
3. Business "submit without a document" (Decision 3's default `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED=False`)
   is implemented as a toggle on the Upload screen that skips the confirm step entirely and calls `submit()`
   directly with no document — not explicitly spelled out screen-by-screen in the Plan but required to make
   AC2/Decision 3 reachable from the UI at all.

## What's next

- `tester`/`architect` — re-verify the coupling fix above (grep checks + the four chip-rendering tests).
- Once both report clean and the user signs off, `tech-lead` writes `Walkthrough_S05_VER-001.md`, updates
  `docs/AI/12_TECH_STACK.md` (`file_picker: ^11.0.3`, `http_parser: ^4.1.2`), and deletes this checkpoint.
