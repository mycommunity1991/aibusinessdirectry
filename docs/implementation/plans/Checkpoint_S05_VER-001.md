# Checkpoint — Sprint 05, Story VER-001 (Submit My Provider Verification)

**Owner of this checkpoint:** `frontend` (mobile engineer)
**Status:** Mobile half complete. Backend half already merged (commit `0a306d2`, "Add Verification domain
backend module for VER-001"). Awaiting `tester` and `architect` review, then user sign-off, before `tech-lead`
writes the Walkthrough and this checkpoint is deleted.

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

## Deviations from the Plan worth flagging to `tester`/`architect`

1. **422 sub-type disambiguation on `previewDocument`** — the backend's `ErrorResponse` has no machine-readable
   error code, so distinguishing `VerificationDocumentTooLargeError` vs `VerificationDocumentInvalidTypeError`
   (both 422) required matching the backend's exact, fixed default message text in
   `verification_repository.dart`. Documented in code comments. A future backend improvement (an explicit error
   code field) would be cleaner.
2. **`VerificationUploadController` reads `ProviderRepository`/`ProviderType`** (a read-only, one-directional
   dependency) to gate Freelancer-vs-Business document-type choice — mirrors the backend's own Decision 9
   (`verification → provider`, read-only). This is the one place `features/verification/` reads from
   `features/provider/` beyond the two explicitly-permitted navigation links; reasoned through explicitly in
   code comments as intentional, not an oversight.
3. Business "submit without a document" (Decision 3's default `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED=False`)
   is implemented as a toggle on the Upload screen that skips the confirm step entirely and calls `submit()`
   directly with no document — not explicitly spelled out screen-by-screen in the Plan but required to make
   AC2/Decision 3 reachable from the UI at all.

## What's next

- `tester` — verify AC2/AC3/AC4/AC6 (mobile half) per `Plan_S05_VER-001.md`'s Verification Plan table.
- `architect` — review the two deviations above.
- Once both report clean and the user signs off, `tech-lead` writes `Walkthrough_S05_VER-001.md`, updates
  `docs/AI/12_TECH_STACK.md` (file_picker), and deletes this checkpoint.
