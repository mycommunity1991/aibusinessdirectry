# Plan for Story VER-001 — Submit My Provider Verification

**Sprint:** 05 (Provider Verification) | **Epic:** ML5-EP01 | **Priority:** Critical | **Depends On:** PRO-001
(done, merged to this branch). **Not** dependent on PRO-002, confirmed directly from the Tracker row supplied
for this story (superseding `PROJECT_IMPLEMENTATION_STATE.md` Section 17's earlier, hedged caveat about not
being able to independently open the Tracker).

---

## Story

As a provider, I want to upload the right identity or license document and see what the system read from it
before submitting, so that I can go live on the platform with confidence my submission is correct.

This story implements the Verification domain's document-upload half: `verification_records`/
`verification_documents`, an OCR-assisted confirmation step, and the mandatory-for-Freelancer /
configurable-for-Business trust gate. The OCR integration itself is stubbed pending confirmation of the
existing Ejari/Emirates ID pipeline's interface — this story does not build a new OCR engine from scratch.

**Scope boundary:** does not include the admin review/approval side (VER-002) — no `admin_action_log` writes, no
notification sending, no `PATCH`/status-transition endpoint of any kind. This story only gets a submission into
the pending queue correctly and lets the provider see their own current status. `providers.verification_status`/
`is_discoverable` are never read or written by any code this story adds (see Decision 2) — those remain exactly
as PRO-001 set them until VER-002 ships.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`, as supplied)

1. `verification_records` and `verification_documents` tables exist via migration, with a status enum (pending,
   under_review, approved, rejected).
2. Freelancer providers must submit an Emirates-ID-equivalent document; Business providers submit per the
   configured (lighter) verification bar.
3. Upload validates MIME type, extension, and file size before accepting; rejected uploads show a specific,
   actionable error.
4. After upload, a confirmation screen shows OCR-extracted fields (name, ID number, expiry date where
   applicable) as editable, with copy explicitly framing them as "what we read — please confirm," not as
   already-verified fact.
5. Submitting creates a `verification_records` row with `status=pending`; the provider's discoverability is
   unaffected until VER-002 processes it.
6. A provider can view their own current verification status but cannot self-approve.
7. Resubmission after a rejection creates a new verification cycle rather than mutating the rejected record,
   preserving history.
8. Automated tests cover: upload validation rejections, the OCR-confirmation-is-editable requirement, and that
   submission alone never changes `is_discoverable`.

---

## Verified Current State (read directly from code and docs, not assumed)

- `docs/AI/04_DATABASE.md` already fully specifies `verification.verification_records` (`provider_id`,
  `verification_type`, `status`, `submitted_at`, `reviewed_at`, `reviewed_by`, `rejection_reason`) and
  `verification.verification_documents` (`verification_record_id`, `document_type`, `file_url`,
  `ocr_extracted_data`) column-by-column, plus the `verification_status`, `verification_type`, and
  `document_type` enums (Enum Types table) — nothing to design at the column level. The Relationships Summary
  already models `providers ── verification_records (1:N) → verification_documents (1:N)` — the multiplicity
  this Plan's endpoint shapes must respect (Decision 4).
- **`docs/AI/13_OPEN_DECISIONS.md` still does not exist anywhere in the repository**, confirmed by a fresh
  directory listing — the same cross-story gap PRO-001/PRO-002 both flagged. This directly affects AC2: the
  "Business Verification Bar" is item 5 of that (missing) file, so this Plan must make the Business-side bar a
  **config-driven** decision (Decision 3) rather than a hardcoded product answer, per `04_DATABASE.md` Section
  14's own stated intent ("`verification_type` enum already includes both `business_license` and
  `business_lightweight`; which one is required is an application-config decision, not a schema decision").
- **`backend/app/modules/provider/models.py`'s `_pg_enum` helper already carries a forward-looking comment**
  (written during PRO-002): *"Flagged in the migration for the future Verification-domain story
  (`verification_records.status`) to reuse `verification_status` via `create_type=False, schema='provider'`
  rather than duplicating it."* This is a direct, load-bearing instruction from the prior story — honored as
  Decision 1 below, not re-derived from scratch.
- **No `verification` module exists anywhere** — confirmed by a full `backend/app/modules/**/*.py` glob
  (`audit`, `customer`, `identity`, `provider` only) and `mobile/lib/features/**/*.dart` glob (`auth`, `customer`,
  `home`, `provider` only). This is a genuinely new domain module on both sides (Decision 5/9).
- **No OCR pipeline, external OCR client, or Ejari integration exists anywhere in this codebase.** Confirmed by
  a repo-wide grep for `ocr|OCR|ejari|Ejari|emirates.id|EmiratesId`: every hit outside `docs/AI/` narrative
  documents is either this story's own future-facing doc references or
  `.agents/skills/identity-verification/SKILL.md` (a *behavioral* skill file instructing agents on trust-gate
  discipline, not an integration). There is no `boto3`-style OCR SDK client, no external API wrapper, and
  nothing under `backend/` referencing any real OCR vendor. `00_PROJECT_CONTEXT.md`'s own changelog documents
  that this codebase is a pivot from an earlier "MyCommunity" product (ADR-011) — the "existing Ejari/Emirates ID
  OCR pipeline" language in `03_DOMAIN_MODEL.md`/the story description is best read as describing a
  **product-level asset assumption carried over from planning, not literal code present in this repository**.
  This is stated plainly as Decision 6 below, exactly as the story's own text anticipates ("OCR integration
  itself is stubbed pending confirmation of the existing pipeline's interface").
- **`backend/app/shared/storage/`'s `FileStorage` protocol (ADR-017) is generic and reusable as-is** for the
  save/delete mechanics (`interfaces.py`), but `LocalFileStorage.save()` (`local_file_storage.py`) **hardcodes**
  its returned reference as `f"/media/{subdirectory}/{filename}"` — i.e. it assumes every file it stores is
  meant to be served publicly via the `/media` `StaticFiles` mount (`app/main.py`). That assumption is correct
  for portfolio photos (PRO-002) and **wrong** for verification documents (Decision 7 explains why a public URL
  is not acceptable here). `FileStorage` also has no `read()` method today — `PortfolioService` never needed to
  read a file's bytes back into the application, only serve it statically. Both gaps require a small, additive
  extension (Decision 7), not a fork of the abstraction.
- **`backend/app/shared/storage/image_validation.py`** is portfolio-specific by construction: it hardcodes
  `InvalidPortfolioUploadError`, reads `settings.MAX_PORTFOLIO_PHOTO_SIZE_BYTES`, only recognizes JPEG/PNG/WEBP
  signatures, and deliberately raises one generic, non-revealing error regardless of which check failed. This
  story's documents can also be PDFs (a trade license is very plausibly a PDF, not a photo), and AC3 explicitly
  asks for a **specific, actionable** error — the direct opposite of `image_validation.py`'s deliberately vague
  error philosophy. Reusing it unmodified would both under-support the file types this story actually needs and
  violate AC3's literal wording. See Decision 8.
- `backend/app/core/authorization.py`'s `ensure_owner_or_not_found` and ADR-015's shape rule are directly
  reusable, unchanged.
- `backend/app/modules/provider/services/provider_service.py`'s `get_my_provider(user_id) -> Provider | None`
  is the exact lookup this story needs to resolve the caller's own Provider (id + `provider_type`) — reused via
  a new, one-directional `verification → provider` cross-module service dependency (Decision 9), the same
  constructor-injection, flush-only shape ADR-014/ADR-016 already established twice.
- No Pydantic schema anywhere in this codebase sets `model_config = ConfigDict(extra="forbid")` (confirmed by
  grep) — the project relies on simply never declaring a field, not on rejecting unknown ones, to keep a
  request surface from accepting attacker-supplied values. This is directly relevant to AC6's "cannot
  self-approve": the submission schema this story adds must have **no `status` field of any kind**, so there is
  no route through which a client could even attempt to set it (structural prevention, matching the same
  "no route shape exists" reasoning ADR-015 already uses for ownership).
- `backend/.gitignore` already ignores `/uploads/` (PRO-002) — this story adds a second, sibling upload root
  that must be ignored the same way (Decision 7).

---

## Architecture Decisions

### Decision 1 — `verification_records.status` reuses the existing `provider.verification_status` Postgres enum type; `verification_type`/`document_type` are new, colocated in the `verification` schema

`provider.models.py`'s `_pg_enum(VerificationStatus, "verification_status")` already created a native Postgres
enum type, scoped to the `provider` schema, with exactly the four values `04_DATABASE.md` specifies for
`verification_status` (`pending`, `under_review`, `approved`, `rejected`) — the same four AC1 asks for. Creating
a second, identically-valued enum type in the `verification` schema would be a duplicate type for no benefit and
would directly contradict PRO-002's own explicit hand-off comment. `verification.verification_records.status`
is mapped via `postgresql.ENUM(..., name="verification_status", schema="provider", create_type=False)` in the
new migration — referencing, never re-creating, the existing type. At the Python/ORM level,
`app.modules.verification.models` imports `VerificationStatus` directly from `app.modules.provider.models` — a
pure value-enum import, not a service or repository coupling, exactly mirroring ADR-014's already-accepted
precedent (`customer` reusing `identity.models.LanguageCode`). This is not a new cross-module *service* edge (see
Decision 9 for that); it is the same lightweight, already-approved pattern for sharing a pure enum.

`verification_type` (`freelancer_id`, `business_license`, `business_lightweight`) and `document_type`
(`emirates_id`, `trade_license`, `other`) are genuinely new enums with no existing type anywhere — created fresh,
colocated in the `verification` schema (mirrors `provider`'s own `_pg_enum` colocation convention).

### Decision 2 — This story never reads or writes `providers.verification_status`/`is_discoverable`; a provider's own status view reads `verification_records` directly, not the cache

`04_DATABASE.md` is explicit that `providers.verification_status` is "a denormalized cache... source of truth is
`verification_records`," updated "whenever the latest record here changes status" by "a trigger or
service-layer hook" — and Flow 6 (`14_USER_FLOWS.md`) assigns that hook to the **Admin Verification Review**
flow, i.e. VER-002, not this story. Combined with AC5's explicit "the provider's discoverability is unaffected
until VER-002 processes it," the cleanest, most scope-honest design is: **this story's code path never touches
the `providers` table at all.** No migration in this story alters `providers`; no service in this story imports
`ProviderRepository`'s write methods against `providers` (only `ProviderService.get_my_provider`, a pure read,
per Decision 9).

A direct, useful consequence: `GET /providers/me/verification` (AC6) reads the caller's **latest
`verification_records` row directly**, never `providers.verification_status`. This matters concretely once
VER-002 ships: after a rejection, `providers.verification_status` would read `rejected` (VER-002's cache write)
even after this story's resubmission flow creates a brand-new `pending` record — if the provider's own status
view read the stale cache instead of the true source, they would see "rejected" immediately after successfully
resubmitting. Reading `verification_records` directly avoids that stale-cache UX bug entirely, and costs
nothing extra to build (the row already has to be fetched for `GET` regardless).

**Alternative considered and rejected:** update `providers.verification_status` back to `pending` on
resubmission, to keep the cache "fresh." Rejected — this would mean this story's code writes to another domain's
table for a purpose that isn't really this story's job (recomputing the cache is explicitly VER-002's
responsibility, per the existing "trigger or service-layer hook" framing), and it isn't necessary once the
provider's own status view already reads the true source directly.

### Decision 3 — Business verification bar: config-driven, not hardcoded, per `04_DATABASE.md` Section 14's own stated design intent

`13_OPEN_DECISIONS.md` item 5 (Business Verification Bar) remains unresolved and the file itself still doesn't
exist. `04_DATABASE.md` Section 14 already anticipates exactly this: "which [`verification_type`] is required is
an application-config decision, not a schema decision." Two new settings absorb the eventual product answer
without a breaking migration or endpoint change:

- `BUSINESS_VERIFICATION_TYPE: VerificationType = VerificationType.BUSINESS_LIGHTWEIGHT` — which
  `verification_type` a Business submission is recorded under.
- `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED: bool = False` — whether a Business submission must include a
  document at all. Default `False` matches "lighter... gate" (`03_DOMAIN_MODEL.md`): a Business provider may
  call `POST /providers/me/verification` with no document reference and still get a `pending`
  `verification_records` row (zero `verification_documents` rows — the schema's 1:N relationship already
  permits N=0). If a future product decision flips this to `True` once item 5 resolves, Business submissions
  require a document through the exact same preview→submit flow already built for Freelancer (Decision 4) —
  zero code changes beyond the config flip.

Freelancer is **never** config-driven: `verification_type` is always `freelancer_id`, a document is always
required, and the accepted `document_type` is restricted to `emirates_id` (AC2's literal "Emirates-ID-equivalent
document" wording) — this is a hard business rule (`03_DOMAIN_MODEL.md`: "a safety issue... not just a quality
one"), not something a config flag should be able to weaken.

### Decision 4 — Endpoint shape: a two-call preview → submit flow, with `verification_records` genuinely 1:N (not a `/me` singleton)

AC4's own wording ("**After** upload, a confirmation screen shows OCR-extracted fields... **Submitting**
creates a `verification_records` row") describes three distinct steps — upload, confirm, submit — where the
`verification_records`/`verification_documents` rows must not exist until the final, deliberate "submit" action.
A single combined upload+submit call would force the record to exist *before* the user has had a chance to
review/edit the OCR output, contradicting AC4's sequencing and the "not already-verified fact" framing. This
Plan therefore uses two calls:

- **`POST /providers/me/verification/documents/preview`** (`multipart/form-data`: `file`, `document_type`) —
  validates the upload (Decision 8), runs the stub OCR (Decision 6) against the raw bytes, stores the validated
  file to a **private** location (Decision 7) at a fixed, per-provider "pending" slot (not a client-visible
  token — see below), and returns the OCR-stub's (empty) extracted fields. **Writes no database row at all** —
  purely a validate-and-stash-the-file step. Requires an existing Provider (404 `ProviderNotFoundError`
  otherwise, matching every other `/providers/me/*` sub-resource's established pattern).
- **`POST /providers/me/verification`** (JSON: `document_type` (optional for Business per Decision 3),
  `confirmed_fields: { full_name?, id_number?, expiry_date? }`) — the user's **final, edited** values, not
  necessarily identical to whatever the stub returned. Resolves `verification_type` from `provider_type`
  (Decision 3), checks the pending-slot file exists when a document is required (Decision 3/AC2), and — in one
  transaction — creates the new `verification_records` row (`status=pending`) and, if a document was involved,
  moves the pending file into its permanent private location and creates the matching `verification_documents`
  row (`ocr_extracted_data` = the **confirmed_fields the user actually submitted**, not the stub's raw output —
  this is the concrete mechanism AC8's "OCR-confirmation-is-editable" test targets). Rejects (409
  `VerificationSubmissionNotAllowedError`) if the caller's latest existing record is anything other than absent
  or `rejected` — i.e. a provider with a `pending`/`under_review`/`approved` record cannot submit a duplicate
  cycle; only "no record yet" or "latest is rejected" opens a new cycle. Because this always **creates** a new
  row and never **updates** an existing one, AC7 ("resubmission... creates a new verification cycle rather than
  mutating the rejected record, preserving history") is satisfied by construction, not by a special-cased branch.
- **`GET /providers/me/verification`** — returns the caller's single **latest** `verification_records` row (by
  `submitted_at` descending) plus its documents, or 404 if the caller has never submitted. This is a fixed path
  with no `{id}` — per ADR-015's singleton shape — even though the underlying table is genuinely 1:N; the
  caller-facing *surface* only ever needs "my current status" (AC6's literal ask), never a history browse (no AC
  requires one — see Explicitly Out of Scope). This is a small, deliberate extension of ADR-015's rule (a fixed
  `/me` path over the *latest* row of an N-cardinality table, not a true 1:1 resource) and is flagged for
  `architect`'s explicit attention rather than silently assumed compatible.
- **`GET /providers/me/verification/documents/{document_id}/file`** — streams one of the caller's own document's
  raw bytes (Decision 7). Genuinely `{id}`-addressable, so `ensure_owner_or_not_found` (via the document → its
  parent record → `provider_id` chain) is load-bearing here, per ADR-015.
- **No `PATCH`/`PUT` endpoint of any kind touches `status`, `reviewed_at`, `reviewed_by`, or `rejection_reason`**
  anywhere in this story — there is no route shape through which a caller (or anyone) could self-approve (AC6),
  structurally, not just by an authorization check that could be bypassed or forgotten.

**No client-supplied "storage reference" token exists in this API at all** (see Decision 7's pending-slot
design) — removing an entire class of "guess another user's upload token" attack surface by construction, not
by validation.

**Alternatives considered and rejected:**
- **Single combined upload+submit call** — rejected per AC4's explicit sequencing, above.
- **A client-supplied opaque `storage_reference` returned by the preview call and echoed back at submit** —
  rejected in favor of a fixed, server-derived, per-provider "pending" slot (Decision 7): simpler API surface,
  no token to validate/spoof, and it naturally self-bounds disk usage (each new preview overwrites the same
  slot, so an abandoned preview never accumulates beyond one file per provider).
- **A `GET /providers/me/verification/history`** — not built; no AC asks for it (see Explicitly Out of Scope).

### Decision 5 — Module placement: a new, top-level `backend/app/modules/verification/` module; routes nested under `/providers/me/verification`

`04_DATABASE.md` places `verification_records`/`verification_documents` in their own `verification` Postgres
schema — a peer to `provider`, not a child of it — and `03_DOMAIN_MODEL.md`/`02_ARCHITECTURE.md` both list
Verification as its own top-level Core Business Domain, exactly like Identity, Customer, and Provider each
already got their own `backend/app/modules/<domain>/` module. Cramming this story's models/services/repositories
into `backend/app/modules/provider/` would blur that boundary for no benefit — the two domains have genuinely
different lifecycles (a Provider row is created once; `verification_records` accumulates a full history over
time) and, once VER-002 ships, Verification gains its own admin-facing surface Provider has no reason to know
about.

**Code and URL are deliberately decoupled:** the new module owns its own `models.py`/`repositories/`/
`services/`/`schemas.py`/`api.py`/`dependencies.py`, but its router is mounted at
`/providers/me/verification` (`backend/app/api/v1/api.py` gains
`v1_router.include_router(verification_router, prefix="/providers/me/verification")`, alongside the existing
`provider_router` at `/providers`) — from the mobile client's perspective this reads naturally as "a sub-resource
of my provider," matching `15_SCREEN_INVENTORY.md`'s S-19/S-20 placement immediately after Provider onboarding,
while the backend keeps the two domains' code genuinely separate. This is the same kind of orthogonality
FastAPI already supports cleanly and does not require any change to `provider`'s own router.

**Alternative considered and rejected:** add verification code directly inside `backend/app/modules/provider/`
— rejected as a domain-boundary violation against `04_DATABASE.md`'s own schema separation and
`02_ARCHITECTURE.md`'s "no duplicate domain models... clear separation of concerns," for a savings of one new
module directory that provides no real benefit.

### Decision 6 — OCR pipeline: stated plainly as not existing in this codebase; a swappable `DocumentOcrService` protocol with a stub that always returns empty candidate fields

Per the Verified Current State's grep results, **no OCR pipeline, external OCR SDK, or Ejari integration exists
anywhere in this repository.** The story description's own instruction — "The OCR integration itself is stubbed
pending confirmation of the existing Ejari/Emirates ID pipeline's interface... this story does not build a new
OCR engine from scratch" — is read literally: this story does not attempt to guess at, mock a specific vendor
for, or partially reverse-engineer an "existing" pipeline that isn't present in this codebase. It builds the
correct **shape** for one to be plugged in later, exactly the swappable pattern ADR-017 already established for
file storage:

- `backend/app/modules/verification/services/document_ocr_service.py`: a `DocumentOcrResult` value object
  (`full_name: str | None`, `id_number: str | None`, `expiry_date: date | None`, `confidence: float`) and a
  `DocumentOcrService` `Protocol` (`async def extract(self, content: bytes, *, document_type: DocumentType) ->
  DocumentOcrResult`).
- The only implementation this story ships, `StubDocumentOcrService`, **always** returns
  `DocumentOcrResult(full_name=None, id_number=None, expiry_date=None, confidence=0.0)` regardless of the actual
  file content — it never attempts real extraction. This directly satisfies AC4's letter (a confirmation screen
  showing "OCR-extracted fields... as editable") while being honest about the fact that nothing was actually
  read yet: the fields are present and editable, just empty, and copy on the mobile confirmation screen should
  say so plainly (Decision — Mobile UX, below) rather than implying a real read happened.
- `VerificationService` (the preview-call handler) depends on the `DocumentOcrService` Protocol, never
  `StubDocumentOcrService` directly, wired via a new `get_document_ocr_service()` DI provider — so a future
  story, once the real pipeline's interface is actually confirmed (per the `identity-verification` skill's own
  Core Directive 2), can add a real implementation and change one dependency-wiring line, with zero changes to
  `VerificationService` itself. Flagged for a new ADR at story close (next available: **ADR-018**), mirroring how
  ADR-017 recorded the same pattern for `FileStorage`.

**Mobile UX consequence (for `frontend` to implement, not prescribed word-for-word here):** because the stub
never actually extracts anything, the confirmation screen's copy should read as "we couldn't automatically read
your document yet — please fill in these details yourself," not "here's what we read" — the same
never-assert-ungrounded-data spirit `00_PROJECT_CONTEXT.md` already applies to the AI conversation, applied here
to OCR. This still satisfies AC4 structurally (an editable confirm step framed as provisional, not fact); it is
simply honest about *why* the fields start empty.

### Decision 7 — Verification documents are private, never served through the public `/media` mount; `FileStorage` gains a minimal, backward-compatible extension to support this

**This is the single most consequential decision in this story and is called out for `architect`'s explicit,
first-priority review.** Portfolio photos (PRO-002) are meant to be public — they're the customer-facing
storefront. Emirates ID scans and trade licenses are exactly the opposite: `06_SECURITY.md` lists "Verification
records" under Sensitive Data explicitly, and this platform targets UAE PDPL/GDPR-ready compliance. Reusing
PRO-002's public-`/media`-mount pattern uncritically for identity documents would mean any predictable/guessed
`/media/verification/...` URL is publicly fetchable with no authentication at all — unacceptable for this data
class, and not something `06_SECURITY.md`'s generic File-Upload-Security section would catch by itself (it
covers MIME/extension/size validation, not access-control-at-rest, so this had to be reasoned through
independently rather than found as an existing written rule).

**Decision:** verification documents are stored under a **second, separate root directory**
(`VERIFICATION_UPLOAD_DIR` setting, e.g. `uploads_private/verification`) that is **never** mounted as
`StaticFiles` and **never** produces a `/media/...` URL. `LocalFileStorage` gains one new constructor parameter,
`public_url_prefix: str | None = "/media"` — defaulting to today's exact behavior for the existing portfolio
wiring (`get_file_storage()`, unchanged, zero behavior change for PRO-002). When constructed with
`public_url_prefix=None` (the new verification wiring), `save()` returns a bare storage-relative reference
(`f"{subdirectory}/{filename}"`) instead of a public URL — a reference that is only ever meaningful to the
backend itself, never handed to a client as a clickable link. `delete()`'s existing hardcoded
`removeprefix("/media/")` is generalized to use `self._public_url_prefix` (a small, behavior-preserving
refactor, `public_url_prefix or ""`). The `FileStorage` Protocol gains one new method, `async def read(self,
url_path: str) -> bytes`, implemented by `LocalFileStorage` (the only implementer; adding a method is additive
and does not affect `PortfolioService`, which never calls it). This is flagged for a second new ADR at story
close (next available after ADR-018: **ADR-019**) — a genuinely new consequence of the file-storage
infrastructure (private vs. public storage), not something ADR-017 anticipated in its original text.

Clients never receive a raw file path or public URL for a verification document. `GET
/providers/me/verification`'s response includes, per document, a `file_download_url` pointing at this story's
own authenticated endpoint (`/api/v1/providers/me/verification/documents/{document_id}/file`) — the mobile
client's existing Dio client already attaches the caller's bearer token to every request, so no new
authentication mechanism is needed, only an endpoint that checks ownership before streaming bytes
(`ensure_owner_or_not_found` via the document → record → `provider_id` chain, per Decision 4). This endpoint's
authorization check is written so a future VER-002 admin-review surface can extend it to "owner OR an Admin"
without restructuring the storage split.

**Pending-slot mechanic (avoids both a client-supplied token and unbounded disk growth):** the preview call
(Decision 4) writes to a **fixed, deterministic, per-provider path** — `pending/{provider_id}{extension}` under
`VERIFICATION_UPLOAD_DIR` — never a randomly-generated token. Each new preview call for the same provider
overwrites the previous one, so an abandoned preview (never followed by a submit) never accumulates beyond one
file per provider — no rate limiting or cleanup job is needed to bound this. On a successful `POST
/providers/me/verification`, the pending file's bytes are read (`FileStorage.read`), re-saved under the
permanent path `verification/{provider_id}/{verification_record_id}/{filename}` (a fresh, unique name — a
provider's later resubmission cycle gets its own permanent path, never overwriting a previous cycle's evidence,
preserving history per AC7), and the pending file is deleted — so the pending slot is empty again immediately
after every successful submission. An abandoned preview that is *never* submitted is the only case where a
file lingers, and even then it's capped at one file per provider — an accepted, explicitly-flagged tradeoff
identical in kind to PRO-002 Decision 5's "orphaned-file cleanup is a future administrative job," not a new
class of concern.

`backend/.gitignore` gains `/uploads_private/` alongside the existing `/uploads/` entry.

**Alternatives considered and rejected:**
- **Reuse the existing public `/media` mount, unchanged, for verification documents too** — rejected outright;
  this is the security-sensitive default this Decision exists specifically to avoid.
- **A signed/expiring URL scheme (e.g. a short-lived query-string token) instead of an authenticated streaming
  endpoint** — rejected as unnecessary complexity for this story: the mobile client already authenticates every
  request via its existing Dio bearer-token interceptor, so a normal authenticated `GET` is simpler and equally
  secure, with no new expiry/signing infrastructure to build or reason about.
- **Storing documents as `bytea` directly in Postgres** — rejected for the same reason PRO-002 rejected it for
  portfolios: `verification_documents.file_url`'s own spec says "stored file reference, not the file itself."
- **A client-supplied opaque preview token, stored server-side in Redis with a TTL** — rejected in favor of the
  simpler, stateless, deterministic pending-slot path; introducing Redis-backed ephemeral state for a single
  call site would be the kind of premature infrastructure ADR-014/ADR-016 already declined to build for smaller
  problems than this one.

### Decision 8 — A new, parallel `document_validation.py` (not a reuse or in-place edit of `image_validation.py`), sharing only the underlying magic-byte signature checks

`image_validation.py` is portfolio-specific in every dimension that matters here: its exception type, its size
setting, its allowed type set (images only, no PDF), and its deliberately-uniform, non-revealing error message.
Verification documents need PDF support (a trade license is plausibly a PDF) and, per AC3's explicit wording, a
**specific, actionable** error — the opposite philosophy from `image_validation.py`'s intentionally vague one
(that vagueness was a deliberate anti-probing choice for a *different* AC that never asked for specificity;
AC3 here explicitly does, so the specific AC wins over a borrowed precedent rather than defaulting to it).

**Chosen:** extract the three existing magic-byte checkers (`_is_jpeg`, `_is_png`, `_is_webp`) out of
`image_validation.py` into a new, non-domain-specific `backend/app/shared/storage/file_signatures.py`, adding one
new checker, `_is_pdf` (`content.startswith(b"%PDF-")`). `image_validation.py` is updated to import from this new
module instead of defining its own copies — a small, behavior-preserving refactor with no test changes expected
(same inputs produce the same outputs). A new `backend/app/shared/storage/document_validation.py` defines
`validate_verification_document_upload(upload_file, *, document_type) -> tuple[bytes, str]`, allowing
`.jpg`/`.jpeg`/`.png`/`.webp`/`.pdf`, checked against a new `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES` setting
(default 10 MB — documents/scans are plausibly larger than a portfolio photo), and raising **distinct**
exceptions per failure category so the error is genuinely actionable:
- `VerificationDocumentTooLargeError` (422) — "This file is too large. The maximum size is 10 MB."
- `VerificationDocumentInvalidTypeError` (422) — "Unsupported file type. Please upload a JPG, PNG, or PDF."

Filenames remain always server-generated (never the client's original filename), matching `06_SECURITY.md`.

**Alternatives considered and rejected:**
- **Reuse `image_validation.py` unmodified** — rejected: no PDF support, wrong exception type, and its
  deliberately-vague error directly conflicts with AC3's literal "specific, actionable error" requirement.
- **Generalize `image_validation.py` in place to accept a caller-supplied exception type/allowed-set/size
  parameter, used by both portfolios and documents** — rejected: this would couple two independently-evolving
  validation policies (portfolio photos deliberately stay vague per their own AC; documents deliberately must be
  specific per theirs) behind one shared function signature, the kind of premature, over-general abstraction
  `08_CODING_STANDARDS.md` warns against. Sharing only the true common primitive (byte-signature sniffing) is
  the right level of reuse.

### Decision 9 — Cross-module dependency: `verification → provider`, read-only, via direct service injection

`VerificationService` needs to resolve the caller's own Provider (its id and `provider_type`) to determine
`verification_type`/document requirements (Decision 3) and to scope every record it creates. It depends on
`provider`'s existing `ProviderService.get_my_provider(user_id)` — a pure read, no write path into any
`provider`-schema table anywhere in this story (Decision 2). This is wired via constructor injection,
`verification/dependencies.py` importing `get_provider_service` from `provider/dependencies.py` — the identical
shape ADR-014 (`identity → customer`, `identity → audit`) and ADR-016 (`provider → identity`) already
established twice; `provider`'s code gains zero new imports from `verification` (one-directional, no cycle
risk). Flagged for a new ADR at story close (next available: **ADR-018**, or **ADR-019** if Decision 6's OCR
protocol is recorded first — the tech-lead will finalize exact numbering at story close, following the same
"flag now, number at close" practice PRO-002 used for ADR-017).

**Alternative considered and rejected:** re-fetch the Provider directly via `ProviderRepository` inside
`verification` — rejected outright as the "Module → Another Module's Repository" pattern `02_ARCHITECTURE.md`
explicitly prohibits.

---

## Backend — Proposed Changes

### Migration
1. New Alembic migration, `verification_domain` (down-revision = PRO-002's head `272b12ab9b2f` — confirm via
   `alembic heads` at implementation time). Creates the `verification` Postgres schema and:
   - New enums `verification_type` (`freelancer_id`, `business_license`, `business_lightweight`) and
     `document_type` (`emirates_id`, `trade_license`, `other`), colocated in `verification` schema.
   - `verification.verification_records` — exactly per `04_DATABASE.md`'s spec; `status` mapped via
     `postgresql.ENUM(..., name="verification_status", schema="provider", create_type=False)` (Decision 1 — does
     **not** create a new type). Indexes: `idx_verification_records_provider_id`,
     `idx_verification_records_status`.
   - `verification.verification_documents` — exactly per spec. Index: `idx_verification_documents_record_id`.
   - No change of any kind to any `provider`-schema table (Decision 2).
2. Verify upgrade/downgrade against a disposable scratch database (ADR-013's precedent for real-DB migration
   verification, separate from the test suite's own `Base.metadata` approach).

### Models (`backend/app/modules/verification/models.py`, new module)
3. `VerificationType(StrEnum)`, `DocumentType(StrEnum)` + `_pg_enum` helper (mirrors `provider/models.py`'s
   pattern). `VerificationRecord(CommonColumnsMixin, Base)` — imports `VerificationStatus` from
   `app.modules.provider.models` (Decision 1) rather than redefining it. `VerificationDocument(CommonColumnsMixin,
   Base)`.

### Repositories (`backend/app/modules/verification/repositories/`, new)
4. `verification_record_repository.py`: `VerificationRecordRepository(BaseRepository[VerificationRecord])` —
   `get_latest_for_provider(provider_id)` (order by `submitted_at` desc, limit 1).
5. `verification_document_repository.py`: `VerificationDocumentRepository(BaseRepository[VerificationDocument])`
   — `list_for_record(record_id)`, `get_by_id(document_id)`.

### Services (`backend/app/modules/verification/services/`, new)
6. `document_ocr_service.py` — `DocumentOcrResult`, `DocumentOcrService` Protocol, `StubDocumentOcrService`
   (Decision 6).
7. `verification_service.py` — `VerificationService(provider_service, verification_record_repository,
   verification_document_repository, verification_file_storage, document_ocr_service)`:
   - `preview_document(user_id, *, upload: UploadFile, document_type: DocumentType) -> DocumentOcrResult` —
     resolves the caller's provider (404 if none), validates the upload (Decision 8), runs the OCR stub, saves
     to the deterministic pending slot (Decision 7), returns the (empty) extracted fields. No DB write.
   - `submit(user_id, *, document_type: DocumentType | None, confirmed_fields: dict) -> VerificationRecord` —
     resolves the caller's provider, derives `verification_type`/document-required from `provider_type` +
     settings (Decision 3), checks resubmission eligibility against the latest existing record (Decision 4/AC7),
     validates a pending-slot file exists when required (`VerificationDocumentRequiredError` otherwise), and
     atomically creates the `verification_records` row plus (if applicable) the `verification_documents` row —
     moving the pending file to its permanent location (Decision 7) in the same flush sequence.
   - `get_my_current_status(user_id) -> VerificationRecord | None` — the caller's latest record, or `None`
     (→ 404 at the API layer). Reads `verification_records` directly (Decision 2), never
     `providers.verification_status`.
   - `get_document_bytes(user_id, document_id) -> tuple[bytes, DocumentType]` — resolves the caller's provider,
     the document, its parent record, `ensure_owner_or_not_found` against `provider_id`, reads bytes via
     `verification_file_storage.read`.

### Storage (`backend/app/shared/storage/`, extended — not a new module)
8. `interfaces.py` — `FileStorage` Protocol gains `async def read(self, url_path: str) -> bytes`.
9. `local_file_storage.py` — `LocalFileStorage.__init__` gains `public_url_prefix: str | None = "/media"`;
   `save()`/`delete()`/new `read()` all honor it (Decision 7). Zero behavior change to the existing
   `get_file_storage()` (portfolio) wiring.
10. `file_signatures.py` (new) — `_is_jpeg`/`_is_png`/`_is_webp`/`_is_pdf`, extracted from `image_validation.py`
    (Decision 8).
11. `image_validation.py` — updated to import from `file_signatures.py` (behavior-preserving refactor).
12. `document_validation.py` (new) — `validate_verification_document_upload` (Decision 8).

### Config (`backend/app/core/config.py`)
13. New settings: `VERIFICATION_UPLOAD_DIR: str = "uploads_private/verification"`,
    `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES: int = 10_485_760`,
    `BUSINESS_VERIFICATION_TYPE: str = "business_lightweight"`,
    `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED: bool = False` (Decision 3). `backend/.gitignore`: add
    `/uploads_private/`.

### Exceptions (`backend/app/core/exceptions/exceptions.py`)
14. `VerificationRecordNotFoundError` (404), `VerificationDocumentNotFoundError` (404,
    ownership-collapsing per ADR-015), `VerificationSubmissionNotAllowedError` (409 — an active/approved cycle
    already exists), `VerificationDocumentRequiredError` (422, actionable — "Please upload and confirm your
    document before submitting."), `VerificationDocumentTooLargeError` (422),
    `VerificationDocumentInvalidTypeError` (422), `InvalidVerificationFieldsError` (422 — malformed
    `expiry_date`/oversized text fields).

### Schemas (`backend/app/modules/verification/schemas.py`)
15. `VerificationPreviewResponse { document_type, full_name: str | None, id_number: str | None, expiry_date:
    date | None, confidence: float }`. `ConfirmedFieldsInput { full_name?: str, id_number?: str, expiry_date?:
    date }` — deliberately optional at every field (Decision 6 — even a real future OCR won't always extract
    every field, and no AC mandates these as required). `SubmitVerificationRequest { document_type:
    DocumentType | None, confirmed_fields: ConfirmedFieldsInput | None }` — **no `status`, `reviewed_at`,
    `reviewed_by`, or `rejection_reason` field anywhere in this schema** (AC6, structural self-approval
    prevention). `VerificationDocumentResponse { id, document_type, ocr_extracted_data, file_download_url }`.
    `VerificationRecordResponse { id, verification_type, status, submitted_at, reviewed_at, rejection_reason,
    documents: list[VerificationDocumentResponse] }`.

### API (`backend/app/modules/verification/api.py`)
16. `POST /documents/preview` (multipart), `POST /` (submit), `GET /` (current status), `GET
    /documents/{document_id}/file` (streamed bytes, `Content-Type` set from the stored extension, no
    `Content-Disposition` implying a public/shareable link). All bare-authenticated (mirrors PRO-002 Decision
    7's reasoning — every call already resolves and scopes strictly to the caller's own Provider/records, and a
    caller who just finished PRO-001's onboarding wizard should not risk a spurious 403 before their token
    naturally refreshes).

### App wiring
17. `backend/app/api/v1/api.py`: `v1_router.include_router(verification_router, prefix="/providers/me/verification")`.
18. `backend/tests/conftest.py`: import `app.modules.verification.models` so its tables join
    `Base.metadata` for the test suite's create/drop lifecycle (ADR-013's established pattern).

### Dependencies (`backend/app/modules/verification/dependencies.py`)
19. `get_verification_record_repository`, `get_verification_document_repository`,
    `get_verification_file_storage` (returns `LocalFileStorage(base_directory=settings.VERIFICATION_UPLOAD_DIR,
    public_url_prefix=None)`), `get_document_ocr_service` (returns `StubDocumentOcrService()`),
    `get_verification_service` (imports `get_provider_service` from `app.modules.provider.dependencies` per
    Decision 9).

### Tests
20. `backend/tests/modules/verification/test_verification_service.py`: preview validates and rejects
    oversized/wrong-type/mismatched-signature uploads with the *specific* exception each case should raise (AC3);
    submitting Freelancer without a prior preview is rejected (`VerificationDocumentRequiredError`); submitting
    Freelancer with a non-`emirates_id` `document_type` is rejected; submitting Business with no document
    succeeds when `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED=False` (default); **OCR-confirmation-is-editable**
    (AC8) — preview returns all-`None` fields, submit is called with different, user-supplied
    `confirmed_fields`, and the persisted `verification_documents.ocr_extracted_data` matches the *submitted*
    values, not the stub's raw output; **is_discoverable never touched** (AC8) — submit is called, then the
    provider's own `is_discoverable`/`verification_status` columns are asserted unchanged, and a grep-level
    review confirms no code path in this module ever imports `ProviderRepository`'s write methods; **resubmission
    after rejection** (AC7) — a record's `status` is set to `rejected` directly (simulating VER-002, which
    doesn't exist yet), a second `submit` call succeeds, and both rows exist afterward, the first row's fields
    unchanged; a second `submit` call while the latest record is still `pending` is rejected (409).
21. `backend/tests/modules/verification/test_verification_endpoints.py`: full HTTP round trip for all four
    routes, including a real small in-memory multipart preview upload and a real PDF-signature fixture (trade
    license path); unauthenticated → 401 on every route; **ownership** — a second provider cannot `GET` the
    first provider's current status or download the first provider's document (404, not 200 or 403).
22. `backend/tests/shared/storage/test_document_validation.py`: valid JPEG/PNG/WEBP/PDF bytes pass; a text file
    renamed to `.pdf` is rejected with the type-specific error; an oversized payload is rejected with the
    size-specific error; a disallowed extension is rejected.
23. `backend/tests/shared/storage/test_local_file_storage.py` (extended or new): `public_url_prefix=None`
    produces a bare relative reference, never a `/media/...` string; `read()` round-trips what `save()` wrote;
    existing portfolio-shaped (`public_url_prefix="/media"`) behavior is unchanged (regression guard for
    PRO-002).

---

## Mobile — Proposed Changes

### New feature module: `mobile/lib/features/verification/`
24. A new, sibling feature module (mirroring the backend's own module separation, Decision 5) — not an
    extension of `features/provider/`. Verification has its own distinct screens (S-19/S-20), its own
    repository/models, and (once VER-002 ships) will eventually gain admin-adjacent surfaces Provider has no
    reason to know about. The only coupling to `features/provider/` is a GoRouter navigation call at the end of
    the onboarding wizard — the same "screen-to-screen navigation only" shape PRO-002's Profile & Settings →
    Storefront link already uses, not a shared-widget or shared-state coupling (`02_ARCHITECTURE.md`: "Features
    must not depend directly on each other").
25. `domain/models/verification_record.dart`, `verification_document.dart`, `document_type.dart`,
    `ocr_preview_result.dart`, `submit_verification_request.dart`, `verification_exception.dart` — mirror the
    backend's new response/request shapes.
26. `data/verification_repository.dart` — `previewDocument(File file, DocumentType documentType)` (multipart,
    mirrors `uploadPortfolioPhoto`'s pattern), `submit(SubmitVerificationRequest)`, `getMyCurrentStatus()`
    (returns `null` on 404 — "not yet submitted" is a normal state, mirroring `getMyProvider`'s established
    null-on-404 convention), `getDocumentBytes(String documentId)` (for an in-app "view what I submitted"
    affordance on S-20, streamed through the authenticated Dio client — never a raw URL `Image.network` call,
    per Decision 7).
27. `presentation/screens/verification_upload_screen.dart` (new, **S-19**) — document-type-specific uploader
    (camera/file picker), calls `previewDocument`, then navigates to:
28. `presentation/screens/verification_confirm_screen.dart` (new — the "OCR confirm" step AC4 describes) —
    editable text fields pre-filled from the preview response (empty, per Decision 6's stub), copy framed per
    Decision 6's mobile-UX note ("we couldn't read this automatically yet — please fill it in" rather than
    implying a real read happened), a locally-rendered thumbnail of the picked file (from the device's own
    picked-file reference — never a fetched server URL, since the pending file is private, Decision 7), and a
    "Submit" primary action calling `submit()`.
29. `presentation/screens/verification_status_screen.dart` (new, **S-20**) — status badge (Pending / Under
    Review / Approved / Rejected, per `16_UX_GUIDELINES.md`'s internal→user-facing copy mapping table:
    "Pending/Under Review" → "We're reviewing your documents," "Rejected" → "We couldn't verify this" + the
    plain-language `rejection_reason` + a "Resubmit" action that routes back to S-19), an empty/first-time state
    ("You haven't submitted verification yet" + a primary "Start Verification" action) when `getMyCurrentStatus`
    returns `null`.
30. Route/entry points: (a) the existing Provider onboarding wizard (`features/provider/`, PRO-001) now
    navigates to the new `verification-upload` route immediately after a successful `POST /providers/me`,
    instead of ending at a stub; (b) the existing Storefront screen (S-25, PRO-002) gains a small verification
    status chip/banner near the top, linking to `verification-status` — the most reasonable available entry
    point given the Provider Dashboard (S-23) has not been built by any prior story.
31. `state/verification_upload_controller.dart`, `verification_status_controller.dart` — Riverpod controllers
    per the existing `features/*/state/` convention.

### Tests
32. `mobile/test/features/verification/verification_upload_screen_test.dart`,
    `verification_confirm_screen_test.dart`, `verification_status_screen_test.dart`,
    `verification_repository_test.dart` (or a fake-repository-backed widget test suite, per the existing
    `fake_provider_repository.dart` convention) — confirm-screen fields are genuinely editable and the submitted
    payload reflects edits, not the stub's raw (empty) response (AC4/AC8 at the UI level); status screen renders
    each of the four statuses' correct copy/badge; a second account's verification data is never
    fetched/displayed (mirrors the backend ownership guarantee at the UI level).
33. `mobile/test/features/verification/fakes/fake_verification_repository.dart` (new, following
    `fake_provider_repository.dart`'s established shape).

---

## Explicitly Out of Scope (do not implement in this story)

- Any admin-facing endpoint, `admin_action_log` write, or the actual approve/reject transition — all VER-002.
- Any notification send on status change (`03_DOMAIN_MODEL.md`'s Notification domain, Flow 8) — VER-002's
  trigger, not this story's.
- Any write to `providers.verification_status`/`is_discoverable` — VER-002's cache-update responsibility
  (Decision 2). This story's submission never changes discoverability (AC5), by never touching the column at
  all.
- `GET /providers/me/verification/history` or any multi-record browsing surface — no AC requires viewing
  anything but the current/latest cycle (AC6).
- A real OCR integration of any kind — `StubDocumentOcrService` (Decision 6) is explicitly interim; a future
  story swaps it in once the real pipeline's interface is actually confirmed to exist.
- Virus/malware scanning of uploaded documents (`06_SECURITY.md` already flags this as a future enhancement,
  same as PRO-002's precedent).
- Rate limiting or a cleanup job for abandoned pending-slot files — bounded to one file per provider by
  construction (Decision 7); not a growth risk that needs active mitigation at this scale.
- The Provider Dashboard (S-23) — not built by any prior story; this story links the verification status entry
  point from the existing Storefront screen instead (Decision, Mobile item 30).
- Claim-Your-Listing's own verification gate (`14_USER_FLOWS.md` Flow 3) — reuses this same
  `verification_records`/`verification_documents` mechanism conceptually, per the domain model, but wiring the
  Claim flow itself is a separate, not-yet-built story.
- Resolving `13_OPEN_DECISIONS.md` item 5 (the actual Business verification bar product decision) — this story
  only makes the *schema and config* absorb whichever answer is eventually chosen (Decision 3), per
  `04_DATABASE.md` Section 14's own stated intent; it does not make that product decision itself.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet — this is a fresh start (Sprint 4's Checkpoint, if any existed, was
deleted at PRO-002's close per the Continuity & Checkpointing process).

1. **backend** — Migration, `verification` module (models/repositories/services/schemas/api/dependencies), the
   `FileStorage`/`image_validation.py` extensions (Decisions 7/8), config, exceptions, `main.py`/`api.py` wiring,
   tests (items 1–23 above). ACs to satisfy: 1, 2, 3, 5, 6 (backend half), 7, 8 (backend half). **Read Decision 7
   in full before starting** — the private-storage split is the part most likely to be gotten subtly wrong
   (e.g. accidentally routing a verification document through the existing public `get_file_storage()`
   dependency instead of the new private one).
2. **frontend** — New `features/verification/` module, S-19/S-20 screens plus the confirm-screen step, wizard/
   Storefront navigation wiring, tests (items 24–33 above), once backend endpoints exist (or in parallel against
   a fake repository). ACs to satisfy: 2 (mobile half — the picker/confirm UI), 3 (mobile half — surfacing the
   specific, actionable error copy per rejection type), 4, 6 (mobile half — status display).
3. **tester** — Verify all 8 ACs individually. Particular attention to: AC3 (confirm each rejection category
   — size, extension, magic-byte mismatch — produces a genuinely *different*, actionable message, not one
   generic string); AC4/AC8 (the OCR-confirmation-is-editable test must prove the *submitted*, user-edited
   values are what get persisted, not merely that the endpoint accepts a payload); AC5/AC8 (read the actual
   service code to confirm no code path writes to `providers` at all, not merely that a test happens not to
   check it); AC6 (confirm no route in `api.py` accepts a `status`/`reviewed_*`/`rejection_reason` field at any
   layer, and that the ownership check on document download is genuinely exercised — read the service code, not
   just trust the DB); AC7 (two full rows exist after a rejection→resubmission sequence, first row's fields
   genuinely untouched); the private-storage split (Decision 7) — attempt to fetch a verification document via
   the public `/media` mount path shape and confirm it 404s, since it was never written there at all.
4. **architect** — Review Decision 7 (private storage split, `FileStorage` extension) first and most carefully
   against `06_SECURITY.md`'s Sensitive Data/File Upload Security sections and `02_ARCHITECTURE.md`'s
   "Infrastructure depends on Domain" rule; Decision 1 (enum reuse via `create_type=False`) for genuine
   correctness against the existing `provider.verification_status` type; Decision 4's endpoint shapes against
   ADR-015 (including the flagged "fixed path over the *latest* of an N-cardinality table" nuance); Decision 9
   (the new `verification → provider` cross-module edge) against ADR-014/ADR-016's established pattern; Decision
   3 (config-driven Business bar) against `04_DATABASE.md` Section 14's stated intent.
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decisions 6
   and 9 (or however the tech-lead finally sequences them) as **ADR-018**/**ADR-019** in `09_DECISIONS.md`;
   update `04_DATABASE.md` (new `verification` schema tables, confirming they match spec, and the
   `create_type=False` enum-reuse deviation from a naive "colocate everything" reading); update
   `12_TECH_STACK.md` if any new setting/dependency was actually introduced (none expected — no new Python/Dart
   package this story); flag `13_OPEN_DECISIONS.md`'s continued non-existence again, as PRO-001/PRO-002 both
   already did, for a separate follow-up outside this story's ownership.

---

## Verification Plan (mapped to the 8 ACs)

| AC | Verified by |
|---|---|
| 1 | Migration runs clean upgrade/downgrade; `\d verification.verification_records` / `\d verification.verification_documents` match spec; `verification_records.status`'s type is confirmed to be the *same* Postgres enum OID as `providers.verification_status` (not a duplicate type), per Decision 1. |
| 2 | Service/integration tests: a Freelancer submission without a document is rejected; a Freelancer submission with `document_type != emirates_id` is rejected; a Business submission with no document succeeds under the default config; flipping `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED=True` in a test makes an undocumented Business submission fail the same way Freelancer's does. |
| 3 | Upload tests: oversized, wrong-extension, and magic-byte-mismatched files are each rejected with their own specific exception/message (not one generic string); a valid JPEG/PNG/WEBP/PDF succeeds. |
| 4 | Widget/integration test: the confirm screen's fields are genuinely editable text inputs pre-filled from the (empty) preview response; changing a field and submitting sends the changed value, not the original. |
| 5 | Integration test: submit succeeds and creates a `pending` `verification_records` row; the provider's `is_discoverable`/`verification_status` columns are read before and after and asserted identical. |
| 6 | Integration test: `GET /providers/me/verification` returns the caller's own current record; no endpoint in `api.py` accepts a `status`/`reviewed_*` field at any layer (schema-level review + a test that a stray `status` field in the request body is silently ignored, never applied). |
| 7 | Integration test: a record is marked `rejected` (simulating VER-002), a resubmission is called, both rows exist afterward with the first row's fields unchanged and the second row's `status=pending`. |
| 8 | Three distinct, independently-runnable test cases confirmed: upload validation rejections (AC3, each category separately), OCR-confirmation-is-editable (submitted values persisted, not the stub's raw output), and `is_discoverable`/`verification_status` never changing across a submission. |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md`
- `docs/AI/03_DOMAIN_MODEL.md`
- `docs/AI/04_DATABASE.md` (Verification Domain section; Section 14's Business Verification Bar accommodation)
- `docs/AI/05_API_GUIDELINES.md`
- `docs/AI/06_SECURITY.md` (Sensitive Data; File Upload Security)
- `docs/AI/07_UI_GUIDELINES.md`
- `docs/AI/08_CODING_STANDARDS.md`
- `docs/AI/09_DECISIONS.md` (ADR-014, ADR-015, ADR-016, ADR-017 — all directly extended by this story)
- `docs/AI/14_USER_FLOWS.md` (Flow 2 steps 6–8; Flow 6, explicitly out of scope here)
- `docs/AI/15_SCREEN_INVENTORY.md` (S-19, S-20)
- `docs/AI/16_UX_GUIDELINES.md` (Trust & Verification UX Patterns; internal→user-facing copy mapping table)
- `.agents/skills/identity-verification/SKILL.md`
- `docs/implementation/plans/Plan_S04_PRO-001.md` / `Plan_S04_PRO-002.md` (module/endpoint-shape/file-upload
  precedents this story extends)
- `docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md` / `Walkthrough_S04_PRO-002.md`
