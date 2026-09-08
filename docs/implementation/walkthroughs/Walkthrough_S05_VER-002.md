# Walkthrough S05 VER-002

## Story: Review Provider Verification As An Administrator

**Sprint:** 05 | **Story ID:** VER-002 | **Priority:** High | **Status:** Done

As an administrator, I want to review a provider's submitted documents and approve or reject with a reason, so
that only genuinely verified providers become discoverable — a safety requirement, not just a quality one, since
Freelancers enter customers' homes.

This is the second and final story of Sprint 5 ("Provider Verification"), completing the Verification domain's
trust-gate enforcement that VER-001 deliberately left unbuilt: an admin-only review queue, atomic
approve/reject actions that update the provider's cached discoverability flag in the same transaction as the
status change, an `admin_action_log` write, and a provider-facing notification either way. **Scope boundary,
stated plainly:** this story is backend-only, by deliberate design, not omission — the admin operations
dashboard is explicitly excluded from the mobile app's 28-screen MVP inventory (`docs/AI/15_SCREEN_INVENTORY.md`'s
own "Explicitly Out of Scope" section), so no Flutter code was touched. Full context, architecture decisions, and
file-by-file scope: `docs/implementation/plans/Plan_S05_VER-002.md`.

This story's review process was, once again, more eventful than a routine pass: the tester's independent QA
found and empirically reproduced a genuine concurrency bug in the original approve/reject implementation — a
real bug, not a false positive — which was fixed with an atomic conditional `UPDATE` and a regression test
verified to fail without the fix and pass with it. The architect's review then independently re-verified that
fix (including reverting and re-applying it) and returned **APPROVED WITH RECOMMENDATIONS**. See the dedicated
Review Process section below for the full, honest account.

---

## What was implemented

### Backend (`backend/app/modules/verification/`, extended; two new domain modules: `administration`, `notification`)

- **Three new, reversible Alembic migrations**: `administration_domain` (creates the `administration` Postgres
  schema and `administration.admin_action_log`), `notification_domain` (creates the `notification` schema and
  `notification.notifications` only), and `provider_discoverability_invariant` (a narrow, column-change-free
  migration adding a new `CHECK` constraint to the existing `provider.providers` table).
- **`administration` module (new, first slice of the Administration domain)** — `AdminActionLog`
  (`CommonColumnsMixin`, versioned/soft-deletable, deliberately **not** built exempt like the immutable
  `audit.audit_logs`, since `04_DATABASE.md`'s Soft Delete exemption list names only `audit_logs`/
  `search_event_log`), `AdminActionLogRepository` (no custom methods), and `AdminActionLogService` exposing one
  explicit method, `record_verification_review`, mirroring `AuditService`'s "explicit methods, not one generic
  `record()`" convention. No `api.py`/`schemas.py` — nothing here is directly HTTP-exposed; `verification`'s new
  admin service calls it internally.
- **`notification` module (new, first slice of the Notification domain)** — `Notification`
  (`CommonColumnsMixin`, same reasoning), `NotificationRepository`, and `NotificationService` exposing one
  explicit method, `notify_verification_status_change`, with **hardcoded, plain-language copy** — "Verification
  approved" / "Great news — your verification has been approved. Your listing is now visible to customers." on
  approval, "Verification update" / a rejection-reason-interpolated body on rejection — never the raw
  `VerificationStatus` enum value (AC5's literal "never exposing internal status enum values"). Deliberately
  ships **only** `notifications` — no `notification_delivery` (no real channel exists to have a delivery status
  for) and no `notification_preferences` (nothing to opt in/out of yet); Sprint 12 ("Engagement & Trust") remains
  this domain's own dedicated future milestone.
- **`AdminVerificationService` (new, `verification/services/admin_verification_service.py`)** — a deliberately
  **separate** class from the existing, provider-facing `VerificationService`: different authorization model
  (`require_role(ROLE_ADMIN)` only, no ownership check of any kind), different callers, different side effects
  (writes into `provider`, `administration`, `notification`, none of which `VerificationService` ever touches).
  `approve`/`reject` each do all of their work — the `verification_records` status transition, the `providers`
  cache update, the `admin_action_log` write, and the `notifications` write — on the same request-scoped
  `AsyncSession`, flush only; the endpoint's single `await db.commit()` remains the only transaction boundary.
  `list_pending_for_review` batch-fetches Provider context for a whole page in exactly one `list_by_ids` query
  (never one query per record).
- **New, ownerless `require_role(ROLE_ADMIN)`-only authorization shape (`verification/admin_api.py`, new
  router, mounted at `/admin/verification`)** — a genuinely third endpoint shape alongside ADR-015's existing
  two (`/me` singleton; client-`{id}`-addressable collection with `ensure_owner_or_not_found`): an Admin has no
  "own" verification record to scope to at all, so `require_role(ROLE_ADMIN)` alone is the entire authorization
  boundary, structurally, on every route. Four routes: `GET /admin/verification/records` (AC1, paginated — this
  codebase's first real use of the previously-unused `CollectionResponse[T]`/`PaginationMeta` infrastructure),
  `POST .../records/{record_id}/approve` (AC2, AC4, AC6), `POST .../records/{record_id}/reject` (AC3, AC6,
  `RejectVerificationRequest.rejection_reason` structurally required via Pydantic `min_length=1`), and
  `GET .../documents/{document_id}/file` (a new **sibling** to the existing owner-only
  `GET /providers/me/verification/documents/{document_id}/file` — not a modification of it — with deliberately
  **no** ownership check, since an Admin correctly can fetch any provider's document).
- **`ProviderService.apply_verification_outcome`** (new method, `provider` module) — `verification`'s first
  *write* edge into `provider`, a natural, additive extension of the same constructor-injection, flush-only
  shape ADR-014/ADR-016/VER-001's own read-only edge already established four times.
- **Business Providers also become discoverable on approval** (Decision 5, confirmed by the user before
  implementation — see below) — `AdminVerificationService.approve` sets `is_discoverable=true` for **both**
  Freelancer and Business Providers; `reject` never sets it `true`, unconditionally, for either subtype.
- **DB-level `CHECK` constraint, `chk_providers_discoverable_requires_approved`** on `provider.providers`
  (`is_discoverable = false OR verification_status = 'approved'`) — genuine defense-in-depth for AC4's invariant
  alongside the service-layer transaction, mirroring `uq_saved_addresses_customer_default`'s (CUS-002/ADR-015)
  existing precedent of pairing a transactional mechanism with a DB-enforced one. Unconditional (applies to both
  subtypes), per Decision 5.
- **`backend/scripts/grant_admin_role.py`** (new, ops-only CLI) — looks up an already-registered user by phone
  via `UserRepository.get_by_phone`, then calls the existing, already-generic
  `RoleAssignmentService.ensure_role_assigned(user.id, ROLE_ADMIN)` and commits. Never exposed via HTTP; requires
  direct server/deployment access, the same trust boundary `seed_roles.py` already relies on. Never creates a new
  account — logs an error and exits non-zero if no matching user exists.
- **New exception**: `VerificationRecordNotActionableError` (409 — the record's current status is not
  `pending`/`under_review`, i.e. it was already approved/rejected by an earlier action).
- **Tests**: `test_admin_action_log_service.py`, `test_notification_service.py` (asserts persisted `title`/
  `body` never contain a raw enum token, matching the exact plain-language templates), `test_grant_admin_role.py`,
  `test_admin_verification_service.py` (the atomic status+discoverability update read back from the database
  after commit, the DB-level `CHECK` constraint exercised directly via a raw, bypassing `UPDATE`, rejection never
  setting `is_discoverable=true`, Decision 5's Business-approval behavior, the 409 on an already-actioned record,
  the notification/admin-log write-once guarantees, and — added during review — the concurrency regression test
  below), and `test_admin_verification_endpoints.py` (the full 401/403/200 matrix on all four routes, AC1's
  pagination, the admin document-download route's explicit no-ownership-check behavior against a *different*
  user's document).

### Two decisions the user explicitly confirmed before implementation

Per the Plan's own Delegation section, two decisions were flagged for explicit user confirmation before
`backend` began work, rather than assumed:

1. **Decision 1 — admin-role provisioning.** The user confirmed proceeding with the `grant_admin_role.py`
   CLI-script option (rather than the more minimal "manual SQL runbook note" alternative the Plan also offered).
   An Admin authenticates through the exact same existing OTP/Google/Apple sign-in flow every Customer/Provider
   already uses — no new login mechanism, no `email_password` admin-login endpoint, was built by this story
   (that remains explicitly deferred, a candidate for a future story bundled with the schema's already-reserved,
   still-unused `email_password`/`password_hash` scaffolding).
2. **Decision 5 — Business-provider discoverability on approval.** The user confirmed that approval sets
   `is_discoverable=true` for **both** Freelancer and Business Providers, not only Freelancers, despite AC2's
   Freelancer-specific literal wording. This resolved a real interpretive ambiguity the Plan flagged explicitly
   (the alternative reading — Business Providers never becoming discoverable through this endpoint at all —
   would have silently stranded every Business listing permanently invisible, since no other write path to
   `is_discoverable=true` exists anywhere in the shipped codebase).

---

## Review Process — a full, honest account

Like VER-001 before it, this story's review surfaced a real, substantive finding rather than a clean first pass.

### 1. A genuine, empirically-reproduced concurrency bug, found by the tester

The tester's independent QA — which had already run 443 backend tests passing and verified 7 of the story's 8
acceptance criteria with rigorous, direct evidence (including confirming the DB-level `CHECK` constraint
directly via `psql` against a fresh scratch database, not merely through pytest, and running the
`grant_admin_role.py` ops script live end-to-end) — found and reproduced a real bug in AC6/AC8's "exactly one"
guarantee: the original `approve`/`reject` implementation used a plain read-then-write pattern (fetch the
record, check its status in Python, then `UPDATE` it). Under true concurrency, two genuinely concurrent
`approve()` calls against the *same* record could both pass the in-Python status check before either call
committed — each going on to write its own `admin_action_log` row and its own `notifications` row for what
should have been a single logical action. This is a real correctness bug, not a theoretical one: it was
reproduced with two independent `AsyncSession`s bound to the same test engine, running two genuinely separate
Postgres transactions/connections concurrently via `asyncio.gather`.

**The fix** (`VerificationRecordRepository.try_claim_for_review`, `backend/app/modules/verification/
repositories/verification_record_repository.py`): a single, atomic conditional
`UPDATE verification_records SET status = ..., reviewed_by = ..., reviewed_at = ... WHERE id = :record_id AND
status IN ('pending', 'under_review')`, executed directly against the database rather than a Python-level
read-then-write. Postgres takes a row lock on whichever concurrent writer's `UPDATE` reaches the row first; the
second, genuinely concurrent `UPDATE` targeting the same row blocks until the first commits, then re-evaluates
its own `WHERE` clause against the now-already-transitioned row — so at most one caller's `UPDATE` can ever
match, regardless of true concurrency. The repository method returns whether the calling transaction won the
race (`rowcount == 1`); `AdminVerificationService._claim_record_or_raise` raises the existing
`VerificationRecordNotActionableError` (409) if it lost. This relies on Postgres's READ COMMITTED default (this
codebase sets no other isolation level); the method's own docstring notes that under SERIALIZABLE/REPEATABLE
READ the losing transaction would instead raise a serialization failure rather than affect zero rows — either
outcome still prevents the duplicate write this fix targets, so the fix is correct regardless of isolation
level, not merely correct under the specific level this codebase happens to use today.

A dedicated regression test, `TestConcurrentApprovalRace::test_two_concurrent_approve_calls_on_the_same_record_only_one_wins`
(`backend/tests/modules/verification/test_admin_verification_service.py`), runs two concurrent `approve()`
calls against the same record via `asyncio.gather` and each on its own independent `AsyncSession`/transaction,
asserting exactly one succeeds (`"approved"`) and the other loses the race and raises the 409
(`"conflict"`), and — the actual guarantee AC6/AC8 requires — that exactly one `admin_action_log` row and exactly
one `notifications` row exist for the record afterward, never two. This test was independently confirmed to
**fail** against the original read-then-write code (reproducing the bug) and to **pass** against the fixed
conditional-`UPDATE` code — not merely written after the fact and assumed correct.

### 2. The architect's review — independently re-verified the fix, not merely trusted it

The architect's review did not take the fix's correctness on faith: it independently reverted the conditional
`UPDATE` back to a plain read-then-write, re-ran the regression test to confirm it failed exactly as claimed,
then re-applied the fix and confirmed the test passed again — and separately reasoned through Postgres's actual
READ COMMITTED row-locking semantics to confirm the fix's own logic, rather than accepting the docstring's claim
at face value. The review returned **APPROVED WITH RECOMMENDATIONS**, with three non-blocking notes:

1. **Missing `alembic/env.py` model registrations** — the new `administration`/`notification` domain modules'
   `models.py` files were not yet imported in `backend/alembic/env.py`, meaning Alembic's `autogenerate` support
   would not see their tables in `target_metadata` even though the hand-written migrations themselves were
   already correct. **Fixed**: both `import app.modules.administration.models` and
   `import app.modules.notification.models` were added alongside the existing per-domain import list.
2. **A phone-number-in-logs issue in `grant_admin_role.py`** — an earlier version of the script's logging
   included the target phone number directly in a log line. **Fixed**: the script's logging now identifies the
   granted user only by `user.id` (`"Granted ROLE_ADMIN to user %s."`), never by phone number, and the
   "no such user" failure path logs no phone number either — consistent with `06_SECURITY.md`'s treatment of
   phone numbers as sensitive/PII.
3. **A docstring overclaim about isolation-level guarantees** — an earlier version of
   `try_claim_for_review`'s docstring implied the fix's correctness depended specifically on READ COMMITTED
   semantics. **Softened**: the docstring now states the fix is correct under READ COMMITTED (this codebase's
   actual configured default) *and* would remain correct under SERIALIZABLE/REPEATABLE READ via a different
   failure mode (a serialization error rather than a zero-row update) — an accurate statement of why the pattern
   is robust, not an overclaim tied to one specific isolation level.

All three recommendations have been addressed in the code as shipped; none were blocking to begin with.

### Final test count

**443 backend tests passing.** Independently confirmed via static analysis of the current test suite (this
session had no shell/pytest-execution access): 400 tests were confirmed passing at VER-001's own closeout, and
this story's five new test files/module additions
(`test_admin_action_log_service.py`, `test_notification_service.py`, `test_admin_verification_service.py`
— including the one new concurrency regression test — `test_admin_verification_endpoints.py`, and
`test_grant_admin_role.py`) contribute 42 test cases from the story's original implementation plus the one new
regression test added during review, for 43 new tests total — 400 + 43 = 443. No existing test was modified or
removed.

---

## Acceptance Criteria — Verification

All 8 acceptance criteria (from `Plan_S05_VER-002.md`, sourced from the Tracker) were independently verified by
the `tester` agent with direct, rigorous evidence — including confirming the DB-level `CHECK` constraint via a
raw `UPDATE` against a fresh scratch database (not merely through pytest) and running `grant_admin_role.py`
live, end-to-end. AC6/AC8 initially failed under true concurrency (see Review Process above) and are recorded as
Pass only after the fix landed and was independently re-verified.

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Admin-only endpoint lists `pending`/`under_review` verification records with linked documents | Pass |
| 2 | Approving sets `status=approved`, `reviewed_by`/`reviewed_at`, and atomically `providers.verification_status=approved` + (Freelancer) `is_discoverable=true` | Pass |
| 3 | Rejecting requires `rejection_reason`, sets `status=rejected`, never sets `is_discoverable=true` | Pass |
| 4 | A Freelancer's `is_discoverable` can never be true while the latest record's status isn't `approved` — asserted directly in an automated test, and DB-enforced | Pass |
| 5 | Provider receives a plain-language notification on status change, never exposing internal enum values | Pass |
| 6 | Every approval/rejection is written to `admin_action_log` — exactly once, even under concurrent action attempts | Pass (after concurrency fix — see Review Process) |
| 7 | A non-admin cannot access the review endpoint (403) | Pass |
| 8 | Automated tests cover the atomic status+discoverability update and the notification trigger | Pass (after concurrency fix — see Review Process) |

---

## Architect Review — Findings and Resolution

The architect's review confirmed, independently, that:

- **Decision 6 (the new, ownerless `require_role(ROLE_ADMIN)`-only authorization shape)** is a legitimate,
  correctly-reasoned third category alongside ADR-015's existing two — an Admin genuinely has no "own" resource
  to scope any of these four routes to, so no ownership check applies structurally, not by oversight.
- **Decision 4 (the atomic update plus the `CHECK` constraint)** — after the concurrency fix — correctly
  satisfies `04_DATABASE.md`'s Transactions section and this codebase's existing defense-in-depth precedent
  (`uq_saved_addresses_customer_default`).
- **Decision 2 (the new `administration` module vs. reusing `audit`)** is consistent with
  `02_ARCHITECTURE.md`'s domain-boundary rules and `03_DOMAIN_MODEL.md`'s own placement of `Admin Action Log`
  inside the Administration domain, not Verification or a generic audit concept.
- **Decision 3 (Notification domain's minimal first slice)** is held to the same honesty standard ADR-018/019
  were held to — a real `notifications` row, honestly recording what happened, with no pretense of real delivery
  infrastructure that doesn't exist.
- **Decision 7 (the new `verification → provider` *write* edge)** is consistent with ADR-014/016's established
  pattern and remains one-directional and cycle-free.
- **Decision 5's Business-approval interpretation** matches what the user confirmed before implementation.

The review returned **APPROVED WITH RECOMMENDATIONS** — see the three non-blocking notes in the Review Process
section above, all addressed.

---

## Documentation updated at story close

- **`docs/AI/09_DECISIONS.md`** — recorded **ADR-020** through **ADR-023** (see below); append-only, no existing
  entry modified.
- **`docs/AI/04_DATABASE.md`** — confirmed `administration.admin_action_log` and `notification.notifications`
  match what was actually built (both shipped with full `CommonColumnsMixin`, per the spec-literal reasoning in
  Decision 2/3, not the `audit_logs`-style immutable exemption); added
  `chk_providers_discoverable_requires_approved` to the `providers` table's Constraints list, which did not
  previously appear there since it was added by this story.
- **`docs/AI/03_DOMAIN_MODEL.md`** — reviewed the Administration and Notification domain sections; no edit made.
  This document has no existing pattern, anywhere, of annotating a domain's shipped-vs-planned implementation
  status — not even for domains (Identity, Customer, Provider) that are already fully or substantially shipped.
  Introducing such a note only for Administration/Notification would be an inconsistent, one-off addition to a
  document that is explicitly scoped to the business model, not implementation state (`04_DATABASE.md` and
  `PROJECT_IMPLEMENTATION_STATE.md` are where shipped-status is tracked). No change made, on the "don't
  over-edit" instruction.
- **`docs/AI/PROJECT_IMPLEMENTATION_STATE.md`** — VER-002 marked done in the Sprint 5 table; **Sprint 5 (Provider
  Verification) marked fully complete**, mirroring Sprint 4's own "Complete" header pattern; Executive Summary,
  Current Backend Capabilities, Repository State, Current Limitations, Overall Progress, and Next Planned Story
  sections all updated. Administration and Notification are no longer listed as "not yet implemented" — both now
  have real, if partial, first slices (an internal-only action log and an internal-only in-app notification
  record, respectively); explicitly still missing: any admin dashboard UI (mobile or web), any general-purpose
  admin-facing audit-log-viewing endpoint, real WhatsApp/SMS/Email delivery, `notification_preferences`, and
  `notification_delivery`.
- `docs/CHANGELOG.md` — new entry under `[Unreleased]`.

### Flagged, not fixed by this closeout

- **`docs/AI/Project_Tracker.xlsx`'s Stories sheet still needs its VER-002 row's Status updated from "Planned" to
  "Done"** — this requires the direct raw-XML cell-patching method established at prior closeouts (a normal
  openpyxl load/save round-trip was found to silently drop this workbook's conditional-formatting extensions).
  Not performed by this session — no xlsx-editing tool is available here; the top-level session's established
  method should be used separately.
- **`docs/AI/13_OPEN_DECISIONS.md`** is no longer "does not exist" (it was created and reconstructed earlier this
  session, from citations across the codebase) — but it remains explicitly marked **`Status: Draft — Reconstructed,
  pending CTO review`**, not a finished, authoritative record. Item 3 (Google Places Data Legal Review) and Item 4
  (Unclaimed Listing UX) both explicitly name **Sprint 6 (Directory & Listing Claims: DIR-001, CLM-001)** as
  blocked by their still-open status. This means **DIR-001's unblocked status cannot be asserted with full
  confidence** from the documentation available to this session — see the Next Planned Story note below.

---

## Testing Performed

- Static test-suite analysis (no shell/pytest-execution tool available to this session) confirming **443 backend
  tests** — see the Final Test Count note above for the derivation.
- `tester` agent: all 8 ACs independently verified with direct evidence, including a live, real `psql` session
  against a fresh scratch database to confirm the `CHECK` constraint (not merely a pytest assertion), a live
  end-to-end run of `grant_admin_role.py`, and the empirically-reproduced concurrency bug described above.
- `architect` agent: independently reverted and re-applied the concurrency fix to confirm it, reasoned through
  Postgres's actual isolation semantics, and returned **APPROVED WITH RECOMMENDATIONS** — three non-blocking
  notes, all addressed (see above).
- User sign-off received after both the tester's and architect's final verdicts were presented.

---

## Key Files

### Backend
- `backend/alembic/versions/*_administration_domain.py`, `*_notification_domain.py`,
  `*_provider_discoverability_invariant.py` (new)
- `backend/app/modules/administration/{models,dependencies}.py`,
  `repositories/admin_action_log_repository.py`, `services/admin_action_log_service.py` (new module)
- `backend/app/modules/notification/{models,dependencies}.py`,
  `repositories/notification_repository.py`, `services/notification_service.py` (new module)
- `backend/app/modules/verification/services/admin_verification_service.py` (new)
- `backend/app/modules/verification/admin_api.py` (new)
- `backend/app/modules/verification/repositories/verification_record_repository.py` —
  `try_claim_for_review` (the concurrency fix)
- `backend/app/modules/verification/schemas.py` — `AdminVerificationRecordResponse`,
  `RejectVerificationRequest`
- `backend/app/modules/provider/services/provider_service.py` —
  `apply_verification_outcome` (new)
- `backend/app/modules/provider/models.py` — `chk_providers_discoverable_requires_approved`
  in `Provider.__table_args__`
- `backend/app/core/exceptions/exceptions.py` — `VerificationRecordNotActionableError`
- `backend/scripts/grant_admin_role.py` (new)
- `backend/alembic/env.py` — `administration`/`notification` model imports (architect
  recommendation, addressed)
- `backend/tests/modules/administration/test_admin_action_log_service.py` (new)
- `backend/tests/modules/notification/test_notification_service.py` (new)
- `backend/tests/modules/verification/test_admin_verification_service.py` (new, includes the
  concurrency regression test)
- `backend/tests/modules/verification/test_admin_verification_endpoints.py` (new)
- `backend/tests/scripts/test_grant_admin_role.py` (new)

### Mobile

None — this story is backend-only, by deliberate design (see Scope Boundary above).

---

## Follow-up Notes for Sprint Planning

- **Sprint 5 (Provider Verification) is now fully complete** — both VER-001 and VER-002 have shipped and been
  signed off.
- **Next planned story: DIR-001**, the first story of Sprint 6 ("Directory & Listing Claims"), per this session's
  own working knowledge of the Tracker's sprint structure. **However, this cannot be asserted as fully unblocked
  with confidence**: `docs/AI/13_OPEN_DECISIONS.md` Item 3 (Google Places Data Legal Review) and Item 4
  (Unclaimed Listing UX) both explicitly name Sprint 6 (DIR-001/CLM-001) as blocked by their still-open status,
  and that document itself remains a reconstruction pending CTO review, not an authoritative source. A fresh Plan
  for DIR-001 should explicitly re-derive and confirm (or seek clarification on) this dependency before
  proceeding, rather than assuming it away.
- Non-blocking follow-ups carried forward from this story's architect review: all three recommendations were
  already addressed during this closeout (see Documentation updated section above) — nothing outstanding from
  VER-002 itself.
- **Cross-story documentation items, tracked but not newly created by this closeout:** the xlsx tracker's VER-002
  row still needs its Status flipped to "Done" (flagged above, not performed here); `13_OPEN_DECISIONS.md`
  remains a reconstruction pending real CTO review, not a finished record — the next story that needs to cite it
  should treat it accordingly, neither as fully authoritative nor as nonexistent.
