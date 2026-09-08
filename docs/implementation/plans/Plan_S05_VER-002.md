# Plan for Story VER-002 — Review Provider Verification as an Administrator

**Sprint:** 05 (Provider Verification) | **Epic:** ML5-EP02 | **Priority:** High | **Depends On:** VER-001 (done,
merged to this branch, on this same branch).

---

## Story

As an administrator, I want to review a provider's submitted documents and approve or reject with a reason, so
that only genuinely verified providers become discoverable — a safety requirement, not just a quality one, since
Freelancers enter customers' homes.

This story completes the Verification domain's trust-gate enforcement: approving or rejecting must atomically
update the provider's cached discoverability flag in the same transaction as the status change, and the provider
must be notified either way.

**Scope boundary:** does not include the broader admin operations dashboard (ADM-002) — this story is limited to
the verification-review action itself and its direct consequences (the atomic `providers` cache update, the
`admin_action_log` write, and the notification send). It does not build an admin web/mobile UI, an admin login
mechanism beyond what already exists, a general admin audit-log-viewing endpoint, or any part of ADM-002's wider
"operations dashboard" scope.

---

## Acceptance Criteria (authoritative — from `docs/AI/Project_Tracker.xlsx`, as supplied)

1. Admin-only endpoint lists pending/under_review `verification_records` with linked documents.
2. Approving a record sets `status=approved`, records `reviewed_by` and `reviewed_at`, and in the same
   transaction sets `providers.verification_status=approved` and, for Freelancers, `is_discoverable=true`.
3. Rejecting a record requires a `rejection_reason`, sets `status=rejected`, and does not set
   `is_discoverable=true` under any circumstance.
4. A Freelancer's `is_discoverable` can never be true while the latest `verification_records` status is anything
   other than `approved` — this invariant is asserted directly in an automated test.
5. The provider receives a notification on status change, worded in plain language, never exposing internal
   status enum values.
6. Every approval/rejection action is written to `admin_action_log`.
7. A non-admin cannot access the review endpoint (403).
8. Automated tests cover the atomic status+discoverability update and the notification trigger.

---

## Verified Current State (read directly from code and docs, not assumed)

- **`ROLE_ADMIN` already exists** as a real constant (`backend/app/core/constants.py`) and is already seeded
  idempotently into `identity.roles` (`backend/app/modules/identity/services/seed_data.py`'s `_SEED_ROLES`,
  confirmed by `backend/tests/modules/identity/test_seed_data.py`). `require_role()`
  (`backend/app/api/dependencies.py`) already accepts `ROLE_ADMIN` as a valid allowed-role argument — nothing
  about the role *catalog* or the *enforcement mechanism* needs to be built; both already exist from AUTH-004.
  `GET /auth/me` (AUTH-004) already demonstrates `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` as a
  working pattern.
- **No self-service or automatic path grants `ROLE_ADMIN` to any Account, and none should exist** (confirmed by a
  full grep of every `ensure_role_assigned`/`user_roles` call site — the only two production call sites are
  `AuthService`'s inline `ROLE_CUSTOMER` grant at registration and `ProviderService.create_provider`'s
  `ROLE_PROVIDER` grant via `RoleAssignmentService`, ADR-016). `RoleAssignmentService.ensure_role_assigned(user_id,
  role_name: str)` (`backend/app/modules/identity/services/role_assignment_service.py`) is **already fully
  generic** — it takes any role name and is already exercised in tests granting `ROLE_ADMIN`
  (`backend/tests/modules/identity/test_role_assignment_service.py`), so no change to this service is needed to
  support granting the Admin role; only a new caller is needed. See Decision 1.
- **A genuinely separate, currently-unused admin authentication path is already reserved in the schema**:
  `identity.users.auth_provider` includes `email_password` explicitly marked `(admin-only)` in
  `04_DATABASE.md`'s Enum Types table, and `users.password_hash` is documented as "Populated only for
  `email_password` auth (internal Admin accounts)." `AuthProvider.EMAIL_PASSWORD` exists as a model enum member
  and `app/core/security.py` already has working `hash_password`/`verify_password` (Argon2id) utilities — but
  **no endpoint anywhere in this codebase authenticates via email+password**, confirmed by reading every route in
  `identity/api.py` (only `request-otp`/`verify-otp`/`google`/`apple`/`refresh`/`sessions*`/`me` exist). Building
  a full email+password admin login flow is a materially larger scope than "the verification-review action and
  its direct consequences" this story is bounded to — it is its own future story (see Decision 1).
- **No `administration` module and no `notification` module exist anywhere** — confirmed by the full
  `backend/app/modules/**/*.py` glob (`audit`, `customer`, `identity`, `provider`, `verification` only). Both are
  genuinely new domain modules this story must create, exactly as VER-001 was the first module of the
  Verification domain (Decisions 2/3).
- **`04_DATABASE.md` already fully specifies both tables this story needs**, column-by-column:
  `administration.admin_action_log` (`admin_user_id`, `action_type`, `target_entity_type`, `target_entity_id`,
  `metadata`) and `notification.notifications` (`user_id`, `type`, `title`, `body`, `related_entity_type`,
  `related_entity_id`). Neither table is listed in `04_DATABASE.md`'s narrow exemption from the Common Columns
  convention (only `audit.audit_logs` and `search.search_event_log` are named exempt, in the Soft Delete
  section) — so, read literally, both get the full `CommonColumnsMixin` (versioned, soft-deletable), unlike the
  deliberately-immutable `audit_logs`. This is a real, non-obvious distinction from the `audit` module's shape
  and is honored literally rather than assumed away (Decision 2).
- **`customer.customer_preferences.notification_channel` (CUS-001) is never read by any code outside the
  `customer` module itself** — confirmed by a full grep for `notification_channel`: every hit is inside
  `customer/{models,schemas,services/customer_service,api}.py` or that module's own tests/migration. It is
  purely forward-looking schema with zero delivery mechanism behind it, exactly as flagged in the task framing.
  It also doesn't apply to a Provider recipient at all (a Provider has no `customer_profiles` row unless the same
  Account separately holds the Customer role) — so it cannot be reused as-is for notifying a Provider even if it
  were wired up. This confirms AC5 needs its own, new, minimal mechanism rather than reusing existing schema.
- **`app/shared/schemas/response.py`'s `CollectionResponse[T]`/`PaginationMeta` already exist** (Sprint 1,
  BF-010) but have never actually been used by any shipped endpoint yet — every prior collection endpoint in
  this codebase was either a `/me` singleton (ADR-015) or a small, owner-scoped collection exempted from
  pagination by ADR-012. `GET /admin/verification/records` (AC1) is a genuinely shared, platform-wide,
  unbounded-growth collection — ADR-012's exception does not apply — so this is this codebase's **first real use**
  of the pre-existing pagination infrastructure.
- **`ProviderService`/`ProviderRepository` currently have no write path that touches
  `verification_status`/`is_discoverable` after creation.** `create_provider` sets both unconditionally at
  creation time only (PRO-001); `update_basic_info` (PRO-002) explicitly excludes both fields from what
  `PATCH /providers/me` can touch. `ProviderRepository` inherits `get_by_id`/`update` generically from
  `BaseRepository[Provider]` (`backend/app/repositories/base_repository.py`) — both already sufficient for this
  story's new write, with no new repository method needed beyond a small batch-fetch helper (Decision 9).
- **`verification/services/verification_service.py`'s existing `verification → provider` edge (Decision 9,
  VER-001) is read-only** (`ProviderService.get_my_provider`, a pure read). This story needs the first *write*
  edge from `verification` into `provider` — a natural, additive extension of the same cross-module
  constructor-injection shape ADR-014/ADR-016/VER-001-Decision-9 already established four times, not a new kind
  of coupling (Decision 7).
- **ADR-019's own Consequences section already anticipated this exact story**: "The authenticated
  document-download endpoint's ownership check is written so a future VER-002 admin-review surface can extend it
  to 'owner OR an Admin' without restructuring the storage split itself." Read directly:
  `VerificationService.get_document_bytes` calls `ensure_owner_or_not_found` unconditionally; extending it in
  place to special-case "or the caller is an Admin" would blur the meaning of a route mounted under
  `/providers/me/...` (a `/me` path returning someone *else's* provider's document reads as a contradiction in
  terms). This Plan instead adds a **sibling** admin-only method/route with no ownership check at all
  (Decision 6) — consistent with ADR-019's intent (reusing the same private-storage `FileStorage.read` plumbing,
  not restructuring it) without overloading the `/me` path's semantics.
- **VER-001's Decision 5 already predicted where this story's admin surface belongs**: "once VER-002 ships,
  Verification gains its own admin-facing surface Provider has no reason to know about." This directly settles
  the module-placement question for the *review orchestration* code (not the `admin_action_log` table itself,
  which is a genuinely separate Administration-domain concept — see Decision 2): the new admin endpoints and
  their service logic belong inside the existing `backend/app/modules/verification/` module, mounted at a
  different URL prefix, exactly mirroring VER-001 Decision 5's "code and URL are deliberately decoupled" framing.
- **`15_SCREEN_INVENTORY.md`'s own "Explicitly Out of Scope" section already states**: "Admin dashboard... is
  not included [in the 28-screen MVP inventory]... Recommend treating it as a separate internal web tool rather
  than adding 4–5 more screens to the consumer app." Combined with `14_USER_FLOWS.md` Flow 6 (Admin Verification
  Review) describing a generic "Admin opens the queue" step with no reference to the Flutter app at all, this
  story is **backend-only by design**, not an oversight — see the Mobile section below.
- `docs/AI/13_OPEN_DECISIONS.md` still does not exist as a real, CTO-authored document (only the reconstructed
  placeholder created this session) — not directly load-bearing for this story's scope (no item it tracks blocks
  VER-002 the way item 5 blocked VER-001's Business bar), but flagged again per the existing three-strikes
  precedent, for completeness.

---

## Architecture Decisions

### Decision 1 — Admin-role provisioning: reuse the existing OTP/OAuth login + a new, ops-only CLI script calling `RoleAssignmentService`; the `email_password`/`password_hash` admin-login path is explicitly deferred, not built here

**This decision is flagged for explicit user confirmation before `backend` implements this specific piece — see
the Delegation section.** There is, and per the story's own framing should remain, no self-service "become an
admin" flow. The question is how a real Admin Account gets `ROLE_ADMIN` at all in this environment, since
`require_role(ROLE_ADMIN)`-gated endpoints cannot be meaningfully exercised end-to-end (outside of test fixtures
that already bypass this question entirely, see below) without one.

**Decision:** an Admin authenticates through the **exact same existing** mobile-OTP or Google/Apple sign-in flow
any Customer/Provider already uses — no new login mechanism is built by this story. A new, small, ops-only CLI
script, `backend/scripts/grant_admin_role.py`, mirrors the existing `backend/scripts/seed_roles.py` precedent
exactly (`uv run python -m scripts.grant_admin_role --phone-country-code +971 --phone-number 501234567`):
looks up the target `identity.users` row via the existing `UserRepository.get_by_phone`, then calls
`RoleAssignmentService.ensure_role_assigned(user.id, ROLE_ADMIN)` and commits. It requires the target person to
already have a real, already-registered Account (through the ordinary Flow 1 registration path) — granting a
role to an *existing* Account is categorically different from a self-service "sign up as an admin" path, which
this deliberately remains incapable of. The script is never exposed via HTTP and requires direct
server/deployment access to run — the same trust boundary `seed_roles.py` already relies on.

The schema's own `email_password`/`password_hash` reservation (confirmed genuinely unused today, Verified
Current State above) is read as forward-looking scaffolding for a **future, separate Admin Portal login story**
(plausibly bundled with ADM-002's own "admin operations dashboard" work, which this story's own scope boundary
explicitly excludes) — not something VER-002 should build a slice of. Building even a minimal email+password
login endpoint would be new authentication surface, its own security review, and its own test suite — a
materially larger addition than "the verification-review action and its direct consequences."

**Testing is not blocked by this decision either way**: `backend`'s test fixtures can create an admin-role test
user by calling `RoleAssignmentService.ensure_role_assigned(user.id, ROLE_ADMIN)` directly against the test
database, exactly mirroring how `test_role_assignment_service.py` already does today, and exactly how every
other role (`ROLE_CUSTOMER`, `ROLE_PROVIDER`) is already granted in test fixtures throughout the codebase (e.g.
`subject=str(user_id), roles=[ROLE_CUSTOMER], jti=...` token-building helpers already used by every existing
endpoint test file). AC7 ("a non-admin cannot access the review endpoint") is fully testable with a
`ROLE_CUSTOMER`/`ROLE_PROVIDER`-only test user and requires no admin-provisioning mechanism to exist at all.

**Alternatives considered:**
- **Build the full `email_password` admin login endpoint now** — rejected as materially out of this story's
  scope boundary (new auth surface, not "the review action's direct consequences"); flagged as a candidate for
  a future dedicated story instead.
- **No script at all — document a manual `INSERT INTO identity.user_roles ...` SQL statement as an ops runbook
  note** — a strictly more minimal option than the CLI script, with zero new code. Considered a legitimate
  fallback if the user prefers not to add even a small script; the CLI script is proposed as the default because
  it is safer (idempotent, reuses tested application code, cannot construct a malformed row) and costs very
  little, mirroring `seed_roles.py`'s own precedent almost exactly — but this Plan does not treat that
  preference as settled without the user's confirmation.

### Decision 2 — `admin_action_log` lives in a new, first-of-its-kind `administration` domain module — not an extension of `audit`; built with `CommonColumnsMixin`, per `04_DATABASE.md`'s literal (non-exempted) spec

`06_SECURITY.md`'s Audit Logging section lists "Admin Actions"/"Administrative Changes"/"Provider Verification
Status Changes" alongside "Login"/"Logout"/"Registration" as tracked event categories — read superficially, this
could suggest reusing `audit.audit_logs` (which already has a generic `action`/`entity_type`/`entity_id`/
`before_state`/`after_state` shape structurally very close to `admin_action_log`'s columns). This Plan does
**not** take that path, for two independent, decisive reasons:

1. **AC6's own literal wording** names the table directly: "Every approval/rejection action is written to
   `admin_action_log`" — not "the audit log." `04_DATABASE.md` already fully specifies `administration.
   admin_action_log` as its own table under its own schema, with its own column names
   (`admin_user_id`/`action_type`/`target_entity_type`/`target_entity_id`/`metadata`) — genuinely different names
   from `audit_logs`' (`actor_user_id`/`action`/`entity_type`/`entity_id`/`before_state`/`after_state`), not a
   coincidental near-duplicate. Writing into `audit_logs` instead would silently ignore both the AC's explicit
   name and the pre-existing schema spec, exactly the kind of "structurally similar, but not textually
   authorized" substitution this codebase has consistently avoided (VER-001 Decision 1 refused to invent a
   parallel `verification_status` enum for the same reason, in the opposite direction — reuse only what is
   actually specified to be reused).
2. **`03_DOMAIN_MODEL.md`'s own domain boundaries** place `Admin Action Log` inside the **Administration**
   domain's entity list, a peer of `Admin User`, `Manual Match Assignment`, and `Unmatched Query Report` — not
   inside `Verification` or a generic cross-cutting `audit` concept. The Administration domain is explicitly a
   distinct, larger, still-mostly-unbuilt domain (`14_USER_FLOWS.md` Flow 7 — Wizard-of-Oz manual match; the
   story's own scope boundary naming ADM-002, "the broader admin operations dashboard," as a *sibling*, not a
   part of, this story). VER-002 is this domain's **first slice**, exactly the same shape as `audit` being
   AUTH-004's first slice of a cross-cutting concern and `verification` being VER-001's first slice of its own
   domain.

**Decision:** a new `backend/app/modules/administration/` module, mirroring `audit`'s own minimal footprint
(model → repository → service → dependencies; **no `api.py`/`schemas.py`**, since nothing in `administration`
is directly HTTP-exposed by this story — it is called internally by `verification`'s new admin service, exactly
as `identity` calls `audit`'s service internally). `AdminActionLog(CommonColumnsMixin, Base)` — deliberately
**not** built exempt like `AuditLog`, because `04_DATABASE.md`'s Soft Delete section names only `audit_logs` and
`search_event_log` as exempt from Common Columns; `admin_action_log` is not on that list, so it is built exactly
as every other ordinary business table in this codebase (versioned, soft-deletable), even though this means an
admin-action row is not literally immutable the way `audit_logs`' rows are. This is a deliberate, spec-literal
choice, called out explicitly for `architect`'s attention rather than silently assumed to need `audit_logs`'
immutability treatment by analogy.

`AdminActionLogRepository(BaseRepository[AdminActionLog])` needs no custom methods beyond the inherited
`create`. `AdminActionLogService` exposes one explicit method (mirroring `AuditService`'s "explicit methods, not
one generic `record()`" convention): `record_verification_review(*, admin_user_id, verification_record_id,
provider_id, decision: Literal["approved", "rejected"], rejection_reason: str | None) -> AdminActionLog`.

**Alternatives considered and rejected:**
- **Extend `audit.audit_logs` with the admin-action events instead** — rejected per the two reasons above; also
  would have required either overloading `audit_logs`' generic `action`/`entity_type` columns with
  admin-specific semantics or leaving `admin_action_log` (the table `04_DATABASE.md` and AC6 both name
  explicitly) permanently unbuilt.
- **Put `AdminActionLog` inside the `verification` module instead of a new `administration` module** — rejected:
  `admin_action_log` is explicitly reusable by *any* future admin action (Manual Match Assignment review,
  Unmatched Query Report actioning, ADM-002's wider dashboard), not something scoped to Verification alone;
  colocating it inside `verification` would misrepresent its actual domain ownership the same way VER-001
  itself rejected colocating verification code inside `provider`.

### Decision 3 — Notification domain, first slice: a new `notification` module with the `notifications` table only — no `notification_delivery`, no `notification_preferences`, in-app-record-only, explicitly interim

`03_DOMAIN_MODEL.md`'s Notification domain and `PROJECT_IMPLEMENTATION_STATE.md`'s Current Limitations both
state Notifications are "not yet implemented" anywhere in this codebase, and Sprint 12 ("Engagement & Trust," per
the Tracker's sprint list) is this domain's own dedicated milestone — building a full WhatsApp/SMS/Email delivery
pipeline now would be significantly out of this story's scope. At the same time, AC5 is a hard, literal
requirement ("The provider receives a notification on status change") that cannot honestly be satisfied by a
silent no-op.

**Decision:** a new `backend/app/modules/notification/` module — the first module of the Notification domain,
the same "first slice of a real domain" shape `verification` itself was for VER-001. It builds **only**
`notification.notifications` (`user_id`, `type`, `title`, `body`, `related_entity_type`, `related_entity_id`),
exactly per `04_DATABASE.md`'s pre-existing spec, using `CommonColumnsMixin` (not exempted, same reasoning as
Decision 2). It deliberately does **not** build `notification_delivery` (there is no real channel to have a
delivery status for — WhatsApp/SMS/Email sending doesn't exist) or `notification_preferences` (there is nothing
to opt in/out of yet; `customer.customer_preferences.notification_channel`'s own precedent already shows this
codebase is comfortable shipping forward-looking preference schema before the mechanism it configures exists,
but building a *second* one here, for Providers, with no real channel behind either, would be speculative
infrastructure this story doesn't need). A `notifications` row records, honestly, that "a notification of this
type, with this plain-language content, was generated for this user" — nothing more. This directly mirrors
ADR-018 (`StubDocumentOcrService`, honestly does nothing yet) and ADR-017 (`LocalFileStorage`, honestly interim
pending real infrastructure): not a silent no-op, and not a full build-out of Sprint 12's real scope either.

No `api.py`/`schemas.py` in this module — no AC requires a "read my notifications" endpoint (S-13 Notifications
Inbox is out of scope, per the Mobile section below), so nothing here is HTTP-exposed. `NotificationService`
exposes one explicit method: `notify_verification_status_change(*, user_id, approved: bool, rejection_reason:
str | None) -> Notification`, with **hardcoded, plain-language copy** — never simply interpolating the raw
`VerificationStatus` enum member into `title`/`body` (AC5's literal "never exposing internal status enum
values"):
- Approved: `title="Verification approved"`, `body="Great news — your verification has been approved. Your
  listing is now visible to customers."`
- Rejected: `title="Verification update"`, `body=f"We weren't able to verify your submission. Reason:
  {rejection_reason}. You can review the details and resubmit your documents."`

`type="verification_status_change"` (matching `04_DATABASE.md`'s own example value for this column),
`related_entity_type="verification_record"`, `related_entity_id=<the record's id>`.

**Alternatives considered and rejected:**
- **Build the full three-table Notification domain now** (`notification_delivery` + `notification_preferences`
  too) — rejected as materially out of scope; no real channel exists to deliver through or a preference to
  respect yet, and Sprint 12 is this domain's own dedicated milestone.
- **Skip AC5 with a no-op / log line only** — rejected outright; AC5 is a literal, testable acceptance criterion
  ("automated tests cover... the notification trigger," AC8), not an aspiration; a genuine `notifications` row is
  the honest minimum that satisfies it.
- **Reuse/extend `customer.customer_preferences`** — rejected; it is Customer-domain schema with zero delivery
  mechanism behind it today (Verified Current State), and does not even apply to a Provider recipient without a
  Customer profile on the same Account.

### Decision 4 — Atomic status+discoverability update: a single-transaction service method, plus a new DB-level `CHECK` constraint on `providers` as defense-in-depth for AC4's invariant

AC2/AC3 require the `verification_records` status write and the `providers.verification_status`/`is_discoverable`
cache write to happen "in the same transaction." AC4 goes further, requiring the invariant itself ("a Freelancer's
`is_discoverable` can never be true while the latest `verification_records` status is anything other than
`approved`") to be "asserted directly in an automated test" — the strongest wording of any AC in this story.

**Decision:** the transactional half is achieved exactly the way every prior cross-module atomic write in this
codebase has been (ADR-014/ADR-016/VER-001's own Decision 2/9): one service method,
`AdminVerificationService.approve`/`.reject`, does all of its work — the `verification_records` update, the
`ProviderService.apply_verification_outcome` call (new method, `provider` module, Decision 7), the
`admin_action_log` write (Decision 2), and the `notifications` write (Decision 3) — on the **same**
request-scoped `AsyncSession`, flush only, never a nested commit; the endpoint's single, pre-existing
`await db.commit()` remains the only transaction boundary, so every write lands together or none do.

For AC4's invariant specifically, this Plan adds a genuine **second, independent layer**: a new database-level
`CHECK` constraint on `provider.providers`, `chk_providers_discoverable_requires_approved: is_discoverable =
false OR verification_status = 'approved'`. This directly encodes the invariant as a hard, DB-enforced rule —
not just "the service happens to always write both fields together" — mirroring this codebase's existing
defense-in-depth precedent (`uq_saved_addresses_customer_default`, CUS-002/ADR-015's supporting partial unique
index alongside its own transactional mechanism). This constraint applies to **every** Provider, not only
Freelancers, because Decision 5 below establishes that `is_discoverable` is gated on `verification_status =
approved` for Business Providers too under the current design — a strictly *stronger*, always-true invariant for
both subtypes, not a Freelancer-specific carve-out that would need a `provider_type`-conditional `CHECK`
expression (which Postgres `CHECK` constraints can express perfectly well via a `CASE`, but isn't needed here
since the simpler, unconditional form already holds for both).

AC4's own automated test therefore has two independent things to prove: (a) the service-layer transaction
never produces a state where `is_discoverable=true` and `verification_status != approved` on the same row, and
(b) a direct attempt to write such a row (bypassing the service layer entirely, e.g. a raw `UPDATE` in a test)
is rejected by the database itself — the DB constraint, exercised directly, not merely inferred from the service
code's behavior.

**Alternatives considered and rejected:**
- **Service-layer transaction only, no DB constraint** — rejected: AC4's own wording ("can never be true...
  under any circumstance," echoed by AC3) is unusually emphatic among this story's ACs, and a DB-level
  constraint is a proportionate, cheap, well-precedented response, not overengineering.
- **A trigger instead of a `CHECK` constraint** — rejected as unnecessary complexity; a `CHECK` constraint
  expresses this exact invariant declaratively with no procedural code to maintain, and `04_DATABASE.md` already
  uses partial unique indexes (a comparable declarative mechanism) elsewhere rather than triggers.
- **A `provider_type`-conditional `CHECK` (Freelancer-only)** — rejected once Decision 5 establishes the
  unconditional invariant actually holds for both subtypes under the current design; a conditional expression
  would be needless complexity for a rule that's already unconditionally true.

### Decision 5 — `is_discoverable=true` on approval applies to both Freelancer and Business Providers, not only Freelancer, despite AC2's Freelancer-specific literal wording

AC2 states discoverability becomes true "for Freelancers" specifically on approval, without saying what happens
for an approved Business Provider. Read in isolation, this could imply Business Providers *never* become
discoverable through this endpoint at all. This Plan reads AC2's Freelancer-specific phrasing as calling out the
**safety-critical, mandatory** case explicitly (consistent with the story's own framing — "a safety requirement...
since Freelancers enter customers' homes") rather than as a deliberate Business exclusion, for three concrete,
codebase-grounded reasons:

1. `04_DATABASE.md`'s own `providers.is_discoverable` column note already frames Business discoverability as
   **configurable in whether verification is required at all**, not in whether an *approval* unlocks visibility:
   "Computed at write-time from `verification_status` (mandatory `approved` for Freelancer; configurable for
   Business...)." The configurability lives in `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED`/
   `BUSINESS_VERIFICATION_TYPE` (VER-001, Decision 3) — i.e. *whether/what* a Business must submit — not in
   whether a subsequent admin approval fails to unlock visibility.
2. **Every Provider, Business or Freelancer, is created with `is_discoverable=false` unconditionally**
   (PRO-001) and has no other write path to `true` anywhere in the shipped codebase (Verified Current State) —
   if Business approval didn't also set `is_discoverable=true`, no Business Provider could *ever* become
   discoverable through any code that exists today, which would silently strand every Business listing
   permanently invisible — a much larger, unstated behavior change than AC2's narrow wording plausibly intends.
3. VER-001's own Decision 3 already established that a Business Provider goes through the **same**
   `verification_records` submission cycle as a Freelancer (with a possibly-empty document set) — meaning
   Business submissions already land in the same admin review queue this story builds, and are expected to be
   approved/rejected through the same two endpoints.

**Decision:** `AdminVerificationService.approve` sets `is_discoverable=true` on approval for both subtypes;
`AdminVerificationService.reject` never sets it `true` for either (AC3, unconditionally). This is called out
explicitly for `architect`'s and the user's attention as an interpretive judgment call on a not-fully-specified
AC, not a silent assumption — if the intended product behavior is actually "Business Providers require a
separate, later decision before becoming discoverable even after approval" (echoing `13_OPEN_DECISIONS.md` item
5's still-open status), that would be a explicit correction to make before implementation, not after.

### Decision 6 — Endpoint shapes and authorization model: a new, ownerless `require_role(ROLE_ADMIN)`-only authorization shape, extending ADR-015's framework with a genuinely third category

ADR-015 established exactly two shapes for "a resource scoped to the authenticated caller": a `/me` singleton
(structural ownership, no `{id}`) and a client-`{id}`-addressable collection (defensive `ensure_owner_or_not_found`
ownership checks). **This story's endpoints are neither** — an Admin has no "own" verification record to scope
to at all; every record in the queue belongs to some *other* user's Provider. `require_role(ROLE_ADMIN)` alone
is the entire authorization boundary; no ownership check of any kind applies, structurally, because none would
even make sense here. This is flagged as a genuinely new, third authorization shape for `architect`'s explicit
review and is a strong candidate for its own ADR at story close, extending ADR-015's framework rather than
contradicting it.

**Endpoint shapes** (new router, `backend/app/modules/verification/admin_api.py`, mounted at `/admin/verification`
— a new prefix alongside the existing `/providers/me/verification` mount, per `05_API_GUIDELINES.md`'s own
Endpoint Organization list, which already names `/admin` as an anticipated top-level namespace):

- **`GET /admin/verification/records`** (AC1, AC7) — `require_role(ROLE_ADMIN)`. Lists `verification_records`
  whose `status` is `pending` or `under_review` (hardcoded server-side filter; no AC asks for a browsable
  full-history view of every status, so none is built), ordered oldest-`submitted_at`-first (a review queue
  should not let an old submission be perpetually skipped by newer ones jumping the line), each with its
  documents (`file_download_url` pointing at the new admin-only download route below) and enough Provider
  context for an admin to act meaningfully (`provider_id`, `provider_display_name`, `provider_type`). This is a
  genuinely shared, platform-wide, unbounded-growth collection — **paginated** per `05_API_GUIDELINES.md`'s
  default rule (ADR-012's small-owned-collection exception does not apply here), using the pre-existing,
  previously-unused `CollectionResponse[T]`/`PaginationMeta` (Verified Current State).
- **`POST /admin/verification/records/{record_id}/approve`** (AC2, AC4, AC6, AC7) — `require_role(ROLE_ADMIN)`,
  no request body. 409 (`VerificationRecordNotActionableError`, new) if the record's current `status` is not
  `pending` or `under_review` (i.e. it was already approved/rejected by an earlier action — cannot be re-acted
  on). No separate "mark as under review" transition endpoint exists (see Decision 8) — approve/reject act
  directly from either starting state.
- **`POST /admin/verification/records/{record_id}/reject`** (AC3, AC6, AC7) — `require_role(ROLE_ADMIN)`, body
  `{rejection_reason: str}` with Pydantic `min_length=1` (structural enforcement of "requires a
  rejection_reason" — a request with a missing/empty reason 422s before the service layer ever runs, the same
  "let Pydantic handle it, don't invent a redundant exception" lesson VER-001's review already surfaced when the
  tester removed the dead `InvalidVerificationFieldsError`). Same 409 conflict rule as approve.
- **`GET /admin/verification/documents/{document_id}/file`** (AC1, AC7) — `require_role(ROLE_ADMIN)`. A new,
  **sibling** endpoint to the existing owner-only `GET /providers/me/verification/documents/{document_id}/file`
  — not a modification of it (see Verified Current State's ADR-019 discussion). Calls a new
  `VerificationService.get_document_bytes_for_admin(document_id)` method: looks the document up, 404s
  (`VerificationDocumentNotFoundError`, reused) if it doesn't exist at all, and streams its bytes via the same
  private `FileStorage.read` plumbing Decision 7 of VER-001 already built — with **no ownership check**, since
  `require_role(ROLE_ADMIN)` is the entire authorization boundary for this route.

**Alternatives considered and rejected:**
- **Extend the existing `get_document_bytes`/`/providers/me/...` route in place to accept "owner OR Admin"** —
  rejected: a route under `/providers/me/...` returning a *different* provider's document reads as a
  contradiction of the path's own `/me` semantics (ADR-015), even if technically guarded correctly; a sibling
  route under `/admin/...` is clearer and costs one small new method, reusing all the same underlying plumbing
  ADR-019 already built.
- **Nest the admin routes under `/providers/{provider_id}/verification/...`** — rejected: the admin is not
  acting "as" or "on behalf of" a specific known provider in the listing call (AC1 lists across *all*
  providers), and the approve/reject/download actions are keyed by `verification_record_id`/`document_id`
  directly, which is simpler and avoids a redundant, potentially-inconsistent `provider_id` path segment.

### Decision 7 — Cross-module edges: `verification → provider` gains a write method; new `verification → administration` and `verification → notification` edges

`AdminVerificationService` (new, `backend/app/modules/verification/services/admin_verification_service.py` — a
separate class from the existing, provider-facing `VerificationService`, since its authorization model,
side effects, and callers are entirely different; Single Responsibility, not a God class) depends on:

- **`ProviderService`** (existing edge, extended) — a new method, `apply_verification_outcome(provider_id, *,
  verification_status: VerificationStatus, is_discoverable: bool) -> Provider`, using `ProviderRepository`'s
  already-inherited `get_by_id`/`update` (no new repository method needed there). This is `verification`'s first
  *write* into `provider`-schema data — a natural, additive extension of the same constructor-injection,
  flush-only shape ADR-014/ADR-016/VER-001-Decision-9 already established four times, not a new kind of
  coupling. `provider`'s code gains zero new imports from `verification`, preserving the one-directional,
  cycle-free property every prior edge has had.
- **`AdminActionLogService`** (new, `administration` module, Decision 2).
- **`NotificationService`** (new, `notification` module, Decision 3).
- The existing `VerificationRecordRepository`/`VerificationDocumentRepository` (same module, no new edge).

All four dependencies are wired via constructor injection through a new `get_admin_verification_service()`
provider in `verification/dependencies.py`, importing `get_provider_service`, a new `get_admin_action_log_service`
(from `administration/dependencies.py`), and a new `get_notification_service` (from
`notification/dependencies.py`) — the identical shape every prior cross-module edge in this codebase has used.

### Decision 8 — No separate "start review" (`pending → under_review`) transition endpoint

AC1 only requires *listing* records in either `pending` or `under_review` — no AC asks for an admin action that
moves a record from `pending` to `under_review` before approving/rejecting it. Building one would be an
unrequested state-machine step with no consumer. `approve`/`reject` accept a record in either starting state
directly (Decision 6's 409 check only rejects records that are *already* `approved`/`rejected`).

**Alternative considered and rejected:** add a `POST .../start-review` endpoint for completeness with the domain
model's four-state lifecycle — rejected as unrequested scope; if a future story needs to track "an admin is
actively looking at this one" as a distinct, contended state (e.g. to prevent two admins double-acting on the
same record), that is exactly the kind of concern ADM-002's "broader admin operations dashboard" is positioned
to solve, not this story.

### Decision 9 — Admin response enrichment: batch Provider lookup, no new cross-schema ORM relationship

`VerificationRecord` has no ORM `relationship()` to `Provider` (only a plain FK column, per VER-001 Decision 2's
"never touches the `providers` table" framing, which this Plan does not disturb for the *model* layer even
though the *service* layer now writes to `provider` via Decision 7). Building the admin list response (Decision
6) needs each record's Provider's `display_name`/`provider_type` for admin usability. Rather than adding an ORM
relationship (which would blur the deliberate schema-level separation) or querying `providers` once per record
(N+1), `AdminVerificationService.list_pending_for_review` collects the distinct `provider_id`s from one page of
records, calls a new, small `ProviderRepository.list_by_ids(ids: list[uuid.UUID]) -> list[Provider]` (one query,
`WHERE id IN (...)`), and zips the results together in the service layer before returning to the API layer.

---

## Backend — Proposed Changes

### Migrations
1. `administration_domain` — new Alembic migration (down-revision = VER-001's head). Creates the `administration`
   Postgres schema and `administration.admin_action_log` exactly per `04_DATABASE.md`'s spec, with
   `CommonColumnsMixin` columns (Decision 2), plus `idx_admin_action_log_admin_user_id`/
   `idx_admin_action_log_created_at`.
2. `notification_domain` — new Alembic migration. Creates the `notification` Postgres schema and
   `notification.notifications` only (Decision 3), exactly per spec, with `idx_notifications_user_id`/
   `idx_notifications_created_at`. No `notification_delivery`/`notification_preferences` tables.
3. `provider_discoverability_invariant` — new, narrow Alembic migration altering the existing
   `provider.providers` table to add `chk_providers_discoverable_requires_approved` (Decision 4). No column
   changes.
4. Verify upgrade/downgrade for all three against a disposable scratch database (ADR-013's precedent).

### Models
5. `backend/app/modules/administration/models.py` (new) — `AdminActionLog(CommonColumnsMixin, Base)`.
6. `backend/app/modules/notification/models.py` (new) — `Notification(CommonColumnsMixin, Base)`.
7. `backend/app/modules/provider/models.py` — no column changes; the new `CheckConstraint` is declared in
   `Provider.__table_args__` to keep the ORM model and the migration in sync.

### Repositories
8. `backend/app/modules/administration/repositories/admin_action_log_repository.py` (new) —
   `AdminActionLogRepository(BaseRepository[AdminActionLog])`, no custom methods.
9. `backend/app/modules/notification/repositories/notification_repository.py` (new) —
   `NotificationRepository(BaseRepository[Notification])`, no custom methods.
10. `backend/app/modules/verification/repositories/verification_record_repository.py` — new
    `list_for_review(*, offset: int, limit: int) -> tuple[list[VerificationRecord], int]` (filters `status IN
    (pending, under_review)`, orders by `submitted_at` ascending, returns the page plus a total count for
    `PaginationMeta`).
11. `backend/app/modules/provider/repositories/provider_repository.py` — new `list_by_ids(ids: list[uuid.UUID])
    -> list[Provider]` (Decision 9).

### Services
12. `backend/app/modules/administration/services/admin_action_log_service.py` (new) — `AdminActionLogService`
    (Decision 2).
13. `backend/app/modules/notification/services/notification_service.py` (new) — `NotificationService` (Decision
    3).
14. `backend/app/modules/provider/services/provider_service.py` — new `apply_verification_outcome(provider_id,
    *, verification_status, is_discoverable) -> Provider` (Decision 7); raises `ProviderNotFoundError` if the id
    doesn't resolve (defensive — should not happen given Decision 6's flow, but never silently no-ops).
15. `backend/app/modules/verification/services/admin_verification_service.py` (new) — `AdminVerificationService`
    (Decisions 4–9): `list_pending_for_review(*, page, page_size) -> tuple[list[VerificationRecord],
    dict[uuid.UUID, Provider], dict[uuid.UUID, list[VerificationDocument]], int]`, `approve(admin_user_id, *,
    record_id) -> VerificationRecord`, `reject(admin_user_id, *, record_id, rejection_reason: str) ->
    VerificationRecord`, `get_document_bytes_for_admin(document_id) -> tuple[bytes, DocumentType]`.

### Exceptions (`backend/app/core/exceptions/exceptions.py`)
16. `VerificationRecordNotActionableError` (409 — the record's current status is not `pending`/`under_review`).

### Schemas (`backend/app/modules/verification/schemas.py`, extended)
17. `AdminVerificationRecordResponse { id, provider_id, provider_display_name, provider_type, verification_type,
    status, submitted_at, reviewed_at, rejection_reason, documents: list[VerificationDocumentResponse] }` (the
    documents' `file_download_url` points at the new `/admin/verification/documents/{id}/file` route).
    `RejectVerificationRequest { rejection_reason: str = Field(..., min_length=1, max_length=2000) }`.

### API
18. `backend/app/modules/verification/admin_api.py` (new) — the four routes from Decision 6, all gated by
    `Depends(require_role(ROLE_ADMIN))` and nothing else (no ownership dependency of any kind).
19. `backend/app/api/v1/api.py` — `v1_router.include_router(admin_verification_router, prefix=
    "/admin/verification")`.
20. `backend/tests/conftest.py` — import `app.modules.administration.models` and
    `app.modules.notification.models` so their tables join `Base.metadata` for the test suite's create/drop
    lifecycle (ADR-013's established pattern).

### Dependencies
21. `backend/app/modules/administration/dependencies.py` (new) — `get_admin_action_log_repository`,
    `get_admin_action_log_service`.
22. `backend/app/modules/notification/dependencies.py` (new) — `get_notification_repository`,
    `get_notification_service`.
23. `backend/app/modules/verification/dependencies.py` — `get_admin_verification_service` (imports
    `get_provider_service` from `provider/dependencies.py`, `get_admin_action_log_service` from
    `administration/dependencies.py`, `get_notification_service` from `notification/dependencies.py`, per
    Decision 7).

### Ops script (pending user confirmation, Decision 1)
24. `backend/scripts/grant_admin_role.py` (new) — CLI, mirrors `seed_roles.py`'s exact shape; looks up a user by
    phone via `UserRepository.get_by_phone`, calls `RoleAssignmentService.ensure_role_assigned(user.id,
    ROLE_ADMIN)`, commits. Never exposed via HTTP.

### Tests
25. `backend/tests/modules/administration/test_admin_action_log_service.py` (new).
26. `backend/tests/modules/notification/test_notification_service.py` (new) — asserts the persisted `title`/
    `body` never contain the raw enum token (`"VerificationStatus.APPROVED"`/`"approved"` as an internal
    representation) and instead match the exact plain-language copy templates (AC5).
27. `backend/tests/modules/verification/test_admin_verification_service.py` (new) — the core of this story's
    test coverage:
    - **AC2/AC4/AC8 — atomic status+discoverability update**: approving a Freelancer's `pending` record, in one
      call, results in `verification_records.status=approved` **and** `providers.verification_status=approved`
      **and** `providers.is_discoverable=true`, read back from the database after commit — not merely asserted
      against in-memory objects.
    - **AC4 — the DB-level invariant, exercised directly**: a raw attempt to `UPDATE provider.providers SET
      is_discoverable = true WHERE verification_status != 'approved'` (bypassing the service and repository
      layers entirely) is rejected by Postgres with an `IntegrityError` from the new `CHECK` constraint —
      proving the invariant is enforced at the database, not merely by convention.
    - **AC3 — rejection never sets `is_discoverable=true`**: rejecting a record (with a valid reason) leaves
      `providers.is_discoverable=false` and sets `providers.verification_status=rejected`.
    - **AC3 — missing/empty `rejection_reason` is a 422** (schema-level; verified at the endpoint test layer,
      item 29).
    - **Decision 5's Business-approval behavior**: approving a Business Provider's record also sets
      `is_discoverable=true` (documenting the interpretive call explicitly, so it's easy to find and revisit if
      the user's confirmation in Decision 5 goes the other way).
    - **Decision 8's 409**: approving an already-`approved` or already-`rejected` record raises
      `VerificationRecordNotActionableError`.
    - **AC5/AC8 — notification trigger**: both approve and reject each create exactly one `notifications` row
      for the provider's owning `user_id`, with plain-language copy (delegates the exact-copy assertion to item
      26's more detailed test, asserts only "one row was created, for the right recipient" here).
    - **AC6 — `admin_action_log` write**: both approve and reject each create exactly one `admin_action_log` row
      with the correct `admin_user_id`/`action_type`/`target_entity_id`.
    - **Decision 9's batch enrichment**: `list_pending_for_review` returns correct Provider context for a page
      spanning multiple providers, with only one `list_by_ids` query executed (asserted via a spy/mock call
      count, not merely correct output).
28. `backend/tests/modules/verification/test_admin_verification_endpoints.py` (new) — full HTTP round trip:
    - **AC7**: unauthenticated → 401 on all four routes; a `ROLE_CUSTOMER`-only and a `ROLE_PROVIDER`-only token
      → 403 on all four routes (never 401, never 200); a `ROLE_ADMIN` token → 200/201 as appropriate.
    - **AC1**: the list endpoint returns only `pending`/`under_review` records (a separately-created `approved`
      record from a prior test is confirmed absent), paginated correctly (`page`/`page_size`/`total_items`/
      `total_pages` all correct against a known fixture set spanning more than one page).
    - **AC2/AC3**: full approve/reject HTTP flows, asserting the response body's `status` field and a follow-up
      `GET /providers/me/verification` (as the affected provider) reflecting the new status.
    - **The admin document-download route**: a `ROLE_ADMIN` caller can download a document belonging to a
      *different* user's provider (proving no ownership check applies); a non-admin caller gets 403 on the same
      route.
29. `backend/tests/scripts/test_grant_admin_role.py` (new, only if Decision 1's script is confirmed) — the
    script grants `ROLE_ADMIN` to an existing user idempotently and does not affect any other role the user
    already holds (mirrors `test_role_assignment_service.py`'s existing assertions).

---

## Mobile — Proposed Changes

**None. This story is backend-only, by deliberate design, not omission.** Grounds:

- `15_SCREEN_INVENTORY.md`'s own "Explicitly Out of Scope" section states the Admin dashboard (including Manual
  Verification Review, this story's exact flow) "is **not** included [in the MVP's 28-screen inventory]... nothing
  in the docs assigns the Admin dashboard to the mobile app... recommend treating it as a separate internal web
  tool."
- `02_ARCHITECTURE.md` frames the Flutter app as the **consumer-facing** product (Customer/Provider), with the
  website/back-office as a conceptually separate concern.
- `14_USER_FLOWS.md` Flow 6 (Admin Verification Review) describes "Admin opens the queue" generically, with no
  reference to any Flutter screen, unlike every Customer/Provider flow, which cross-references specific
  `15_SCREEN_INVENTORY.md` screen IDs throughout.
- This exactly mirrors AUTH-004's own precedent — the last time a story's every acceptance criterion was
  backend/API-side only, `tech-lead` made the identical "no mobile track" call for the identical reason (no
  screen in the inventory consumes the new capability), recorded plainly in that story's Walkthrough rather than
  silently skipped.

The provider-facing consequence of this story (a status change becoming visible on the existing S-20
Verification Status screen, VER-001) requires **zero mobile code changes** — `GET /providers/me/verification`
(VER-001, unmodified by this story) already reads `verification_records` directly and will naturally reflect
whatever status VER-002's admin action wrote, the next time the existing S-20 screen polls/loads it. No new
mobile screen, repository method, or model is needed for that to work.

---

## Explicitly Out of Scope (do not implement in this story)

- The broader admin operations dashboard (ADM-002) — Manual Match Assignment review, Unmatched Query Reports,
  feature flags/system settings UI, or any general-purpose admin-facing screen beyond verification review.
- Any admin-facing mobile or web UI of any kind (see Mobile section) — this story's every consumer is an
  API client (e.g. Postman/curl/a future internal tool), not a screen this codebase builds.
- A full email+password admin login endpoint, or any change to `AuthProvider.EMAIL_PASSWORD`'s currently-unused
  status — explicitly deferred (Decision 1); flagged as a candidate future story.
- `notification.notification_delivery` and `notification.notification_preferences` — explicitly deferred
  (Decision 3); no real WhatsApp/SMS/Email sending exists or is built by this story.
- A `POST .../start-review` (`pending → under_review`) transition endpoint (Decision 8).
- A general-purpose `GET /admin/verification/records?status=...` filter beyond the hardcoded
  pending/under_review default — no AC asks for browsing `approved`/`rejected` history through this endpoint.
- Resolving `13_OPEN_DECISIONS.md` item 5 (the actual Business Verification Bar product decision) — Decision 5
  above only decides what this story's *approval action* does given the *existing*, already-shipped config-driven
  design; it does not make the underlying, still-open product decision.
- Any change to `verification`'s existing provider-facing endpoints (`POST/GET .../documents/preview`, `POST/GET
  /providers/me/verification`, the existing owner-only document download route) beyond what Decision 6 adds
  alongside them.
- A real, malware-scanning, or otherwise hardened version of anything already flagged interim by VER-001
  (`StubDocumentOcrService`, `LocalFileStorage`) — untouched by this story.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet — fresh start, immediately following VER-001's clean closeout on this
same branch.

**Before backend implementation starts: Decision 1 (the admin-role-provisioning CLI script) needs explicit user
confirmation** — either "proceed with `grant_admin_role.py` as proposed," "use the more minimal manual-SQL-only
option instead, no new script," or a third option the user prefers. Every other decision in this Plan does not
block on this and can proceed regardless of which way Decision 1 resolves (test fixtures grant `ROLE_ADMIN`
directly, independent of how a *real* admin account gets provisioned).

1. **backend** — Migrations, the new `administration`/`notification` modules, `verification`'s new
   `admin_verification_service.py`/`admin_api.py`, the `provider` module's new write method, the new `CHECK`
   constraint, exceptions, schemas, dependencies, app wiring, and the ops script (per Decision 1's confirmation),
   plus all tests (items 1–29 above). ACs to satisfy: 1, 2, 3, 4, 5, 6, 7, 8 — this story is backend-only, so
   `backend` covers every AC. **Read Decision 4 and Decision 6 in full before starting** — the atomic update
   plus its DB-level defense-in-depth, and the new ownerless authorization shape, are the two parts of this story
   most likely to be gotten subtly wrong (e.g. forgetting the `CHECK` constraint's migration, or accidentally
   adding an `ensure_owner_or_not_found` call to an admin route where none belongs).
2. **tester** — Verify all 8 ACs individually, with particular attention to: AC4 (both halves — the
   service-layer atomicity **and** the DB constraint exercised directly via a raw, bypassing `UPDATE`, per item
   27's second bullet); AC2/AC3/Decision 5 (read the actual service code to confirm Business approval's
   `is_discoverable=true` behavior matches what Decision 5 documents, and flag clearly if the user's Decision 5
   confirmation differed from what shipped); AC5 (read the actual notification copy persisted to the database,
   not just that a row exists, to confirm no raw enum token ever appears in `title`/`body`); AC6 (confirm exactly
   one `admin_action_log` row per action, with correct `action_type`/`target_entity_id`, never zero and never
   duplicated by a retry); AC7 (the full 401/403/200 matrix on all four new routes, plus the admin
   document-download route's explicit "no ownership check" behavior — a `ROLE_ADMIN` caller genuinely can fetch
   a stranger's document, which is *correct* per Decision 6, not a bug to flag).
3. **architect** — Review Decision 6 (the new, ownerless `require_role`-only authorization shape) first and most
   carefully against ADR-015's existing framework and `06_SECURITY.md`'s authorization principles; Decision 4
   (the atomic update plus the new `CHECK` constraint) against `04_DATABASE.md`'s Transactions section and this
   codebase's existing defense-in-depth precedent; Decision 2 (new `administration` module vs. reusing `audit`)
   against `02_ARCHITECTURE.md`'s domain-boundary rules; Decision 3 (Notification domain's minimal first slice)
   against the same honesty standard ADR-018/019 were held to; Decision 7 (the new `verification → provider`
   *write* edge) against ADR-014/016's established pattern, confirming it remains one-directional and cycle-free;
   Decision 5's Business-approval interpretation, flagging explicitly if it disagrees with the reading above.
4. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved: record Decisions 1
   (admin-role provisioning), 2 (`administration` module/`admin_action_log` placement), 3 (Notification domain's
   minimal first slice), and 6 (the new ownerless authorization shape) as new ADRs (next available: **ADR-020**
   onward — tech-lead finalizes exact numbering/grouping at story close, following VER-001's own "flag now,
   number at close" practice); update `04_DATABASE.md` (new `administration`/`notification` schema sections
   confirmed built, the new `providers` `CHECK` constraint documented in that table's Constraints list); update
   `03_DOMAIN_MODEL.md` if needed (confirming the Administration/Notification domain sections now have real,
   if partial, implementations); flag `13_OPEN_DECISIONS.md`'s continued lack of CTO review again, as prior
   closeouts have.

---

## Verification Plan (mapped to the 8 ACs)

| AC | Verified by |
|---|---|
| 1 | Integration test: `GET /admin/verification/records` returns only `pending`/`under_review` records with nested documents, correctly paginated; a `ROLE_ADMIN` caller succeeds. |
| 2 | Integration test: approving a `pending` Freelancer record, read back from the database after commit, shows `verification_records.status=approved`, `reviewed_by`/`reviewed_at` populated, `providers.verification_status=approved`, `providers.is_discoverable=true` — all in one atomic call. |
| 3 | Integration test: rejecting without a `rejection_reason` is a 422 before the service layer runs; rejecting with a reason sets `status=rejected`, `providers.verification_status=rejected`, and `providers.is_discoverable` remains `false`. |
| 4 | Two independent tests: (a) the service-layer transaction never produces the forbidden combination, across both approve and reject paths and both provider subtypes; (b) a raw, bypassing `UPDATE` attempting to set `is_discoverable=true` while `verification_status != approved` is rejected by the new `CHECK` constraint at the database level. |
| 5 | Test reads the actual persisted `notifications.title`/`body` values and asserts they match the plain-language copy templates, with no raw `VerificationStatus` enum token present in either field, for both approve and reject. |
| 6 | Test asserts exactly one `admin_action_log` row is created per approve/reject action, with correct `admin_user_id`/`action_type`/`target_entity_id`, and confirms via a repeat-call/idempotency-adjacent check that a 409-rejected re-action (Decision 8) does not create a second log row. |
| 7 | Full 401/403/200 matrix, independently exercised against all four new routes: no token → 401; `ROLE_CUSTOMER`/`ROLE_PROVIDER`-only token → 403; `ROLE_ADMIN` token → 200/201. |
| 8 | Confirmed via items 27–28 above: dedicated, independently-runnable test cases for the atomic status+discoverability update (service-layer and DB-constraint halves) and for the notification trigger (row creation, recipient correctness, and exact copy). |

---

## Related Documents

- `docs/AI/02_ARCHITECTURE.md`
- `docs/AI/03_DOMAIN_MODEL.md` (Verification, Administration, Notification domains)
- `docs/AI/04_DATABASE.md` (`administration.admin_action_log`, `notification.notifications`, Verification
  Domain, Transactions section)
- `docs/AI/05_API_GUIDELINES.md` (Endpoint Organization's `/admin` namespace; Pagination)
- `docs/AI/06_SECURITY.md` (Authorization, Audit Logging, Administrative Functions)
- `docs/AI/09_DECISIONS.md` (ADR-014, ADR-015, ADR-016, ADR-018, ADR-019 — all directly extended by this story)
- `docs/AI/13_OPEN_DECISIONS.md` (item 5, referenced by Decision 5)
- `docs/AI/14_USER_FLOWS.md` (Flow 6 — Admin Verification Review; Flow 8 — Notification Triggers)
- `docs/AI/15_SCREEN_INVENTORY.md` (Explicitly Out of Scope section — Admin dashboard)
- `docs/AI/PROJECT_IMPLEMENTATION_STATE.md` (Section 17 — Next Planned Story)
- `docs/implementation/plans/Plan_S05_VER-001.md` / `docs/implementation/walkthroughs/Walkthrough_S05_VER-001.md`
  (the module/endpoint-shape/file-storage precedents this story extends)
- `docs/implementation/walkthroughs/Walkthrough_S02_AUTH-004.md` (`require_role()`/audit-logging precedent)
