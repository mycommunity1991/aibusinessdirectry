**Active Story:** Sprint 5 | VER-001 | Submit My Provider Verification

**Story:**
As a provider, I want to upload the right identity or license document and see what the system read from it
before submitting, so that I can go live on the platform with confidence my submission is correct.

This is the first story of Sprint 5 and the first story of a genuinely new domain (`verification`) — no
`backend/app/modules/verification/` or mobile `features/verification/` code exists yet. It builds
`verification_records`/`verification_documents`, an OCR-assisted confirmation step (stubbed — see below), and
the mandatory-for-Freelancer / configurable-for-Business trust gate's *submission* side only.

**Scope boundary:** does NOT include the admin review/approval side (VER-002) — no `admin_action_log` writes, no
notification sending, no status-transition endpoint of any kind, no reading or writing of
`providers.verification_status`/`is_discoverable` anywhere in this story. This story only gets a submission into
the pending queue correctly and lets the provider view their own current status.

---

## Technical Context & Architecture Constraints

- `docs/AI/04_DATABASE.md` already fully specifies `verification.verification_records` and
  `verification.verification_documents` column-for-column, plus the `verification_status`/`verification_type`/
  `document_type` enums. **`verification_records.status` must reuse the existing `provider.verification_status`
  Postgres enum type** (`postgresql.ENUM(..., name="verification_status", schema="provider",
  create_type=False)`) — do **not** create a second, duplicate enum type. `provider/models.py`'s `_pg_enum`
  helper left an explicit comment instructing exactly this at PRO-002's close. Import `VerificationStatus`
  directly from `app.modules.provider.models` into the new `verification` module (a pure value-enum import, the
  same shape ADR-014 already established for `identity.models.LanguageCode` — not a service/repository
  coupling). `verification_type`/`document_type` are genuinely new enums, colocated in the new `verification`
  schema.
- **New top-level module, `backend/app/modules/verification/`** — Verification is its own domain, its own
  Postgres schema, its own lifecycle (accumulates history over time, unlike Provider's one-time creation). Do
  not add this code to `backend/app/modules/provider/`. Its router is still mounted under
  `/providers/me/verification` (`backend/app/api/v1/api.py`) — code and URL are decoupled on purpose; see Plan
  Decision 5.
- **No OCR pipeline exists anywhere in this codebase** — confirmed by a repo-wide search; nothing resembling
  "the existing Ejari/Emirates ID pipeline" is present in `backend/`. Build a small `DocumentOcrService`
  Protocol (`async def extract(content, *, document_type) -> DocumentOcrResult`) with exactly one
  implementation, `StubDocumentOcrService`, that **always** returns every field as `None`/`confidence=0.0`,
  regardless of the file's actual content. Do not attempt any real text extraction, regex heuristics, or
  third-party OCR call — this is a genuine stub, not a "best-effort" implementation. Wire it via DI so a real
  implementation can later replace it with one new class and one wiring-line change (mirrors ADR-017's
  `FileStorage` swappability exactly).
- **Two-call preview → submit flow, not a single combined upload+submit call** (Plan Decision 4). AC4's own
  wording ("After upload... a confirmation screen... Submitting creates a `verification_records` row")
  describes upload and submit as genuinely separate steps, with nothing persisted to the database until submit:
  - `POST /providers/me/verification/documents/preview` (multipart: `file`, `document_type`) — validates the
    upload, runs the OCR stub, saves the file to a **private**, deterministic per-provider "pending" slot
    (never a randomly generated token — see below), returns the (empty) extracted fields. Writes **no** DB row.
  - `POST /providers/me/verification` (JSON: `document_type?`, `confirmed_fields: {full_name?, id_number?,
    expiry_date?}`) — the user's final, possibly-edited values. Creates the `verification_records` row
    (`status=pending`) and, if a document is involved, the `verification_documents` row
    (`ocr_extracted_data` = the submitted `confirmed_fields`, **not** whatever the stub returned at preview
    time — this distinction is exactly what AC8's "OCR-confirmation-is-editable" test must prove). Rejects
    (409) unless the caller has no prior record or their latest record is `rejected` — this is what makes AC7
    ("resubmission... creates a new verification cycle... preserving history") true by construction: the code
    only ever `create`s a new row, never `update`s an existing one.
  - `GET /providers/me/verification` — the caller's single latest record + its documents, or 404. Reads
    `verification_records` directly, **never** `providers.verification_status` (which is a cache VER-002 alone
    is responsible for updating) — this avoids showing a stale "rejected" status immediately after a
    successful resubmission.
  - `GET /providers/me/verification/documents/{document_id}/file` — streams one of the caller's own document's
    bytes. `ensure_owner_or_not_found` via the document → record → `provider_id` chain is load-bearing here.
  - **No endpoint anywhere accepts `status`/`reviewed_at`/`reviewed_by`/`rejection_reason`** — this is what
    makes AC6's "cannot self-approve" true structurally, not just by convention.
- **Verification documents must never be served through the existing public `/media` `StaticFiles` mount** —
  this is the single most important constraint in this story. Emirates ID scans and trade licenses are far more
  sensitive PII than portfolio photos, and `/media` has no authentication at all. Store them under a **second,
  separate root** (`VERIFICATION_UPLOAD_DIR` setting, never mounted as static files). Extend
  `backend/app/shared/storage/local_file_storage.py`'s `LocalFileStorage` with a `public_url_prefix: str | None
  = "/media"` constructor parameter (default preserves PRO-002's exact existing portfolio behavior, zero
  regression) — when `None`, `save()` returns a bare storage-relative reference instead of a `/media/...` URL.
  Add `async def read(self, url_path: str) -> bytes` to both the `FileStorage` Protocol
  (`backend/app/shared/storage/interfaces.py`) and `LocalFileStorage` (additive; `PortfolioService` never calls
  it, so this cannot regress PRO-002). Clients only ever reach a verification document through the authenticated
  `GET .../documents/{document_id}/file` endpoint — never a raw URL. The "pending" preview slot uses a
  **fixed, deterministic path per provider** (`pending/{provider_id}{extension}` under
  `VERIFICATION_UPLOAD_DIR`) — never a client-supplied or randomly-generated token — so each new preview
  overwrites the last and disk usage is naturally bounded to one file per provider, with no rate limiting or
  cleanup job needed. On a successful submit, move the pending file to a permanent, cycle-specific path and
  delete the pending slot. Add `/uploads_private/` to `backend/.gitignore`.
- **Do not reuse `image_validation.py` unmodified for documents.** It's portfolio-specific (its own exception
  type, its own size setting, images only, and a deliberately *vague* error). AC3 explicitly wants a
  **specific, actionable** error — the opposite of that vagueness. Extract the shared magic-byte checkers
  (`_is_jpeg`/`_is_png`/`_is_webp`) into a new `backend/app/shared/storage/file_signatures.py`, add `_is_pdf`,
  and have `image_validation.py` import from there (small, behavior-preserving refactor — no test changes
  expected). Add a new `backend/app/shared/storage/document_validation.py` (`.jpg`/`.jpeg`/`.png`/`.webp`/
  `.pdf` allowed, new `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES` setting, default 10 MB) that raises **distinct**
  exceptions per failure category (`VerificationDocumentTooLargeError`, `VerificationDocumentInvalidTypeError`)
  with plain, actionable messages.
- **Business verification bar is config-driven, not hardcoded** (`13_OPEN_DECISIONS.md` item 5 remains
  unresolved and the file itself still doesn't exist — confirmed). New settings:
  `BUSINESS_VERIFICATION_TYPE` (default `business_lightweight`) and
  `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED: bool = False`. When the latter is `False` (the default), a Business
  provider may submit with no document reference at all (zero `verification_documents` rows for that cycle —
  the schema's 1:N relationship already permits N=0). Freelancer is never config-driven: always
  `verification_type=freelancer_id`, always requires a document, and the accepted `document_type` is
  restricted to `emirates_id` only (AC2's literal wording).
- **New cross-module dependency, `verification → provider`, read-only**: `VerificationService` depends on
  `provider`'s existing `ProviderService.get_my_provider(user_id)` (constructor injection, the same shape
  ADR-014/ADR-016 already established twice) to resolve the caller's own Provider id/`provider_type`. No write
  path into any `provider`-schema table anywhere in this story — do not import `ProviderRepository`'s write
  methods, and do not add any migration or code touching the `providers` table itself.
- Full detail, file-by-file, is in `docs/implementation/plans/Plan_S05_VER-001.md` — follow it, including all 9
  numbered Architecture Decisions and the Verified Current State section.

---

## Implementation Instructions

### Backend
1. New Alembic migration (down-revision = current head — confirm via `alembic heads`): `verification` schema,
   new `verification_type`/`document_type` enums, `verification_records` (status column reusing
   `provider.verification_status` via `create_type=False`), `verification_documents` — with all
   constraints/indexes from `04_DATABASE.md`. No change to any `provider`-schema table. Verify upgrade and
   downgrade both work against a scratch database.
2. Add `backend/app/modules/verification/models.py`: `VerificationType`/`DocumentType` enums +
   `_pg_enum` helper; `VerificationRecord`/`VerificationDocument` models (import `VerificationStatus` from
   `app.modules.provider.models`).
3. Add `backend/app/modules/verification/repositories/`: `verification_record_repository.py`
   (`get_latest_for_provider`), `verification_document_repository.py` (`list_for_record`, `get_by_id`).
4. Add `backend/app/modules/verification/services/document_ocr_service.py`: `DocumentOcrResult`,
   `DocumentOcrService` Protocol, `StubDocumentOcrService` (always empty output).
5. Add `backend/app/modules/verification/services/verification_service.py`:
   `VerificationService(provider_service, verification_record_repository, verification_document_repository,
   verification_file_storage, document_ocr_service)` with `preview_document`, `submit`,
   `get_my_current_status`, `get_document_bytes` — per the Plan's Decision 4/7 mechanics exactly (pending-slot
   path, resubmission-eligibility check, ownership enforcement on document download).
6. Extend `backend/app/shared/storage/interfaces.py` (`FileStorage` gains `read()`),
   `local_file_storage.py` (`public_url_prefix` param), add `file_signatures.py` (extracted checkers + `_is_pdf`),
   update `image_validation.py` to import from it, add `document_validation.py`
   (`validate_verification_document_upload`).
7. Add new settings to `backend/app/core/config.py`: `VERIFICATION_UPLOAD_DIR`,
   `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES`, `BUSINESS_VERIFICATION_TYPE`,
   `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED`. Add `/uploads_private/` to `backend/.gitignore`.
8. Add exceptions to `backend/app/core/exceptions/exceptions.py` + `__init__.py`:
   `VerificationRecordNotFoundError` (404), `VerificationDocumentNotFoundError` (404, ownership-collapsing),
   `VerificationSubmissionNotAllowedError` (409), `VerificationDocumentRequiredError` (422),
   `VerificationDocumentTooLargeError` (422), `VerificationDocumentInvalidTypeError` (422),
   `InvalidVerificationFieldsError` (422).
9. Add `backend/app/modules/verification/schemas.py` per the Plan (no `status`/`reviewed_*`/`rejection_reason`
   field on any request schema).
10. Add `backend/app/modules/verification/api.py`: the four routes listed above, all bare-authenticated
    (mirrors PRO-002 Decision 7's reasoning).
11. Add `backend/app/modules/verification/dependencies.py`, importing `get_provider_service` from
    `app.modules.provider.dependencies`.
12. Register the router in `backend/app/api/v1/api.py` (`prefix="/providers/me/verification"`). Add
    `import app.modules.verification.models` to `backend/tests/conftest.py`'s `db_engine` fixture (ADR-013
    pattern).
13. Write tests per the Plan's items 20–23: service-level (upload validation categories, OCR-editable
    persistence, `is_discoverable`/`verification_status` never touched, resubmission-after-rejection creates a
    new row, duplicate-pending submission rejected), endpoint-level (full HTTP round trip, ownership on GET and
    document download), and `shared/storage` tests (`document_validation.py`, `LocalFileStorage`'s
    `public_url_prefix=None`/`read()` behavior, plus a regression check that the existing portfolio
    (`public_url_prefix="/media"`) behavior is unchanged).

### Mobile
14. Add a new `mobile/lib/features/verification/` module (sibling to `features/provider/`, not nested inside
    it) — `domain/models/` (`verification_record.dart`, `verification_document.dart`, `document_type.dart`,
    `ocr_preview_result.dart`, `submit_verification_request.dart`, `verification_exception.dart`),
    `data/verification_repository.dart` (`previewDocument`, `submit`, `getMyCurrentStatus` returns `null` on
    404, `getDocumentBytes`), `state/` controllers.
15. Add screens: `verification_upload_screen.dart` (S-19 — document picker, calls `previewDocument`),
    `verification_confirm_screen.dart` (editable fields pre-filled from the — empty — preview response,
    honest "we couldn't read this automatically yet, please fill it in" framing, a locally-rendered thumbnail
    of the picked file, "Submit" calls `submit()`), `verification_status_screen.dart` (S-20 — status badge +
    plain-language copy per `16_UX_GUIDELINES.md`'s mapping table, "Resubmit" on rejection routes back to S-19,
    empty/first-time state when no record exists yet).
16. Wire navigation: the Provider onboarding wizard (PRO-001) now routes to `verification-upload` immediately
    after a successful `POST /providers/me`, instead of ending at a stub. Add a small verification-status
    chip/banner to the existing Storefront screen (S-25, PRO-002) linking to `verification-status`.
17. Write tests: one per new screen (confirm-screen fields are genuinely editable and submitted edits, not the
    stub's raw response, per AC4/AC8), a `fake_verification_repository.dart` following the existing
    `fake_provider_repository.dart` shape, an ownership test confirming a second account's verification data is
    never fetched/displayed.

### Both
18. Confirm `pytest` (backend) and `flutter test` (mobile) pass, plus `ruff check`/`ruff format --check` and
    `flutter analyze`.
19. Do not implement anything in the Plan's "Explicitly Out of Scope" section (VER-002's admin review/approval/
    notifications/`admin_action_log`, any write to `providers.verification_status`/`is_discoverable`, a
    verification-history browsing endpoint, a real OCR integration, malware scanning, the Provider Dashboard,
    Claim-Your-Listing's own gate, or resolving the actual Business-verification-bar product decision).

---

## Definition of Done

- All 8 acceptance criteria in `docs/AI/Project_Tracker.xlsx` (VER-001 row) are met, verified by `tester`
  against each one individually — see the Plan's Verification Plan table for exactly what each AC's test must
  prove.
- `verification_records`/`verification_documents` match `04_DATABASE.md` column-for-column, with `status`
  confirmed to reuse (not duplicate) the existing `provider.verification_status` Postgres enum type; migration
  upgrade/downgrade both verified.
- A Freelancer provider cannot submit without an `emirates_id` document; a Business provider can submit under
  the default lighter config with no document at all (AC2).
- Every upload-rejection category (size, extension, magic-byte mismatch) produces its own specific, actionable
  message — never one generic string (AC3).
- The confirmation screen's fields are genuinely editable, and the values actually persisted on submit are the
  user's edited values, not the OCR stub's raw (empty) output (AC4/AC8).
- A successful submission never changes `providers.is_discoverable` or `providers.verification_status` —
  proven by reading the actual service code, not merely by a passing test that doesn't check (AC5/AC8).
- A provider can view their own current status; no endpoint anywhere accepts a `status`/`reviewed_*` field,
  making self-approval structurally impossible, not just conventionally forbidden (AC6).
- A resubmission after a rejection creates a brand-new `verification_records` row; the prior (rejected) row's
  fields are never mutated (AC7).
- Verification documents are never reachable through the public `/media` mount — confirmed by an explicit test
  attempting the public-path shape and asserting it 404s.
- Backend and mobile automated test suites pass; lint/format clean on both sides.
- Upon `tester`/`architect` clean verdicts, pause for explicit user sign-off before the Walkthrough is written
  or the changelog/tracker is touched. If approved: record the OCR-protocol swappability pattern and the new
  `verification → provider` cross-module edge as the next two ADRs (**ADR-018**, **ADR-019** — tech-lead to
  finalize exact numbering/ordering at story close) in `09_DECISIONS.md`; update `04_DATABASE.md` (confirm the
  new `verification` schema tables match spec, document the `create_type=False` enum-reuse); flag
  `13_OPEN_DECISIONS.md`'s continued non-existence again, as PRO-001/PRO-002 both already did.
