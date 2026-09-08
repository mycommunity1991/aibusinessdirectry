# Walkthrough S05 VER-001

## Story: Submit My Provider Verification

**Sprint:** 05 | **Story ID:** VER-001 | **Priority:** Critical | **Status:** Done

As a provider, I want to upload the right identity or license document and see what the system read from it
before submitting, so that I can go live on the platform with confidence my submission is correct.

This is the first story of Sprint 5 ("Provider Verification"), shipping the document-upload half of the
Verification domain: `verification_records`/`verification_documents`, a preview→confirm→submit flow, and the
mandatory-for-Freelancer/configurable-for-Business trust gate. **Scope boundary, stated plainly so it is not
overstated below:** this story only gets a submission into the `pending` queue and lets a provider see their own
current status. It does **not** make any provider discoverable, does not change any verification outcome, and
does not implement any admin review/approval mechanism — a provider can *submit for* verification after this
story; they cannot *get verified* by anything this story shipped. That entire review/approval/cache-update
mechanism is VER-002's job. Full context, architecture decisions, and file-by-file scope:
`docs/implementation/plans/Plan_S05_VER-001.md`.

This story's review process was more eventful than prior ones — a real backend bug was found and fixed during
implementation review, a dead exception class was found and removed by the tester, and the architect's first-pass
review returned **CHANGES REQUIRED** over a genuine mobile architecture violation before a focused re-review
returned **APPROVED WITH RECOMMENDATIONS**. See the dedicated Review Process section below for the honest account
of all three.

---

## What was implemented

### Backend (new `backend/app/modules/verification/` module; `backend/app/shared/storage/` extended)

- **Migration** creating the new `verification` Postgres schema and its two tables, exactly per
  `04_DATABASE.md`'s pre-existing spec: `verification.verification_records` (`provider_id`, `verification_type`,
  `status`, `submitted_at`, `reviewed_at`, `reviewed_by`, `rejection_reason`) and
  `verification.verification_documents` (`verification_record_id`, `document_type`, `file_url`,
  `ocr_extracted_data`), with `idx_verification_records_provider_id`/`idx_verification_records_status`/
  `idx_verification_documents_record_id`. No change of any kind to any `provider`-schema table or column — this
  story never reads or writes `providers.verification_status`/`is_discoverable` anywhere in its code, by
  construction (Decision 2), which is the concrete mechanism behind AC5.
- **Decision 1 — enum reuse:** `verification_records.status` does **not** get its own Postgres enum type.
  It reuses the existing `provider.verification_status` type PRO-002 already created, mapped via
  `postgresql.ENUM(..., name="verification_status", schema="provider", create_type=False)` in the migration and
  `create_type=False` at the ORM level too (`app/modules/verification/models.py` imports `VerificationStatus`
  directly from `app.modules.provider.models`, a pure value-enum import, not a service/repository coupling —
  the same shape ADR-014 already established for `customer` reusing `identity.models.LanguageCode`). Confirmed
  genuine, not just claimed: independently re-verified by the tester against a real scratch database that
  `verification_records.status` and `providers.verification_status` share the same Postgres enum OID, not two
  identically-shaped duplicate types. `verification_type` (`freelancer_id`, `business_license`,
  `business_lightweight`) and `document_type` (`emirates_id`, `trade_license`, `other`) are genuinely new enums,
  colocated in the `verification` schema.
- **Decision 3 — config-driven Business verification bar:** `BUSINESS_VERIFICATION_TYPE` (default
  `business_lightweight`) and `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED` (default `False`) absorb the still-open
  "Business Verification Bar" product decision (`13_OPEN_DECISIONS.md` item 5 — see the recurring documentation
  gap noted below) without a schema or endpoint change once that product decision is finally made. Freelancer is
  never config-driven: a document is always required and always `emirates_id`, a hard business rule per
  `03_DOMAIN_MODEL.md`, not a flag that could be weakened.
- **Decision 4 — endpoint shapes**, a deliberate three-step preview → confirm → submit flow (not one combined
  call), because AC4 requires the OCR fields to be shown and made editable *before* any database row is created:
  `POST /providers/me/verification/documents/preview` (validates + runs the OCR stub + stashes the file to a
  private, deterministic per-provider "pending" slot; writes no DB row), `POST /providers/me/verification`
  (creates the `verification_records` row plus, if applicable, the `verification_documents` row, moving the
  pending file to its permanent location in the same flush), `GET /providers/me/verification` (the caller's
  latest record), `GET /providers/me/verification/documents/{document_id}/file` (authenticated byte stream).
  Because submit always **creates** a new row and never **updates** an existing one, AC7 (resubmission after
  rejection preserves history) is satisfied by construction. `GET /providers/me/verification` is a fixed `/me`
  path returning the *latest* row of a genuinely 1:N table — a deliberate, explicitly-flagged extension of
  ADR-015's singleton rule, not a silent assumption (see the architect's assessment below).
- **Decision 6 — the OCR stub, this codebase's first OCR integration point:** no OCR pipeline, external SDK, or
  Ejari/Emirates-ID integration exists anywhere in this repository (confirmed by a repo-wide grep during
  planning). Rather than guessing at or partially reverse-engineering a pipeline that isn't present,
  `DocumentOcrService` (`backend/app/modules/verification/services/document_ocr_service.py`) is a `Protocol`
  (`async def extract(content, *, document_type) -> DocumentOcrResult`), and the only implementation shipped,
  `StubDocumentOcrService`, always returns an all-`None`, `confidence=0.0` result — honestly, not pretending to
  read anything. `VerificationService` depends on the Protocol, never the stub directly, so a future story can
  add a real implementation with one dependency-wiring change and zero changes to `VerificationService` itself.
  Recorded as **ADR-018** (below).
- **Decision 7 — private vs. public file storage, the single most consequential decision in this story:**
  verification documents (Emirates ID scans, trade licenses) are sensitive data (`06_SECURITY.md`'s Sensitive
  Data list) and must never be reachable through the existing public `/media` `StaticFiles` mount PRO-002 built
  for portfolio photos. `LocalFileStorage` gains one new constructor parameter, `public_url_prefix: str | None`
  (default `"/media"`, preserving PRO-002's exact existing behavior with zero change), and one new `FileStorage`
  Protocol method, `read(url_path) -> bytes`. Verification's own storage wiring uses `public_url_prefix=None` and
  a completely separate, never-mounted root directory (`VERIFICATION_UPLOAD_DIR`, e.g.
  `uploads_private/verification`, added to `.gitignore` alongside the existing `/uploads/` entry). Clients never
  receive a raw path or public URL for a verification document — `GET /providers/me/verification`'s response
  gives a `file_download_url` pointing at this story's own authenticated
  `GET .../documents/{document_id}/file` endpoint, which streams bytes only after `ensure_owner_or_not_found`
  confirms the caller owns the parent record. The preview call writes to a fixed, deterministic,
  per-provider "pending" slot (never a client-supplied token), so an abandoned preview never accumulates beyond
  one file per provider. This held up best of all nine decisions under review: the tester independently verified,
  via real HTTP requests (not just code inspection), that a verification document is never reachable through the
  public media mount's URL shape, and the architect confirmed it cleanly satisfies `06_SECURITY.md` and
  `02_ARCHITECTURE.md`'s "Infrastructure depends on Domain" rule. Recorded as **ADR-019** (below).
- **Decision 8 — new `document_validation.py`**, sharing only the underlying magic-byte signature checks with
  PRO-002's `image_validation.py` (extracted into a new `file_signatures.py`, plus a new `_is_pdf` checker).
  Verification documents can be JPEG/PNG/WEBP/PDF (a trade license is plausibly a PDF), validated against a new
  `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES` (default 10 MB), and — per AC3's explicit "specific, actionable" error
  requirement (the opposite of `image_validation.py`'s deliberately vague philosophy) — raise **distinct**
  exceptions per failure category: `VerificationDocumentTooLargeError` and `VerificationDocumentInvalidTypeError`.
- **Decision 9 — cross-module edge `verification → provider`, read-only:** `VerificationService` depends on
  `provider`'s existing `ProviderService.get_my_provider(user_id)` (a pure read) via constructor injection,
  wired through `verification/dependencies.py` importing `get_provider_service` from `provider/dependencies.py`
  — the identical one-directional, cycle-free shape ADR-014/ADR-016 already established twice. `provider`'s code
  gains zero new imports from `verification`.
- **New exceptions:** `VerificationRecordNotFoundError`, `VerificationDocumentNotFoundError` (404,
  ownership-collapsing per ADR-015), `VerificationSubmissionNotAllowedError` (409), plus the three from Decisions
  8/4 above.
- **Tests**: `test_verification_service.py`, `test_verification_endpoints.py`, `test_document_validation.py`,
  and extensions to `test_local_file_storage.py` — covering upload validation rejections per category (AC3),
  the OCR-confirmation-is-editable requirement (AC4/AC8 — submit's persisted `ocr_extracted_data` matches the
  user's *submitted* `confirmed_fields`, not the stub's raw output), that submission never touches
  `is_discoverable`/`verification_status` (AC5/AC8), resubmission-after-rejection creating a second row with the
  first untouched (AC7), the pending-slot stale-file regression (see Review Process below), and ownership
  boundaries on every `{id}`-addressable route.

### Mobile (new `mobile/lib/features/verification/` module; small `shared/` additions)

- A new, sibling feature module (mirroring the backend's own domain separation) with its own domain models,
  repository, two Riverpod controllers, and three screens: `verification_upload_screen.dart` (**S-19**,
  camera/file picker via the new `file_picker` dependency — `image_picker` alone can't browse an arbitrary PDF),
  a confirm screen (the OCR-confirm step AC4 describes, with copy honestly framed as "we couldn't read this
  automatically yet — please fill it in," matching the stub's honesty per Decision 6, not implying a real read
  happened), and `verification_status_screen.dart` (**S-20**, status badge + rejection copy + a "Resubmit"
  action).
- Route/entry wiring: the Provider onboarding wizard now navigates to the verification-upload route immediately
  after a successful `POST /providers/me`; the Storefront screen (S-25, PRO-002) gained a small verification
  status chip/banner.
- `verification_repository.dart` mirrors the backend's preview/submit/status/document-bytes shapes, streaming
  document bytes through the existing authenticated Dio client rather than a raw `Image.network` URL, consistent
  with Decision 7's private-storage design.

---

## Review Process — a full, honest account

Unlike the more routine prior stories, this one surfaced three distinct, real issues during review, in addition
to the standard clean run. Each is recorded here rather than glossed over.

### 1. A real pending-slot file bug, found and fixed during backend implementation review

The original preview implementation located the pending file by trying each known extension in a fixed order.
If a provider previewed a `.jpg`, then changed their mind and previewed a `.pdf` instead, the `.jpg` was left
behind on disk — orphaned — and a later `submit` call could pick up the *stale* `.jpg` instead of the `.pdf` the
provider had actually just confirmed. This was fixed by having `preview_document` clear every other
known-extension pending slot before writing the new one, so at most one pending file per provider ever exists at
any time, and it is always the most recently previewed one. A dedicated regression test
(`backend/tests/modules/verification/test_verification_service.py`) now exercises exactly this
preview-`.jpg`-then-preview-`.pdf`-then-submit sequence and asserts the submitted document is the `.pdf` and the
stale `.jpg` no longer exists on disk.

### 2. A dead exception class, found by the tester and removed

`InvalidVerificationFieldsError` was defined in the Plan (for malformed `expiry_date`/oversized text fields) but
was never actually raised anywhere in the shipped service code — Pydantic's own field-level validation already
covers those cases before the service layer runs. The tester flagged this as dead code during review; it was
removed. `backend/app/core/exceptions/exceptions.py`'s verification section now has exactly the six exceptions
that are genuinely reachable: `VerificationRecordNotFoundError`, `VerificationDocumentNotFoundError`,
`VerificationSubmissionNotAllowedError`, `VerificationDocumentRequiredError`,
`VerificationDocumentTooLargeError`, `VerificationDocumentInvalidTypeError`.

### 3. A genuine mobile feature-coupling violation, caught on the architect's first pass

The architect's first-pass review returned **CHANGES REQUIRED**, not a clean pass. The finding: the mobile
`features/provider/` and `features/verification/` modules were importing each other's repository, controller,
and domain-model classes directly — `VerificationUploadController` read `features/provider/`'s
`ProviderRepository`/`ProviderType` to resolve the caller's provider type, and Storefront's verification-status
chip read `features/verification/`'s own controller/`VerificationRecord` model directly. This is a bidirectional
import cycle between two features, which `02_ARCHITECTURE.md`'s "Features must not depend directly on each
other" rule explicitly prohibits — a real, correctly-caught architectural violation, not a nitpick.

**The fix:**
- `ProviderType` moved from `features/provider/domain/models/provider_type.dart` to
  `mobile/lib/shared/models/provider_type.dart` (content unchanged; every import across the codebase updated).
- Two new, minimal shared accessors added so neither feature needs to import the other's internals:
  `mobile/lib/shared/data/current_provider_type_repository.dart` (`CurrentProviderTypeRepository`, calls
  `GET /providers/me` directly, returns `ProviderType?`) — now what `VerificationUploadController` depends on
  instead of `ProviderRepository`; and `mobile/lib/shared/data/verification_status_summary_repository.dart`
  (`VerificationStatusSummaryRepository`, calls `GET /providers/me/verification` directly, returns a small
  `VerificationStatusSummary` enum from `mobile/lib/shared/models/verification_status_summary.dart`) — now what
  the Storefront chip watches instead of `features/verification/`'s controller.
- `features/verification/`'s own `VerificationStatusScreen`/`VerificationStatusController` were left untouched —
  they genuinely need the full `VerificationRecord` detail, which is appropriately internal to that feature.
- Verified via grep, both directions: zero `features/verification` imports remain under `features/provider/`,
  and zero `features/provider` imports remain under `features/verification/`.

A focused architect re-review (scoped to just this fix) confirmed the coupling was genuinely resolved and
returned **APPROVED WITH RECOMMENDATIONS** — see the two non-blocking items below.

### Final test counts (post-fix)

- **Backend: 400 tests passing**, 0 regressions.
- **Mobile: 134 tests passing** (130 at the point the coupling issue was first flagged, plus 4 new tests added
  for the fix — a group in `storefront_screen_test.dart` covering the status chip's not-started/under-review/
  approved/rejected states against the new shared repository/fakes).

---

## Acceptance Criteria — Verification

All 8 acceptance criteria (from `Plan_S05_VER-001.md`, sourced from the Tracker) were independently verified by
the `tester` agent, including re-deriving the enum-reuse claim against a real scratch database and confirming
via real HTTP requests that a verification document is never reachable through the public `/media` mount.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `verification_records`/`verification_documents` tables exist via migration, with a 4-value status enum | Pass |
| 2 | Freelancer must submit an Emirates-ID-equivalent document; Business submits per the configured, lighter bar | Pass |
| 3 | Upload validates MIME type, extension, and size before accepting; rejected uploads show a specific, actionable error per category | Pass |
| 4 | Confirmation screen shows OCR-extracted fields as editable, framed as "what we read — please confirm," not fact | Pass |
| 5 | Submitting creates a `pending` `verification_records` row; discoverability unaffected until VER-002 | Pass |
| 6 | Provider can view their own current status but cannot self-approve | Pass |
| 7 | Resubmission after rejection creates a new cycle, preserving history rather than mutating the rejected record | Pass |
| 8 | Automated tests cover upload validation rejections, OCR-confirmation-is-editable, and that submission never changes `is_discoverable` | Pass |

---

## Architect Review — Findings and Resolution

The architect's **first pass** returned **CHANGES REQUIRED** over the mobile feature-coupling violation
described above — a real, correctly-identified issue, not a false positive. Everything else in that first pass
was already sound:

1. **Decision 7 (private/public storage split)** — confirmed sound against `06_SECURITY.md`'s Sensitive Data
   section and `02_ARCHITECTURE.md`'s "Infrastructure depends on Domain" rule; assessed as the part of this
   story that held up best under review.
2. **Decision 1 (enum reuse via `create_type=False`)** — confirmed genuinely correct, not merely claimed,
   against the real `provider.verification_status` type.
3. **Decision 4 (endpoint shapes)** — confirmed against ADR-015, including the flagged "fixed `/me` path over
   the *latest* row of an N-cardinality table" nuance: the architect explicitly assessed this as a legitimate,
   deliberate extension of ADR-015 (not a violation), with one **non-blocking naming recommendation** (below).
4. **Decision 9 (`verification → provider` cross-module edge)** — confirmed consistent with ADR-014/ADR-016's
   established pattern.
5. **Decision 3 (config-driven Business bar)** — confirmed consistent with `04_DATABASE.md` Section 14's own
   stated intent.

Once the coupling fix landed, a focused architect **re-review** (scoped to the fix, not a full re-derivation of
items 1–5 above) confirmed it and returned **APPROVED WITH RECOMMENDATIONS**.

### Non-blocking recommendations (2)

1. **Endpoint-naming suggestion, not a requirement:** consider renaming `GET /providers/me/verification` to
   `GET /providers/me/verification/current` in a future story, to make the "fixed path over the *latest* row of
   a genuinely 1:N table" nuance more self-documenting in the URL itself. Not required now — the current shape is
   a legitimate ADR-015 extension, per the architect's own assessment above.
2. **Minor message-precision issue, not a blocker:** `VerificationDocumentRequiredError` is reused for a
   Freelancer submission whose `document_type` is present but wrong (not `emirates_id`) as well as for the "no
   document at all" case — the error copy ("Please upload and confirm your document before submitting.") is
   slightly imprecise for the wrong-type case specifically. A future story could split this into a distinct,
   more accurate exception if this UX detail becomes worth polishing further.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-018** (the swappable `DocumentOcrService` Protocol /
  `StubDocumentOcrService`, this codebase's first OCR integration point, explicitly interim) and **ADR-019**
  (the private-vs-public `FileStorage` split — `public_url_prefix`, the separate never-mounted
  `VERIFICATION_UPLOAD_DIR` root, the authenticated streaming-download endpoint pattern). ADR-019 is recorded
  second even though Decision 7 is called out as the single most consequential decision in this story, because
  ADR-018 (the OCR Protocol) is the simpler, more foundational "first integration point" pattern that ADR-019's
  storage split is then built alongside; either ordering was left open by the Plan for the tech-lead to finalize,
  and this ordering keeps the OCR/storage decisions grouped in the same order they appear in the Plan's own
  Decision numbering (6 then 7).
- **`docs/AI/04_DATABASE.md`** — confirmed the `verification.verification_records`/`verification.verification_documents`
  tables match the pre-existing spec exactly (no column-level changes needed); added an explicit note under the
  Verification Domain section documenting the `create_type=False` enum-reuse mechanism (`verification_records.status`
  shares `provider.verification_status`'s Postgres enum type rather than duplicating it) — a genuine, documented
  deviation from a naive "colocate every enum in its own domain schema" reading.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — Sprint 5 table added with VER-001 marked done; Executive
  Summary, Current Backend Capabilities, Repository State, Current Limitations, Overall Progress, and Next
  Planned Story sections updated. Stated carefully, per the story's own scope boundary: VER-001 lets a provider
  submit into the `pending` queue and view their own status — it does **not** make any provider discoverable or
  resolve any verification outcome; that remains entirely VER-002's job (admin review/approval, the
  `providers.verification_status`/`is_discoverable` cache update, notification sending). VER-002 ("Review
  provider verification as an administrator") is next, and is now unblocked.
- **`docs/AI/12_TECH_STACK.md`** — already documented `file_picker`/`http_parser` (added by the orchestrating
  session during mobile implementation); verified present, not duplicated here.
- `docs/CHANGELOG.md` — new entry under `[Unreleased]`.

### Flagged, not fixed by this closeout (outside tech-lead's tool access / ownership)

- `docs/AI/Project_Tracker.xlsx`'s Stories sheet still needs its VER-001 row's Status updated from "Planned" to
  "Done" — requires the direct raw-XML cell-patching method established at prior closeouts (a normal openpyxl
  load/save round-trip was found to silently drop this workbook's conditional-formatting extensions). Not
  performed here; no xlsx-editing tool is available to this agent.
- **`docs/AI/13_OPEN_DECISIONS.md` still does not exist anywhere in the repository.** This is now a
  **three-strikes documentation gap**: PRO-001, PRO-002, and now VER-001's own Plan have each independently
  flagged this file's absence, and each has had to route around one of its cited-but-undocumented open items
  (Category Taxonomy for PRO-001/PRO-002; the Business Verification Bar, item 5, for this story's Decision 3).
  Flagging it a fourth time and moving on is no longer the right response — this should get real attention as
  its own piece of work (creating the file with at minimum the items already cited by name across
  `03_DOMAIN_MODEL.md`, `04_DATABASE.md`, `14_USER_FLOWS.md`, `15_SCREEN_INVENTORY.md`, and
  `PROJECT_IMPLEMENTATION_STATE.md`), rather than being deferred a fifth time by whatever story ships next.

---

## Testing Performed

- `cd backend && uv run pytest -q` — **400/400 passing**, 0 regressions — independently re-run and confirmed by
  the `tester` agent from a clean shell.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` —
  verified against a disposable scratch database; the enum-reuse claim (Decision 1) independently re-derived by
  inspecting the real Postgres enum OIDs, not merely trusted from the migration's own code comment.
- Real HTTP requests (not just code inspection) confirmed a verification document is never reachable through the
  public `/media` mount's URL shape — it 404s, since it was never written there at all (Decision 7).
- `cd mobile && flutter test` — **134/134 passing** (130 at the point the coupling issue was first caught, +4 new
  chip-state tests added with the fix) — independently re-run and confirmed by the `tester` agent.
- `cd mobile && flutter analyze` — 0 issues, both before and after the coupling fix.
- `tester` agent: all 8 ACs independently verified with direct evidence — see table above.
- `architect` agent: first pass **CHANGES REQUIRED** (mobile feature-coupling violation); focused re-review after
  the fix returned **APPROVED WITH RECOMMENDATIONS** — see findings above.
- User sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/*_verification_domain.py` (new — creates the `verification` schema, both tables,
  `verification_type`/`document_type` enums)
- `backend/app/modules/verification/models.py` — `VerificationType`, `DocumentType`, `VerificationRecord`,
  `VerificationDocument` (imports `VerificationStatus` from `app.modules.provider.models`)
- `backend/app/modules/verification/repositories/{verification_record_repository,verification_document_repository}.py`
- `backend/app/modules/verification/services/{document_ocr_service,verification_service}.py`
- `backend/app/modules/verification/{schemas,api,dependencies}.py`
- `backend/app/shared/storage/{interfaces,local_file_storage}.py` — `public_url_prefix`, new `read()` method
- `backend/app/shared/storage/{file_signatures,document_validation}.py` (new); `image_validation.py` (refactored
  to import from `file_signatures.py`)
- `backend/app/core/config.py` — `VERIFICATION_UPLOAD_DIR`, `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES`,
  `BUSINESS_VERIFICATION_TYPE`, `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED`; `.gitignore` — `/uploads_private/`
- `backend/app/core/exceptions/exceptions.py` — six new verification exceptions (see Review Process item 2)
- `backend/tests/modules/verification/{test_verification_service,test_verification_endpoints}.py` (new)
- `backend/tests/shared/storage/test_document_validation.py` (new); `test_local_file_storage.py` (extended)

### Mobile
- `mobile/lib/features/verification/` (new module — domain models, repository, two controllers, three screens)
- `mobile/lib/shared/models/provider_type.dart` (moved from `features/provider/`, coupling fix)
- `mobile/lib/shared/models/verification_status_summary.dart` (new, coupling fix)
- `mobile/lib/shared/data/{current_provider_type_repository,verification_status_summary_repository}.dart` (new,
  coupling fix)
- `mobile/lib/features/provider/presentation/screens/storefront_screen.dart` — `_VerificationStatusChip`, now
  reading the shared `VerificationStatusSummaryRepository` instead of `features/verification/`'s controller
- `mobile/pubspec.yaml` — `file_picker: ^11.0.3`, `http_parser: ^4.1.2` (promoted from transitive to direct)
- `mobile/test/features/verification/` (new — fakes + 3 screen test files)
- `mobile/test/shared/fakes/{fake_current_provider_type_repository,fake_verification_status_summary_repository}.dart`
  (new, coupling fix)

---

## Follow-up Notes for Sprint Planning

- **Sprint 5 (Provider Verification) has its first story, VER-001, complete.** VER-002 ("Review provider
  verification as an administrator") is next and is now unblocked — it will add the admin review/approve/reject
  transition, the `providers.verification_status`/`is_discoverable` cache-update hook, and the associated
  notification send, none of which this story implements.
- Non-blocking follow-ups carried forward: the two architect recommendations above (the `/verification/current`
  naming suggestion; the imprecise `VerificationDocumentRequiredError` reuse for the wrong-document-type case);
  the pending-slot design remains capped at one file per provider by construction, with no active cleanup job
  needed at this scale; a real OCR integration remains a distinct future story once the actual pipeline's
  interface is confirmed to exist.
- **Cross-story documentation gap, now flagged a third time — recommend real follow-up, not a fourth flag:**
  `docs/AI/13_OPEN_DECISIONS.md` still does not exist, despite being cited by name across multiple `docs/AI/`
  documents. PRO-001/PRO-002 routed around its "Category Taxonomy" item; this story routed around its "Business
  Verification Bar" item (item 5) via Decision 3's config-driven approach. The next story that needs to cite this
  file should not have to flag its absence a fourth time.
