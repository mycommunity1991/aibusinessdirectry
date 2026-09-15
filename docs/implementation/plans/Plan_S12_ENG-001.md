# Plan for Story ENG-001 — Receive Marketplace Notifications In My Preferred Channel

**Sprint:** 12 ("Engagement & Trust") | **Epic:** ML12-EP01 | **Milestone:** ML12 | **Priority:** High |
**Depends On:** CON-001 (done, Sprint 8), VER-002 (done, Sprint 5), REV-001 (done, Sprint 9) — all satisfied

---

## Story (verbatim, `Project_Tracker.xlsx`, `ENG-001` row — relayed via `docs/AI/SESSION_HANDOFF.md` this session)

"As a user, I want to be notified about new leads, verification status changes, and outcome-tag prompts through
my preferred channel, so that I don't have to keep checking the app manually. This story implements the
Notification domain end to end: data model, WhatsApp/SMS/Email delivery adapters behind a single interface, and
the trigger wiring for every notification-worthy event already emitted by earlier stories. Scope boundary: does
not include the deep-link/Verified-Visit features (ENG-002) — this story is notification delivery only."

## Acceptance Criteria (verbatim, 8 items)

1. `notifications`, `notification_preferences`, and `notification_delivery` tables exist via migration.
2. A single `NotificationSender` interface has WhatsApp, SMS, and Email adapters; delivery failures surface as
   typed errors, never a silent no-op.
3. Triggers are wired for: new Contact View → Provider, verification status change → Provider, manual match
   assignment created → Admin, outcome-tag prompt → Customer.
4. A disabled channel or muted category in `notification_preferences` is checked before every send and is a
   hard stop, not a soft suggestion.
5. Non-urgent events update a badge/inbox entry without forcing a push notification unless the user has opted
   in; time-sensitive events may push immediately.
6. Notifications Inbox screen groups entries as New/Earlier and deep-links each entry to its relevant context.
7. Duplicate sends are prevented via an idempotency key on retry.
8. Automated tests cover: preference-disabled blocking a send, and idempotent retry not double-sending.

**Sibling story:** Sprint 12's second story is `ENG-002` ("Share a provider profile and verify an arrival,"
depends on `CON-001`) — explicitly out of scope for this Plan.

---

## Verified Current State (read directly from code and docs before writing this Plan — do not trust the
tracker's own "end to end... for the first time" framing)

### Investigation 1 — `NotificationService` genuinely already exists, and does genuinely more than the tracker/prior-session summaries suggested

`backend/app/modules/notification/` was read in full (`models.py`, `services/notification_service.py`,
`repositories/notification_repository.py`, `dependencies.py` — no `api.py`, no `schemas.py` exist yet). Confirmed
directly:

- **One table exists today**: `notification.notifications` (shipped by `VER-002`, migration
  `04c69a216287_notification_domain.py`), with the full `CommonColumnsMixin` plus `user_id`, `type`, `title`,
  `body`, `related_entity_type`, `related_entity_id`. **No `notification_preferences` or `notification_delivery`
  table exists anywhere** — confirmed by grepping every migration in `backend/alembic/versions/` (23 files) for
  `notification_preferences`/`notification_delivery`: zero matches beyond `04_DATABASE.md`'s own spec text.
- **`NotificationService` exposes three methods today, not one**: `notify_verification_status_change` (VER-002,
  AC5), `notify_new_contact_view` (CON-001, AC7), and `notify_outcome_tag_prompt` (REV-001, AC3) — **all three
  already wired in and already called synchronously** from their respective originating modules:
  `AdminVerificationService.approve`/`reject` (`verification/services/admin_verification_service.py`),
  `ContactService.create_contact_view` (`contact/services/contact_service.py`, twice — once for the provider's
  new-lead notification, once unconditionally for the customer's outcome-tag prompt). Each method writes exactly
  one `notification.notifications` row with hardcoded, plain-language `title`/`body` copy — confirmed by
  `backend/tests/modules/notification/test_notification_service.py`'s existing, passing test suite (12 tests).
- **No multi-channel adapter, no delivery attempt, no preference check, and no idempotency key exist anywhere**
  in this code path — every one of the three existing methods does exactly one thing: insert an in-app row and
  return. `NotificationRepository` (read in full) has no custom methods beyond `BaseRepository`'s CRUD — no
  `list_for_user`, no unread-count query, nothing an Inbox screen could call today.
- **`04_DATABASE.md`'s own text (lines 890–893, unchanged since `VER-002`) already says this out loud**: *"Only
  this table exists so far; `notification_preferences` and `notification_delivery`... remain unbuilt — there is
  no real WhatsApp/SMS/Email delivery channel to have a status for, and nothing to opt in/out of yet."* This is
  the same class of "documented as not-yet-built, confirmed directly against the code" finding `ADM-001`
  (`unmatched_query_reports`) and `ADM-002` (`feature_flags`/`system_settings`) each made before their own
  planning.

**Conclusion, resolving the CTO's flagged discrepancy directly**: `ENG-001`'s "end to end... for the first time"
framing is not literally accurate — a real, already-shipped, already-wired `NotificationService` exists and does
real work (in-app notification generation for three of this story's four trigger events). This story's genuine
net-new scope is: (a) the two missing tables + a schema fix each needs beyond what was pre-documented (Decision
3 below); (b) real multi-channel delivery + preference enforcement + idempotency, layered **onto** the three
already-existing call sites via an **in-place extension of `NotificationService`'s existing three methods**,
never a second, parallel notification mechanism; (c) one genuinely new fourth trigger (manual-match-assignment →
Admin) that does not exist in any form today; (d) the Notifications Inbox screen (mobile), which has zero
precedent anywhere in this codebase (no `api.py` for this module exists yet either). See Decision 1.

### Investigation 2 — the `notification_channel` Postgres enum type already exists, in a different schema, with a real, already-wired consumer

`04_DATABASE.md`'s own pre-written `notification_preferences` spec (line 914) names a `channel` column of type
`notification_channel` — but grepping the full migration history for that literal string surfaces a real,
already-shipped consumer that has nothing to do with `notification.notifications`: `customer.customer_preferences.
notification_channel` (`customer_domain.py`, `CUS-001`, Sprint 3), a native Postgres `ENUM('whatsapp', 'sms',
'email', name='notification_channel', schema='customer')`, already editable end-to-end via `PATCH /customers/me`
(`customer/services/customer_service.py`'s `_PREFERENCES_FIELDS` frozenset includes it), defaulting to `whatsapp`
for every customer. **This is a second, genuinely real, load-bearing existing preference this Plan must not
silently ignore or duplicate** — it predates `ENG-001` by six sprints, is customer-only (no equivalent field
exists for providers/admins, since `provider`/`identity` have no analogous preferences table), and is currently
read by **zero delivery code anywhere** (nothing has ever consumed it — it has been a stored-but-inert value
since `CUS-001` shipped). See Decision 4 for how this Plan reconciles it with the new, role-agnostic
`notification.notification_preferences` table `ENG-001`'s own ACs require.

### Investigation 3 — no admin-recipient concept, no push-notification-to-admin precedent, but a real, reusable RBAC primitive exists

`docs/AI/SESSION_HANDOFF.md` Section 4 records an explicit standing rule: *"Never invent a push-notification
'notify the admin team' mechanism — no such recipient concept exists in this codebase."* AC3 literally requires a
"manual match assignment created → Admin" trigger, creating a real tension this Plan must resolve, not paper
over. Checked directly: `administration.services.manual_match_assignment_service.ManualMatchAssignmentService.
create` (read in full) creates a `status=pending`, `assigned_admin_id=NULL` row — there is no admin identity
attached at creation time (assignment is pull-based; an admin claims it later via `resolve`). However,
`identity.models`/`identity.repositories.role_repository.RoleRepository` (read in full) confirm a real,
already-seeded RBAC system exists: `identity.roles`/`identity.user_roles` join tables, `ROLE_ADMIN = "admin"`
(`app/core/constants.py`), and `RoleRepository.get_role_names_for_user(user_id)` (the forward direction, already
used by `AuthService`/`SessionService` at login/refresh). **No reverse lookup (all user ids holding a given role)
exists yet** — this is a genuine, small, one-method gap, not evidence the whole RBAC concept needs inventing from
scratch. See Decision 9 for how this Plan satisfies AC3 by broadcasting an in-app-only notification to every
`ROLE_ADMIN` account via one new reverse-lookup method, without ever inventing a push-to-admin mechanism.

### Investigation 4 — no idempotency-key precedent exists yet as a persisted column, but the INSERT-shaped atomic-conflict family (`ADR-049`) generalizes directly

`docs/AI/05_API_GUIDELINES.md`'s own "Idempotency" section (lines 367–382) only documents the general REST
convention (an `Idempotency-Key` request header, named as required for "critical POST operations" like payments)
— it has never actually been implemented anywhere in this codebase yet. `ADR-049`'s `INSERT ... ON CONFLICT DO
NOTHING ... RETURNING` pattern (`outcome_tags`' uniqueness guard, later reused by `reviews.contact_view_id`) is
the closest, directly-reusable precedent — see Decision 8 for why a **deterministic, server-computed** key (not
a caller-supplied header) is the correct shape for this story's specific retry scenario (an internal delivery
retry, not a client-facing API call).

### Investigation 5 — no "read/unread" concept exists on `notifications` today; AC6's New/Earlier grouping and AC5's "badge" both need one

`notification.notifications` (current columns, Investigation 1) has no read-state column of any kind, and
`CommonColumnsMixin`'s `is_active`/`deleted_at` are soft-delete-only — repurposing either for "read" would
conflate two unrelated concepts. This is a genuine, real schema gap this story must close to honestly satisfy
AC5's "badge" (an unread count) and AC6's "New/Earlier grouping" (which needs a boundary to group by). See
Decision 3.

### `notification` module's cross-module edges today: none. New edges this story adds are all one-directional and safe

Grepped `backend/app/modules/notification/` for any `from app.modules.<other>` import: **zero matches** — the
`notification` module currently has no outgoing cross-module edges at all (only `verification`, `contact`, and
now `administration` import *into* it). This story adds two new outgoing edges (`notification -> customer`,
Decision 4; `notification -> identity`, Decision 9) plus one new incoming edge (`administration -> notification`,
Decision 9) — none creates a cycle: `customer/dependencies.py` and `identity/dependencies.py` (both read in full)
import from `audit`/`customer`/`provider` only, never from `notification`; `administration/dependencies.py`
(read in full, post-`ADM-002`) imports from `search`/`verification` only, never from `notification`. `backend`
must re-confirm this with a real `python -c "import app.main"` sanity check per this codebase's standing
practice (`ADR-060`), but no obstacle is foreseen.

---

## Architecture Decisions

### Decision 1 — Scope: extend `NotificationService`'s three existing methods in place; do not build a second, parallel notification mechanism

Resolved above (Investigation 1). **Chosen:** `NotificationService.notify_verification_status_change`,
`.notify_new_contact_view`, and `.notify_outcome_tag_prompt` are extended **in place** (`ADR-042`-style — the
exact same "in-place upgrade of a shared write path" principle already applied twice in this codebase) to, after
creating their existing `notifications` row exactly as today, additionally run the new preference-check +
delivery-dispatch pipeline (Decisions 5–8). Their existing signatures, existing copy templates, and existing
callers (`AdminVerificationService`, `ContactService`) are **unchanged** — this story adds behavior *after* the
already-correct existing behavior, never forking a `_v2` method or duplicating the in-app-row-creation logic a
second time. A fourth, genuinely new method (`notify_manual_match_assignment_created`) is added for AC3's new
trigger (Decision 9). `NotificationService`'s constructor gains three new dependencies (`NotificationPreference
Service`, `NotificationDeliveryService`, and the identity/customer raw-repository edges those two services
themselves need — see Decisions 4/9) — a straightforward, additive constructor extension.

**Alternatives considered and rejected:**
- **Build a brand-new `NotificationDispatchService` that duplicates the three existing `notify_*` methods'
  in-app-row-creation logic**, leaving `NotificationService` untouched. Rejected — this is exactly the "silently
  duplicate a second notification mechanism alongside the old one" outcome the CTO's own framing explicitly
  warned against; it would also leave two independent code paths that could drift (e.g. a future copy-template
  change applied to only one of them).
- **Route the three existing call sites (`AdminVerificationService`, `ContactService`) directly at their own new
  delivery/preference dependencies**, bypassing `NotificationService` entirely. Rejected — `NotificationService`
  is the correct, single choke point for "what happens when a notification-worthy event occurs" (its own,
  already-established purpose); pushing delivery concerns out to every caller would duplicate the
  preference-check/dispatch logic once per caller instead of once, centrally.

### Decision 2 — Module placement: `notification_preferences`/`notification_delivery` stay inside the existing `notification` module

Both new tables share the existing `notification` Postgres schema (`04_DATABASE.md`'s own pre-written spec
already scopes them there) — per `ADR-051`'s module/schema placement rule, a new table set folds into an
existing module when it *shares* that module's schema, and only gets its own new module when it owns a
genuinely separate one. **Chosen:** both tables, their repositories, and their services live inside
`backend/app/modules/notification/`, alongside the existing `Notification`/`NotificationRepository`/
`NotificationService` — the third instance of a module holding more than one closely-related concern
(`outcome_tags`→`contact`, `ADR-048`; `feature_flags`/`system_settings`→`administration`, `ADM-002`).

### Decision 3 — Schema: two genuine additions beyond `04_DATABASE.md`'s pre-written spec, both required to honestly satisfy a literal AC

`04_DATABASE.md`'s existing `notification_preferences`/`notification_delivery` column specs (lines 909–933,
written well before this story's own ACs were finalized) are followed **exactly** except for two real,
literal-AC-driven additions:

- **`notification_preferences.channel_enabled: BOOLEAN NOT NULL DEFAULT true`** (new column, not in the
  original spec). The pre-existing spec's `channel` column is the already-shipped, 3-value
  `customer.notification_channel` enum (`whatsapp`/`sms`/`email`) — it has **no "off"/"none" value** (confirmed,
  Investigation 2), so there is no way to express AC4's literal "a disabled channel... is checked before every
  send" using `channel` alone. Adding a fourth enum value (`ALTER TYPE ... ADD VALUE`) was considered and
  rejected (see Alternatives) — a separate boolean cleanly represents "is any external channel currently
  enabled at all," independent of *which* channel is the user's standing preference (so re-enabling remembers
  the prior choice rather than losing it).
- **`notification_delivery.idempotency_key: VARCHAR(255) NOT NULL`, `UNIQUE`** (new column, not in the original
  spec). AC7 ("duplicate sends are prevented via an idempotency key on retry") is not satisfiable at all without
  a persisted key to conflict on — the original spec's column list (`notification_id`, `channel`, `status`,
  `provider_message_id`, `sent_at`, `delivered_at`, `failure_reason`) has nothing serving this purpose. See
  Decision 8 for the key's exact, deterministic shape.
- **`notifications.read_at: TIMESTAMPTZ NULL`** (new column on the already-shipped table, via `ALTER TABLE` —
  this codebase's first column-addition-to-an-existing-table migration). Required to honestly satisfy AC5's
  "badge" (an unread count needs a read/unread boundary) and AC6's "New/Earlier grouping" (same boundary).
  `NULL` = unread ("New"); a real timestamp = read ("Earlier"), set once, by `PATCH /notifications/{id}/read`
  (Decision 10).

Both `notification_preferences.channel` and `notification_delivery.channel` reuse the already-existing
`customer.notification_channel` Postgres enum type (`create_type=False`) rather than creating a duplicate
enum type in the `notification` schema — see Decision 4.

All three new/changed columns get the full `CommonColumnsMixin` treatment for the two new tables (matching
every other business table in this domain — `notifications` itself already has it), per `04_DATABASE.md`'s
"every business table gets Common Columns unless explicitly exempted" default.

**Alternatives considered and rejected:**
- **Add a 4th `"none"` value to the existing `customer.notification_channel` enum type**, reusing `channel`
  alone for the disabled state (no new boolean). Rejected — `ALTER TYPE ... ADD VALUE` cannot run inside the
  same transaction as other DDL on some Postgres versions/drivers, adding real migration-ordering risk for a
  cosmetic simplification; a separate boolean is simpler, safer, and preserves the user's channel choice across
  an enable/disable toggle (re-enabling remembers `email` instead of forcing a re-selection).
- **A caller-supplied `Idempotency-Key` HTTP header**, mirroring `05_API_GUIDELINES.md`'s general REST
  convention literally. Rejected for this specific mechanism — every trigger in this story fires from
  server-side business logic (a service method call), not a client-facing `POST` a caller could retry with a
  repeated header; a deterministic, server-computed key (Decision 8) is the correct shape for an *internal*
  retry (e.g. a future outbox/retry job), and remains available as a documented, real REST idiom for a future
  client-facing notification-sending endpoint if one is ever added.
- **A separate `notification_read_receipts` table** instead of a column on `notifications`. Rejected — massive
  overkill for a single-user, single-boolean-transition read state (no multi-device "read on device X but not Y"
  requirement exists anywhere in this story's ACs); a nullable column is this codebase's own established
  minimal-schema convention for a simple state transition.

### Decision 4 — Reuse the existing `customer.notification_channel` Postgres enum type; seed a customer's initial preference from their existing `customer_preferences.notification_channel` value

Resolved above (Investigation 2) — a genuinely real, already-editable, currently-inert customer preference
already exists for exactly this concept, just scoped narrower (customer-only) than what `ENG-001`'s
role-agnostic `notification_preferences` table needs. **Chosen:**
- `notification.notification_preferences.channel` is declared with `SqlEnum(CustomerNotificationChannel,
  name="notification_channel", schema="customer", create_type=False)` — the exact same cross-schema
  enum-type-reuse shape `customer_preferences.language` already established for `identity.language_code`
  (`CUS-001`, Decision 2, `Plan_S03_CUS-001.md`). `notification/models.py` imports the existing `NotificationChannel`
  `StrEnum` class directly from `customer.models` (a plain Python-level type import for schema-shape purposes,
  not a business-logic cross-module call — no `ADR-047` concern, mirroring `customer/models.py`'s own identical
  import of `identity.models.LanguageCode`).
- `NotificationPreferenceService.get_or_create_for_user(user_id)` (Decision 5): on first touch for a user with no
  `notification_preferences` row yet, if a `customer.customer_profiles` row already exists for that `user_id`
  (a raw, read-only `CustomerPreferencesRepository`/`CustomerProfileRepository` lookup — no side effects, never
  provisioning a new customer profile as a byproduct), seed the new row's `channel` from that customer's existing
  `customer_preferences.notification_channel` value; otherwise (a provider/admin account, or a customer somehow
  missing that row) default to `whatsapp`, matching the column's own documented server-default. This is a
  one-time seed at row-creation time only — the two preference rows are **not** kept in sync afterward (editing
  one does not push into the other); see Open Question 3.

**Alternatives considered and rejected:**
- **Create a brand-new, duplicate `notification.notification_channel` enum type.** Rejected — an unnecessary
  duplicate of an identically-shaped, already-existing type, when this codebase already has a direct precedent
  (`language_code`) for reusing one across schemas.
- **Deprecate/remove `customer_preferences.notification_channel` in favor of the new table.** Rejected as
  out-of-scope for this story — it would require a data-migration/backfill and changing `CUS-001`'s own shipped
  `PATCH /customers/me` contract, neither of which any `ENG-001` AC asks for; flagged as a genuine follow-up in
  Open Question 3/`13_OPEN_DECISIONS.md` rather than silently expanded into this Plan.

### Decision 5 — Preference enforcement is a full hard stop per category: a muted category suppresses the in-app row too, not just external delivery

AC4's literal wording ("checked before every send... a hard stop, not a soft suggestion") is read broadly here:
**Chosen:** `NotificationPreferenceService.is_category_allowed(user_id, category) -> bool` (`category` ∈
`{"leads", "verification", "outcome_prompts"}`, mapping 1:1 to `notification_preferences`' three existing
documented boolean columns) is checked **first**, before `NotificationService`'s existing in-app-row-creation
step runs at all. If `False`, the entire `notify_*` call becomes a no-op — no `notifications` row, no
`notification_delivery` row, nothing recorded. If `True`, the in-app row is always created (feeding the Inbox/
badge unconditionally), and a **separate** check, `is_channel_enabled(user_id) -> bool` (reads the new
`channel_enabled` column, Decision 3), gates only the external-delivery attempt (Decision 6/7) — a muted category
and a disabled channel are two independently-checkable hard stops, both real, neither bypassable by the other.
`get_or_create_for_user` (Decision 4) is called once per `notify_*` invocation to resolve the caller's row,
mirroring `CustomerService.get_my_profile`'s own established "lazily backfill a pre-existing account with
defaults on first touch" shape — every account created before this story ships gets default-allow, default-
`whatsapp`-or-seeded-from-`customer_preferences` values the first time any trigger fires for them, never an
error or a silently-dropped notification for having "no preferences row yet." See Open Question 1 for the
default-allow-vs-deny reasoning spelled out explicitly.

**Alternatives considered and rejected:**
- **Only gate external delivery on the category flag; always create the in-app row regardless.** Rejected —
  a real, defensible alternative reading of AC4, but the chosen behavior more literally satisfies "checked
  before every send" (a muted category really should mean "don't tell me about this at all," matching ordinary
  inbox-app UX expectations, not "still clutter my inbox, just don't push it to my phone").

### Decision 6 — Urgency (push-immediately vs. inbox-only) is a fixed, type-level property; AC5's "unless the user has opted in" clause has no concrete opt-in mechanism in this iteration's schema

**The problem:** AC5 requires "time-sensitive events may push immediately" vs. "non-urgent events update a
badge/inbox entry without forcing a push notification unless the user has opted in" — but `04_DATABASE.md`'s
own pre-written `notification_preferences` spec (and this Plan's own Decision 3 additions) provide no *fourth*
dimension distinguishing "opted in to push for an otherwise-non-urgent category" from the plain category-enabled
flag every account already defaults to `true` (Decision 5) — using the category flag itself for this would mean
every non-urgent event pushes by default for every account, which is the literal opposite of AC5's stated
default expectation.

**Chosen:** classify each of the four trigger types as a fixed, code-level constant, never a further
user-configurable preference:
- **Urgent (push immediately when category-allowed and channel-enabled):** new Contact View → Provider
  (a lead is time-sensitive — the whole point of `LEAD-001`'s existing Leads screen is fast follow-up);
  verification status change → Provider (a meaningful, infrequent, high-value event).
- **Non-urgent (in-app/badge only — never triggers `NotificationDeliveryService`, even when the category flag
  and channel are both enabled):** outcome-tag prompt → Customer (already surfaced inline, immediately, via the
  existing mobile bottom-sheet chained after Contact Reveal, `ADR-050` — a duplicate external push would be
  redundant, not helpful); manual-match-assignment → Admin (Decision 9 — bypasses external delivery entirely
  regardless of urgency).

AC5's "unless the user has opted in" clause is honestly unsatisfiable as a *distinct, user-configurable*
capability with the schema this story ships — there is no concrete affordance for a user to make that opt-in
choice today. **Recommended default (Open Question 2): ship urgency as fixed-by-type, with no per-category
"also push me for non-urgent events" toggle in this iteration** — a well-scoped, honestly-documented extension
point for a future preference field, not a silently-dropped requirement.

**Alternatives considered and rejected:**
- **Invent a fourth preference dimension** (e.g. `push_non_urgent_too: BOOLEAN`) to literally satisfy the "opted
  in" clause. Rejected for this iteration — no AC names this field, `04_DATABASE.md` never specified it, and
  inventing an unrequested preference dimension contradicts this codebase's own established discipline against
  building capability nobody asked for (`ADM-002`, Decision 3's identical reasoning for feature-flag keys).
  Flagged as Open Question 2 rather than silently decided either way.

### Decision 7 — `NotificationSender` Protocol + one stub adapter per channel; typed delivery failures are caught and recorded, never propagated to break the triggering caller's own request

Mirrors this codebase's fourth-now-fifth application of the swappable-Protocol external-integration pattern
(`FileStorage`, `DocumentOcrService`, `GooglePlacesClient`, `ConversationAiClient`, and now `NotificationSender`
— narrower in scope than `identity.SmsSender`, which is OTP-code-specific and stays untouched/unreused here, see
Alternatives). **Chosen:**
- `NotificationSender` — an `abc.ABC` with one abstract method, `async def send(self, *, recipient_user_id:
  uuid.UUID, title: str, body: str) -> str | None` (returns an optional external provider message id on success;
  raises on failure — never returns a falsy sentinel to signal failure).
- Three typed exceptions, all inheriting a common `NotificationDeliveryError(Exception)` base (a plain Python
  exception hierarchy, **not** a `BusinessException`/HTTP-mapped error — a delivery failure must never surface as
  an HTTP error response on the *triggering* request, e.g. a WhatsApp outage must never fail a Contact View
  creation call): `WhatsAppDeliveryError`, `SmsDeliveryError`, `EmailDeliveryError`.
- Three concrete stub implementations (`StubWhatsAppSender`, `StubSmsSender`, `StubEmailSender`), each logging a
  clearly-labelled "no real provider is called" message (mirroring `ConsoleSmsSender`'s exact shape/docstring
  convention) and **always succeeding** (no real vendor exists to fail against, so a stub that pretends to fail
  would itself be a fabrication) — automated tests for the "delivery failure surfaces as a typed error" half of
  AC2/AC8 use a fake/spy `NotificationSender` that deliberately raises, exactly mirroring how `AUTH-001`'s own
  OTP tests already verify `SmsSender` failure handling via a fake, never by forcing the real stub to fail.
- `NotificationDeliveryService` holds a `dict[NotificationChannel, NotificationSender]` registry (mirrors
  `identity.dependencies.get_oauth_service`'s existing `{AuthProvider.GOOGLE: ..., AuthProvider.APPLE: ...}`
  dict-of-implementations shape exactly) and dispatches to the correct sender by the recipient's `channel`
  preference.

**Alternatives considered and rejected:**
- **Reuse/extend `identity.SmsSender`** for the SMS channel instead of a new one. Rejected — `SmsSender` is
  narrowly scoped to a fixed OTP-code message shape (`send(phone_country_code, phone_number, code)`), has no
  concept of a `title`/`body`/arbitrary notification payload, and lives in `identity` for a genuinely distinct
  concern (phone-number verification, not marketplace event notification). Reusing it would either force an
  awkward, unrelated-concern coupling or require changing its signature for an unrelated caller — a new,
  purpose-built `NotificationSender` Protocol is the correct, precedented choice (a fifth application of the
  swappable-Protocol pattern, not a sixth reuse of a fourth one).
- **A single stub class implementing all three channels** instead of three separate ones. Rejected — the story's
  own literal AC2 wording ("WhatsApp, SMS, and Email adapters," plural) and this codebase's own precedent
  (`identity.get_oauth_service`'s per-provider dict of distinct implementations) both favor three small, distinct
  classes over one class silently branching on channel internally.

### Decision 8 — Idempotency key: a deterministic, server-computed natural key (`f"{notification_id}:{channel}"`), not a caller-supplied header — the fourth application of the INSERT-shaped atomic-conflict family (`ADR-049`)

**Chosen:** `NotificationDeliveryRepository.try_create(notification_id, channel, idempotency_key) ->
NotificationDelivery | None` — `postgresql.insert(...).values(...).on_conflict_do_nothing(index_elements=
["idempotency_key"]).returning(...)`, returning `None` on conflict (no `IntegrityError`/rollback dance),
mirroring `OutcomeTagRepository.try_create`/`ReviewRepository`'s identical shape exactly.
`NotificationDeliveryService.send(notification, channel)` computes `idempotency_key = f"{notification.id}:
{channel.value}"` itself (never accepts one from a caller) — this is what makes the mechanism genuinely
idempotent-on-retry (AC7/AC8) without inventing new caller-facing API surface: if `notify_new_contact_view` (or
a future retry/outbox job) is ever invoked twice for the same already-created `notifications` row and channel,
the second `try_create` call returns `None` (conflict), and `NotificationDeliveryService` short-circuits —
**it never calls `NotificationSender.send` a second time for an already-attempted `(notification_id, channel)`
pair**, regardless of whether the first attempt ultimately succeeded or failed. A genuinely new
attempt with a **different** `notification_id` (e.g. a second, independent lead notification) always gets its
own key and is never blocked by an earlier, unrelated delivery.

**Alternatives considered and rejected:**
- **A caller-supplied `Idempotency-Key` header**, per `05_API_GUIDELINES.md`'s general convention. Rejected —
  resolved above (Decision 3 Alternatives): none of this story's four triggers are client-facing `POST` calls a
  caller could retry with a repeated header; a deterministic natural key requires no new caller contract at all.
- **Retry the send if the first attempt failed** (treat `status=failed` differently from `status=sent` for
  idempotency purposes, allowing a second real attempt). Rejected for this iteration — no AC or trigger in this
  story actually re-invokes a failed send (every trigger fires exactly once, synchronously, at its originating
  event); a genuine retry/outbox mechanism (which *would* want this distinction) is unbuilt infrastructure this
  story doesn't need and isn't asked to build (mirrors `ADR-050`'s "don't invent scheduling infrastructure nobody
  asked for" principle) — AC7/AC8's "retry" is satisfied by the idempotency guarantee holding even if the exact
  same call is made twice, which is what the tests in Decision 12 below actually exercise.

### Decision 9 — The Admin trigger (AC3's fourth event) is a role-broadcast, in-app-only notification that bypasses the entire preference/delivery pipeline — resolving the tension between AC3 and the "never invent a push-to-admin mechanism" standing rule

Resolved above (Investigation 3). **Chosen:** a new `RoleRepository.get_user_ids_for_role(role_name: str) ->
list[uuid.UUID]` method (the reverse of the existing `get_role_names_for_user`, an identically-shaped `SELECT ...
JOIN user_roles ... WHERE roles.name = :role_name` query) is added to `identity`. `NotificationService.
notify_manual_match_assignment_created(assignment_id: uuid.UUID) -> list[Notification]` (new method, called by
`ManualMatchAssignmentService.create` — a new `administration -> notification` constructor edge, the same
one-directional shape already established twice, `verification -> notification`/`contact -> notification`) looks
up every current `ROLE_ADMIN` user id and creates one `notifications` row per admin (`type=
"manual_match_assignment_created"`, `related_entity_type="manual_match_assignment"`,
`related_entity_id=assignment_id`) — **and nothing else**: no preference check (no admin-specific category flag
exists, or is needed), no `NotificationDeliveryService` call, no external channel dispatch of any kind, ever.
This satisfies AC3's literal trigger requirement using this codebase's own already-existing, already-seeded RBAC
primitive (never a new, invented "admin team" recipient concept), and never contradicts the standing "no
push-to-admin" rule, because no push is ever attempted for this trigger — it is purely an in-app row, consistent
with every existing admin capability in this codebase being pull-based (`SESSION_HANDOFF.md` Section 4's
"pull-based admin queue pattern," four prior applications). It also has zero mobile-UI surface (Decision 10 —
this codebase's mobile app has no admin-facing screens at all, confirmed unchanged since `ADM-002`'s own
investigation).

**Alternatives considered and rejected:**
- **Skip AC3's admin trigger entirely**, treating it as unsatisfiable given the standing "no push-to-admin"
  rule. Rejected — the standing rule specifically targets inventing a *push* mechanism; a broadcast in-app row
  using the already-real RBAC system is a materially different, much smaller thing, and AC3's literal wording is
  satisfiable honestly without contradicting that rule.
- **A single admin-team "inbox" notification (one row, no recipient) rather than one row per admin user.**
  Rejected — `notifications.user_id` is `NOT NULL` with no "broadcast/no-owner" concept anywhere in this schema;
  one row per admin correctly lets each admin's own Inbox (if a future admin UI is ever built) show/hide/mark it
  independently, and is a direct, minimal application of the existing schema rather than a new one.

### Decision 10 — Notifications Inbox: new `notification/api.py` (first-ever for this module), role-agnostic; mobile deep-links resolve by `related_entity_type`, reusing existing screens/widgets wherever one already exists

**Backend:** three new endpoints, mounted at `/notifications`, gated only by `get_current_user` (no
`require_role` — every account, of any role, may have notifications; mirrors how `/customers/me`-shaped
endpoints impose no extra role check beyond authentication):
- `GET /notifications?page=1&page_size=20` → `CollectionResponse[NotificationResponse]`, newest first
  (`NotificationResponse`: `id`, `type`, `title`, `body`, `related_entity_type`, `related_entity_id`, `read_at`,
  `created_at` — raw fields, client groups into New/Earlier by `read_at is None`, mirroring `ADR-046`'s
  "raw fields, client-computed, never a server-computed enum" precedent, applied here to a grouping decision
  rather than a badge-precedence one).
- `GET /notifications/unread-count` → `SuccessResponse[UnreadCountResponse]` (`{"count": int}`) — a dedicated,
  `COUNT(*)`-only query (mirrors `ADM-002` Decision 4's "dedicated count-only method, never reuse a `list_*`'s
  bundled total" precedent), backing AC5's "badge."
- `PATCH /notifications/{id}/read` → `SuccessResponse[NotificationResponse]`, 404 via `ensure_owner_or_not_found`
  (`ADR-015` — an ordinary `{id}`-addressable-resource ownership check, ADR-049's negative case doesn't apply
  here since there's no multi-actor race to make atomic: only the owning user can ever mark their own row read).

**Mobile:** a new `mobile/lib/features/notifications/` module (list/detail concerns distinct enough from every
existing feature to warrant its own folder, mirroring `LEAD-001`'s own "new, standalone screen" reasoning):
Inbox screen with a `RefreshIndicator`-wrapped, sectioned list (New / Earlier headers, mirroring the New/Earlier
grouping AC6 asks for literally), each row deep-linking on tap by `related_entity_type`:
- `verification_record` → `AppRoutes.verificationStatus` (already a bare, self-contained deep link, no `extra`
  needed — existing screen already resolves the caller's own current record server-side).
- `contact_view`, recipient is a Provider (`type="new_contact_view"`) → `AppRoutes.leads` (the existing Leads
  screen already lists all of a provider's leads server-side; no per-notification "jump to this exact lead"
  screen exists or is needed).
- `contact_view`, recipient is a Customer (`type="outcome_tag_prompt"`) → re-opens the **existing**
  `OutcomeTagPromptSheet` widget directly (already built by `REV-001`, `ADR-050`, requiring only
  `contact_view_id`) as a modal, rather than navigating to a new screen — if the tag was already submitted, the
  existing `OutcomeTagAlreadyExistsError` (409) is caught and rendered as an "already recorded" state inline,
  reusing the widget's own existing error-mapping convention.
- `manual_match_assignment` (Admin recipients) → **no mobile deep link at all**; this codebase's mobile app has
  no admin-facing screens or admin sign-in concept whatsoever (confirmed unchanged since `ADM-002`), so this
  entry type is rendered read-only (title/body only, tapping only marks it read) — consistent with Decision 9's
  own "in-app-row-only, no further surface" scope for this trigger.

A new entry point tile is added to `homePlaceholder` (Decision 10, Open Question 4) — the only currently-existing
screen every authenticated account of any role lands on, unlike `storefront`/`profileSettings` which are
role-specific — showing the unread badge count from the new endpoint.

**Alternatives considered and rejected:**
- **A `require_role(ROLE_CUSTOMER, ROLE_PROVIDER, ROLE_ADMIN)` gate** (naming every role explicitly, mirroring
  `identity/api.py`'s own multi-role example) instead of plain `get_current_user`. Rejected — every account
  necessarily holds at least one of these roles already (dual-role customers/providers per `03_DOMAIN_MODEL.md`);
  naming all three explicitly adds no real restriction over plain authentication and would silently break the
  day a new role is ever added.
- **Build a dedicated "Contact View detail" screen for the outcome-tag-prompt deep link** instead of reusing the
  existing sheet widget. Rejected as unnecessary scope beyond this story's actual need — the existing widget
  already does exactly what's needed with zero new screen-building required.

---

## Backend — Proposed Changes

1. **New migration** `backend/alembic/versions/<timestamp>-<hash>_notification_preferences_and_delivery.py`
   (down_revision = `f4a8c1d9e6b3`, the current head) —
   - `ALTER TABLE notification.notifications ADD COLUMN read_at TIMESTAMPTZ NULL` (Decision 3).
   - `CREATE TABLE notification.notification_preferences` — full `CommonColumnsMixin`, `user_id` (UUID, FK →
     `identity.users.id`, `UNIQUE`), `channel` (reuses `customer.notification_channel`,
     `create_type=False`, server default `'whatsapp'`), `channel_enabled` (BOOLEAN, NOT NULL, server default
     `true`), `leads_enabled`/`verification_enabled`/`outcome_prompts_enabled` (BOOLEAN, NOT NULL, server default
     `true` each) — exactly `04_DATABASE.md`'s pre-written spec plus Decision 3's one addition.
     Constraint: `uq_notification_preferences_user_id`.
   - `CREATE TABLE notification.notification_delivery` — full `CommonColumnsMixin`, `notification_id` (UUID, FK →
     `notification.notifications.id`), `channel` (reuses `customer.notification_channel`, `create_type=False`),
     `status` (VARCHAR(20), NOT NULL — `pending`/`sent`/`failed`, no `delivered` state used yet since no real
     vendor delivery-receipt webhook exists — see Open Question 5), `provider_message_id` (VARCHAR(255), NULL),
     `sent_at`/`delivered_at` (TIMESTAMPTZ, NULL), `failure_reason` (TEXT, NULL), `idempotency_key` (VARCHAR(255),
     NOT NULL, `UNIQUE`) — `04_DATABASE.md`'s pre-written spec plus Decision 3's one addition. Constraint:
     `uq_notification_delivery_idempotency_key`. Index: `idx_notification_delivery_notification_id`.
2. **`backend/app/modules/notification/models.py`** — add `read_at: Mapped[datetime | None]` to `Notification`;
   add `NotificationPreference(CommonColumnsMixin, Base)` and `NotificationDelivery(CommonColumnsMixin, Base)`
   matching item 1 exactly; import `NotificationChannel`/build the reused enum type from
   `app.modules.customer.models` mirroring `customer/models.py`'s own `_identity_language_code_enum()` helper
   shape (name it `_customer_notification_channel_enum()` here, with a docstring naming the cross-schema reuse
   and citing `CUS-001`'s `language_code` precedent, per `ADR-047`'s naming-duty convention extended to type
   reuse).
3. **New file `backend/app/modules/notification/repositories/notification_preference_repository.py`** —
   `NotificationPreferenceRepository(BaseRepository[NotificationPreference])`: `get_by_user_id(user_id) ->
   NotificationPreference | None`; `try_create(user_id, *, channel) -> NotificationPreference | None`
   (`INSERT ... ON CONFLICT (user_id) DO NOTHING ... RETURNING`, `ADR-049`-shaped).
4. **New file `backend/app/modules/notification/repositories/notification_delivery_repository.py`** —
   `NotificationDeliveryRepository(BaseRepository[NotificationDelivery])`: `try_create(notification_id, *,
   channel, idempotency_key) -> NotificationDelivery | None` (`ADR-049`-shaped, Decision 8); `mark_sent(id, *,
   provider_message_id)`; `mark_failed(id, *, failure_reason)` (both plain `BaseRepository.update` calls — no
   race to guard against once the row is already exclusively owned by the one delivery attempt that created it).
5. **`backend/app/modules/notification/repositories/notification_repository.py`** — add `list_for_user(user_id,
   *, page, page_size) -> tuple[list[Notification], int]` (newest first); `count_unread(user_id) -> int`
   (`WHERE user_id = :user_id AND read_at IS NULL`); `mark_read(notification_id, user_id) -> Notification | None`
   (a plain, ownership-scoped `UPDATE ... WHERE id = :id AND user_id = :user_id AND read_at IS NULL RETURNING`,
   idempotent — marking an already-read row read again is a harmless no-op, returns the row either way via a
   follow-up `get_by_id`).
6. **New file `backend/app/modules/notification/services/notification_sender.py`** — `NotificationSender(ABC)`
   (Decision 7); `NotificationDeliveryError(Exception)` base + `WhatsAppDeliveryError`/`SmsDeliveryError`/
   `EmailDeliveryError`; `StubWhatsAppSender`/`StubSmsSender`/`StubEmailSender` (all always succeed, log-only,
   mirroring `ConsoleSmsSender`'s docstring convention).
7. **New file `backend/app/modules/notification/services/notification_preference_service.py`** —
   `NotificationPreferenceService(repository, customer_profile_repository, customer_preferences_repository)`:
   `get_or_create_for_user(user_id) -> NotificationPreference` (Decision 4/5); `is_category_allowed(user_id,
   category: Literal["leads", "verification", "outcome_prompts"]) -> bool`; `is_channel_enabled(user_id) ->
   bool`. The two raw `customer.*Repository` dependencies are a documented `ADR-047` exception (no
   side-effect-free `CustomerService` read primitive exists — `get_my_profile` auto-provisions, which is an
   unacceptable side effect here) — named explicitly in this file's own docstring and in
   `notification/dependencies.py`'s, per `ADR-054`'s naming-duty precedent.
8. **New file `backend/app/modules/notification/services/notification_delivery_service.py`** —
   `NotificationDeliveryService(delivery_repository, senders: dict[NotificationChannel, NotificationSender])`:
   `async def send(self, notification: Notification, *, channel: NotificationChannel) -> NotificationDelivery`
   (Decision 8) — computes the deterministic idempotency key, `try_create`s the delivery row, short-circuits on
   conflict (returns the existing row via `get_by_id`, calling no sender), otherwise calls
   `senders[channel].send(...)`, catching `NotificationDeliveryError` and calling `mark_failed` (never
   re-raising to the caller — Decision 7), or calling `mark_sent` on success.
9. **`backend/app/modules/notification/services/notification_service.py`** — extend `notify_verification_status_
   change`/`notify_new_contact_view`/`notify_outcome_tag_prompt` in place (Decision 1): each now first calls
   `preference_service.is_category_allowed(user_id, category=...)` (mapping: verification→`"verification"`,
   new_contact_view→`"leads"`, outcome_tag_prompt→`"outcome_prompts"`); if `False`, return `None` immediately
   (no row created — update each method's return type to `Notification | None` and update the three call sites
   in `AdminVerificationService`/`ContactService` accordingly, which already tolerate/ignore the return value
   today per their own existing "fire and forget" shape). If `True`, create the `notifications` row exactly as
   today, then — only for the two urgent types (Decision 6) — call `preference_service.is_channel_enabled` and,
   if `True`, `delivery_service.send(notification, channel=preferences.channel)`. Add
   `notify_manual_match_assignment_created(assignment_id) -> list[Notification]` (Decision 9). Constructor gains
   `preference_service: NotificationPreferenceService`, `delivery_service: NotificationDeliveryService`, and
   `role_repository: RoleRepository` (Decision 9's raw-repository edge, documented per `ADR-047`).
10. **`backend/app/modules/identity/repositories/role_repository.py`** — add `get_user_ids_for_role(role_name:
    str) -> list[uuid.UUID]` (Decision 9, the reverse of `get_role_names_for_user`).
11. **`backend/app/modules/administration/services/manual_match_assignment_service.py`** — `create` gains one
    new, unconditional call to `notification_service.notify_manual_match_assignment_created(assignment.id)`
    after the row is created (Decision 9, mirroring `ADR-050`'s "flagged, additive touch-point" shape exactly).
    Constructor gains `notification_service: NotificationService`.
12. **`backend/app/modules/notification/dependencies.py`** — extend with
    `get_notification_preference_repository`/`_service`, `get_notification_delivery_repository`/`_service`,
    `get_notification_sender_registry` (the `dict[NotificationChannel, NotificationSender]`, mirrors `identity.
    get_oauth_service`'s shape), and extend `get_notification_service` with the three new dependencies —
    constructing `CustomerProfileRepository(db)`/`CustomerPreferencesRepository(db)` and `RoleRepository(db)`
    **directly** (leaf-repository construction, no `customer.dependencies`/`identity.dependencies` import), with
    a docstring naming both `ADR-047` exceptions explicitly.
13. **`backend/app/modules/administration/dependencies.py`** — `get_manual_match_assignment_service` gains the
    new `notification_service` dependency, importing `notification.dependencies.get_notification_service` (a new
    `administration -> notification` edge — safe, confirmed no cycle, Investigation 5).
14. **New file `backend/app/modules/notification/schemas.py`** — `NotificationResponse`, `UnreadCountResponse`.
15. **New file `backend/app/modules/notification/api.py`** — `router = APIRouter(tags=["Notifications"])`
    (Decision 10): `GET ""` (paginated list), `GET "/unread-count"`, `PATCH "/{notification_id}/read"`. All three
    gated by plain `get_current_user` (no `require_role`).
16. **`backend/app/api/v1/api.py`** — import `notification.api.router` and register
    `v1_router.include_router(notification_router, prefix="/notifications")`.
17. **`backend/app/core/exceptions/exceptions.py`** (+ `__init__.py` export list) — add
    `NotificationNotFoundError` (404), mirroring `ContactViewNotFoundError`'s shape, for the `PATCH .../read`
    ownership check.
18. **Existing test call sites** constructing `NotificationService`, `ManualMatchAssignmentService`, or
    `AdminVerificationService`/`ContactService` directly (explicit keyword arguments) must be updated for the new
    constructor dependencies — flagged here so `backend` doesn't discover this as a surprise mid-suite-run
    (mirrors `Plan_S11_ADM-002.md` item 21's identical flag).

### Tests

19. `backend/tests/modules/notification/test_notification_preference_service.py` (new) — `get_or_create_for_user`
    seeds `whatsapp` for a provider/admin account and the customer's own existing `customer_preferences.
    notification_channel` value for a customer account with one already set to something else (e.g. `email`) —
    proving Decision 4's seeding genuinely reads the right source; returns the same row (not a second one) on a
    second call; `is_category_allowed`/`is_channel_enabled` reflect a real row's stored values and honor the
    documented `true` defaults for a freshly-created row.
20. `backend/tests/modules/notification/test_notification_delivery_service.py` (new) — a fake, deliberately
    failing `NotificationSender` proves a delivery failure is caught, recorded as `status="failed"` with a
    non-null `failure_reason`, and never re-raised past `send()` (AC2); calling `send()` twice with the same
    `notification`/`channel` creates exactly one `notification_delivery` row and calls the underlying sender
    exactly once (AC7/AC8's idempotent-retry proof — the second call's `try_create` conflicts and short-circuits
    before ever reaching the sender).
21. `backend/tests/modules/notification/test_notification_service.py` (extend the existing 12-test file) —
    **preference-disabled blocking a send** (AC8, first half): with `leads_enabled=False` for a provider,
    `notify_new_contact_view` creates **zero** `notifications` rows and never calls the sender registry (a spy
    asserts zero invocations); with `channel_enabled=False`, the `notifications` row **is** still created but no
    `notification_delivery` row is ever created and the sender is never called; the three existing methods'
    already-passing tests (exact copy-template assertions) are re-confirmed unchanged with default (allow)
    preferences, proving Decision 1's in-place extension broke nothing already shipped; `notify_outcome_tag_
    prompt`/the manual-match-assignment trigger never call the delivery service regardless of preference state
    (Decision 6's fixed-urgency classification, a genuine regression-shaped assertion, not just "not yet
    tested"). `notify_manual_match_assignment_created` creates one row per seeded `ROLE_ADMIN` account and zero
    `notification_delivery` rows (Decision 9).
22. `backend/tests/modules/identity/test_role_repository.py` (or equivalent existing file) — `get_user_ids_for_
    role` returns exactly the seeded admin account ids, excludes non-admin accounts, and returns an empty list
    for a role no account currently holds.
23. `backend/tests/modules/administration/test_manual_match_assignment_service.py` — extend `create`'s existing
    coverage: a successful creation triggers `notify_manual_match_assignment_created` exactly once with the new
    assignment's id (a spy/fake `NotificationService` or a real DB assertion of the resulting `notifications`
    rows).
24. `backend/tests/modules/notification/test_notification_api.py` (new) — full HTTP round trips: 200 `GET
    /notifications` (pagination, newest-first ordering, correct `read_at` values); 200 `GET /notifications/
    unread-count` (matches a fixture's known unread count); 200 `PATCH /notifications/{id}/read` (persists
    `read_at`, idempotent on a second call); 404 `PATCH` for another user's notification id (never a 403, `ADR-
    015`); 401 for an unauthenticated caller on all three routes.
25. Full existing backend suite re-run (not just new tests), plus `ruff check .`, plus a real `python -c "import
    app.main"` sanity check confirming no circular import was introduced (Investigation 5).

---

## Frontend — Proposed Changes

No new mobile package dependency required (reuses `dio`/Riverpod/GoRouter, already in place).

1. **New feature folder `mobile/lib/features/notifications/`**:
   - `domain/models/notification_item.dart` — mirrors `NotificationResponse` (`id`, `type`, `title`, `body`,
     `relatedEntityType` nullable, `relatedEntityId` nullable, `readAt` nullable, `createdAt`).
   - `domain/models/notification_exception.dart` — per-feature exception mapping (`network`; `unknown`) mirroring
     every other feature's identical convention.
   - `data/notification_repository.dart` — `Future<(List<NotificationItem>, PaginationMeta)> listNotifications
     ({int page = 1, int pageSize = 20})` (`GET /notifications`); `Future<int> getUnreadCount()` (`GET
     /notifications/unread-count`); `Future<void> markRead(String id)` (`PATCH /notifications/{id}/read`).
   - `state/notifications_controller.dart` (Riverpod) — owns `Status`/list state (mirrors `LeadsController`'s
     shape) plus a separate, lightweight unread-count provider (for the badge, refreshed on Inbox open/pull-to-
     refresh and after each `markRead` call).
   - `presentation/screens/notifications_inbox_screen.dart` (`NotificationsInboxScreen`) — an `AppBar` titled
     "Notifications," a `RefreshIndicator`-wrapped, sectioned `ListView` (a "New" header + rows where `readAt ==
     null`, an "Earlier" header + rows where `readAt != null` — AC6's literal grouping requirement), a loading
     spinner, a retry-able error state, and a textually distinct empty state ("No notifications yet"). Tapping a
     row calls `markRead` (moving it from New to Earlier on the next refresh) then deep-links per Decision 10's
     `relatedEntityType` mapping (`verification_record` → `context.push(AppRoutes.verificationStatus)`;
     `contact_view` + the row's own `type == "new_contact_view"` → `context.push(AppRoutes.leads)`; `contact_view`
     + `type == "outcome_tag_prompt"` → opens the existing `OutcomeTagPromptSheet` as a modal bottom sheet,
     passing `relatedEntityId` as `contactViewId`; `manual_match_assignment` → no navigation, read-only row).
2. **`mobile/lib/features/customer/presentation/screens/home_placeholder_screen.dart`** (or equivalent) — add a
   new "Notifications" entry-point tile showing the live unread-count badge (a small `Consumer` reading the
   unread-count provider), mirroring `storefront_screen.dart`'s existing `_LeadsEntryPointCard`-style
   read-from-`AppRoutes`-constant-only shape.
3. **`mobile/lib/core/routing/app_routes.dart`** — add `static const String notificationsInbox =
   '/notifications-inbox';`, documented mirroring the existing entries' doc-comment convention.
4. **`mobile/lib/core/routing/app_router.dart`** — add `GoRoute(path: AppRoutes.notificationsInbox, builder:
   (context, state) => const NotificationsInboxScreen())` — no `extra` required.
5. **`mobile/lib/l10n/app_en.arb` / `app_ar.arb`** — new keys: `notificationsInboxTitle`,
   `notificationsNewSectionHeader`, `notificationsEarlierSectionHeader`, `notificationsEmptyStateMessage`,
   `homeNotificationsEntryLabel`.

### Tests

6. `mobile/test/features/notifications/` — controller tests (loaded/error/empty, pagination, unread-count
   refresh after `markRead`); widget tests for `NotificationsInboxScreen` (New/Earlier sections render correctly
   from fixed `readAt` fixtures, empty state renders and is pull-to-refresh-able, each `relatedEntityType`
   variant navigates/opens the correct target on tap — four cases, including the no-navigation admin-type case).
7. `mobile/test/features/customer/` (or equivalent) — extend the home-placeholder screen's existing test to
   assert the new Notifications entry tile is present, navigates to `AppRoutes.notificationsInbox`, and renders
   a live badge count from a fixture.
8. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **Real WhatsApp/SMS/Email vendor integration** — `StubWhatsAppSender`/`StubSmsSender`/`StubEmailSender` are the
  only implementations shipped, mirroring every other swappable-Protocol precedent in this codebase
  (`FileStorage`/`DocumentOcrService`/`GooglePlacesClient`/`ConversationAiClient`, and `identity.SmsSender`
  itself). A new `13_OPEN_DECISIONS.md` item is added at closeout tracking this real-vendor gap (Open Question 5
  notes there isn't already one covering it — `13_OPEN_DECISIONS.md` item 11 covers OCR, item 13 covers the LLM
  vendor; neither covers notification delivery).
- **The deep-link/Verified-Visit features** — `ENG-002`'s own explicitly named scope boundary.
- **A retry/outbox job that re-attempts a previously-failed delivery.** No trigger in this story re-invokes a
  failed send; Decision 8 explicitly defers a genuine retry mechanism as unbuilt infrastructure nobody asked for
  yet (mirrors `ADR-050`).
- **A user-configurable "opt in to push for non-urgent events" preference.** Decision 6/Open Question 2 —
  urgency is fixed by type in this iteration.
- **Deprecating or migrating `customer.customer_preferences.notification_channel`.** Decision 4's Alternatives —
  a real, flagged follow-up, not built here.
- **Any admin-facing UI of any kind** for the manual-match-assignment notification — Decision 9/10; this
  codebase's mobile app has no admin surface anywhere, unchanged by this story.
- **Delivery receipts / webhooks from a real vendor** (the `delivered`/`delivered_at` half of `notification_
  delivery`'s documented shape) — columns exist per the pre-written spec, but nothing ever sets them in this
  story (no real vendor to receive a webhook from); `status` only ever reaches `pending`→`sent`/`failed` here.
- **Push-notification OS-level plumbing** (APNs/FCM device tokens, background notification handling). This
  story's mobile scope is the in-app Inbox screen and its badge only — no `pubspec.yaml` push-messaging
  dependency is added (confirmed none exists today).
- **Any customer-facing "manage my notification preferences" settings screen.** No AC requires end users to be
  able to edit `channel`/`channel_enabled`/the three category flags via the app in this story — only the backend
  data model, defaults, and enforcement logic are required. Flagged as a natural, obvious follow-up (Open
  Question 6), not built here.

---

## Open Questions (flagged for CTO awareness — do not block `backend`/`frontend` from starting; per standing
instruction, resolved with this Plan's own stated recommendation if not addressed before implementation)

1. **Default-allow vs. default-deny for a pre-existing account's first-touch preferences (Decision 5).**
   **Recommended default: default-allow** (`channel_enabled=true`, all three category flags `true`, `channel=
   whatsapp` or seeded from `customer_preferences` for a customer) — matches `04_DATABASE.md`'s own pre-written
   column-level defaults exactly, and preserves every existing user's current experience (they already receive
   in-app notifications today with no preference gate at all; flipping to default-deny would silently break
   `VER-002`/`CON-001`/`REV-001`'s already-shipped, already-relied-upon notification behavior for every account
   that hasn't explicitly opted out of anything).
2. **AC5's "unless the user has opted in" clause has no concrete schema affordance in this iteration (Decision
   6).** **Recommended default: ship urgency as a fixed, type-level classification**, with no new preference
   dimension — a well-scoped, explicitly-documented gap for a future story to close if the product later wants
   granular non-urgent-push opt-in, rather than inventing an unrequested field now.
3. **Should `customer.customer_preferences.notification_channel` be deprecated in favor of the new, broader
   `notification.notification_preferences.channel` (Decision 4)?** **Recommended default: keep both, seed-once
   at creation time only** — deprecation/migration is a real, separate follow-up with its own blast radius
   (touching `CUS-001`'s shipped `PATCH /customers/me` contract), flagged as a new `13_OPEN_DECISIONS.md` item
   rather than folded into this already-large story.
4. **Where the Inbox's entry point/badge lives in the mobile app, given no real Home/Activity/Profile tab shell
   exists yet (`CUS-001`, Decision 7 in that Plan already flagged this as still-open).** **Recommended default:
   a tile on `homePlaceholder`** (the only screen every authenticated account of any role currently lands on) —
   consistent with how every other post-`CUS-001` feature (Leads, Visibility Analytics, Verification) has added
   its own ad hoc entry-point tile to an existing screen rather than waiting for a real navigation shell to be
   built first.
5. **`notification_delivery.status`'s `delivered`/`delivered_at` fields are pre-specified but genuinely unused by
   this story (no real vendor webhook exists to set them).** **Recommended default: create the columns exactly
   per `04_DATABASE.md`'s pre-written spec (so a future real-vendor integration needs no further migration), but
   leave them permanently `NULL`/unset in this story's own code** — flagged as a new `13_OPEN_DECISIONS.md` item
   (no existing item covers real notification-vendor selection; items 11/13 cover OCR/LLM only) at closeout.
6. **No customer/provider-facing settings screen to edit their own notification preferences exists in this
   story.** **Recommended default: out of scope here** (no AC requires it) — flagged as an obvious, real follow-
   up story for a future sprint, not silently built as unrequested scope now.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story (fresh start — Sprint 12's first story, first work of Milestone ML12).

1. **backend** — Backend Proposed Changes items 1–18, Tests items 19–25. Suggested build order: (a) migration +
   model changes (items 1–2) first, including the `read_at` `ALTER TABLE` and the cross-schema enum reuse — get
   this reviewed/confirmed applying cleanly before anything else depends on it; (b)
   `NotificationPreferenceRepository`/`Service` and the new `identity.RoleRepository.get_user_ids_for_role`
   method (items 3, 7, 10) with tests 19, 22; (c) `NotificationSender`/`NotificationDeliveryRepository`/`Service`
   (items 4, 6, 8) with test 20, including the fake-failing-sender test proving AC2's typed-error requirement;
   (d) extend `NotificationService`'s three existing methods in place plus the new fourth method (items 5, 9, 11)
   with test 21 and 23 — read Decision 1/5/6/9 in full before touching this file, since getting the in-place
   extension genuinely right (not breaking the 12 already-passing tests) is this story's most architecturally
   sensitive step; (e) wiring (items 12–13) with a real import-cycle sanity check; (f) the new `api.py`/
   `schemas.py`/exception (items 14–17) with test 24; (g) item 18's existing-test-call-site sweep and the full
   regression run (test 25) at the very end.
2. **frontend** — Frontend Proposed Changes items 1–5, Tests items 6–8, only once `backend`'s endpoints
   (item 15) are merged/available. Reuse the existing `OutcomeTagPromptSheet` widget as-is (Decision 10) rather
   than building a new one.
3. **tester** — verify all 8 verbatim ACs with real evidence (real DB, real HTTP round trips):
   - **AC1**: migration applies cleanly; all three tables' columns/constraints match this Plan's spec (including
     the two genuine additions beyond `04_DATABASE.md`'s original text, Decision 3) exactly.
   - **AC2**: a fake, deliberately-failing `NotificationSender` produces a typed `NotificationDeliveryError`
     that is caught and recorded (`status="failed"`, non-null `failure_reason`) — never a silent no-op, and
     never propagated to fail the triggering request.
   - **AC3**: all four triggers fire correctly end-to-end — a real Contact View creation produces a provider
     notification; a real verification approve/reject produces a provider notification; a real manual-match-
     assignment creation produces one notification per seeded admin account; a real Contact View creation also
     produces the customer's outcome-tag-prompt notification (regression-confirming the already-shipped
     `REV-001` behavior still works after Decision 1's in-place extension).
   - **AC4**: a muted category genuinely blocks the *entire* send (zero `notifications` row, zero
     `notification_delivery` row, zero sender calls); a disabled channel blocks only the external-delivery half
     (the in-app row still exists) — two independently-verified hard stops, not one representative sample.
   - **AC5**: the two urgent-type triggers call `NotificationDeliveryService`/the sender when channel-enabled;
     the two non-urgent-type triggers (outcome-tag-prompt, manual-match-assignment) never do, regardless of
     preference state — a genuine behavioral assertion, not just "not yet tested."
   - **AC6**: `GET /notifications` returns correct `read_at` values distinguishing New/Earlier; `PATCH .../read`
     genuinely transitions a row; the mobile Inbox screen groups correctly and each `relatedEntityType` deep-
     links to its real, working target (or correctly does nothing for the admin-type case).
   - **AC7**: calling the same trigger twice for the same underlying event never creates a second
     `notification_delivery` row and never calls the sender a second time (test 20's exact scenario, re-verified
     independently).
   - **AC8**: tests 21 (preference-disabled blocking) and 20 (idempotent retry) both exist, pass, and genuinely
     exercise the scenario their name claims (not just "assert 200").
4. **architect** — review: Decision 1's in-place extension of `NotificationService` for genuine "prove the
   untouched parts really didn't change" rigor (`ADR-042` standard) against the 12 already-passing pre-existing
   tests; Decision 4's cross-schema enum-type reuse and the `notification -> customer` raw-repository edge for
   correct `ADR-047` docstring-naming; Decision 8's idempotency-key mechanism for genuine race-safety (confirm
   the `try_create`-then-conditionally-call-sender sequence has no window where two concurrent callers could both
   observe "no existing row" and both call the sender — i.e. confirm the atomic INSERT, not a read-then-write, is
   what actually gates the sender call); Decision 9's `administration -> notification` new edge and the
   `identity.RoleRepository` reverse-lookup for correct `ADR-047`/`ADR-060`-style docstring-naming and no
   circular import; confirm `05_API_GUIDELINES.md`'s pagination rule on `GET /notifications`; confirm the new
   `PATCH .../read` endpoint correctly returns 404 (never 403) per `ADR-015`.
5. Once `tester` and `architect` both report clean, **the orchestrator pauses and presents both verdicts plus a
   summary of the diff to the user for explicit sign-off** before writing the Walkthrough or touching the
   changelog/tracker — no standing "proceed straight through" instruction has been given for this story (unlike
   several Sprint 11 stories). A failed or "sent back" verdict from either loops back to `backend`/`frontend`
   automatically first, as always.
6. At closeout (after sign-off): record Decisions 1, 3, 4, 5, 6, 7, 8, 9, 10 as new ADRs (next available:
   **ADR-064** onward); update `04_DATABASE.md`'s Notification Domain section to mark `notification_preferences`/
   `notification_delivery` as shipped (including the two genuine spec additions, Decision 3) and document the new
   `notifications.read_at` column; add the new `13_OPEN_DECISIONS.md` items from Open Questions 3/5/6; update
   `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 12 section; update `docs/AI/SESSION_HANDOFF.md` with the new state.

---

## Verification Plan (mapped to the 8 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | Migration applies cleanly; all three tables' columns/constraints confirmed directly (test 24's round trips exercise all three in practice). |
| 2 | `test_notification_delivery_service.py`'s fake-failing-sender assertion (test 20). |
| 3 | `test_notification_service.py`'s four-trigger coverage (test 21) plus `test_manual_match_assignment_service.py`'s extended coverage (test 23). |
| 4 | `test_notification_service.py`'s muted-category (zero rows) and disabled-channel (in-app row only) assertions (test 21). |
| 5 | `test_notification_service.py`'s urgent-vs-non-urgent behavioral assertions (test 21). |
| 6 | `test_notification_api.py`'s `GET`/`PATCH` round trips (test 24) plus the mobile Inbox screen's widget tests (Frontend test 6). |
| 7 | `test_notification_delivery_service.py`'s double-send-same-key assertion (test 20). |
| 8 | Tests 20 and 21 both exist and pass, genuinely exercising each named scenario. |

---

## Related Documents

- `docs/AI/04_DATABASE.md` (Notification Domain — the pre-existing `notification_preferences`/
  `notification_delivery` spec this Plan follows, plus Decision 3's two genuine additions to update at closeout;
  Customer Domain — `customer_preferences.notification_channel`'s pre-existing shape reused/seeded from,
  Decision 4)
- `docs/AI/09_DECISIONS.md` (`ADR-015` — 404-not-403 for `{id}`-addressable ownership checks, `PATCH .../read`;
  `ADR-042` — in-place upgrade of a shared write path, Decision 1's governing precedent; `ADR-046` — raw fields/
  client-computed grouping, Decision 10; `ADR-047`/`ADR-054` — Services-only rule and its raw-Repository
  exception naming duty, applied three times in this Plan; `ADR-048`/`ADR-051` — module-vs-schema placement,
  Decision 2; `ADR-049` — INSERT-shaped atomic conflict pattern, Decision 8's fourth application; `ADR-050` —
  synchronous best-effort notification firing and "don't invent scheduling infrastructure," Decisions 6/7/8;
  `ADR-060` — circular-import-avoidance, the same discipline applied to Decision 9's new edges)
- `docs/AI/SESSION_HANDOFF.md` Section 4 (the full precedent list this Plan cites throughout — pull-based admin
  queue pattern and its "never invent a push-to-admin mechanism" rule, Decision 9; swappable-Protocol pattern,
  Decision 7)
- `docs/AI/13_OPEN_DECISIONS.md` (items 11/13 — the existing real-vendor-gap items this story's own new gap,
  Open Question 5, is modeled after but distinct from)
- `docs/implementation/plans/Plan_S03_CUS-001.md` (Decision 2 — the original `customer_preferences.language`/
  `identity.language_code` cross-schema enum-reuse precedent Decision 4 mirrors exactly; Decision 4 — the
  get-or-create-with-lazy-backfill shape Decision 5 mirrors)
- `docs/implementation/plans/Plan_S05_VER-002.md` (Decision 3 — the original "notification_preferences/
  notification_delivery remain unbuilt, no real channel yet" reasoning this story now resolves)
- `docs/implementation/plans/Plan_S08_CON-001.md`, `Plan_S09_REV-001.md` (the two already-shipped `notify_*`
  call sites this Plan extends in place, Decision 1)
- `docs/implementation/plans/Plan_S10_LEAD-001.md` (the mobile "new, standalone feature folder" precedent
  Frontend item 1 mirrors)
- `docs/implementation/plans/Plan_S11_ADM-001.md`, `Plan_S11_ADM-002.md` (the pull-based admin-queue pattern and
  circular-import-avoidance precedents Decision 9 directly reuses)
- `docs/AI/05_API_GUIDELINES.md` (Pagination section, applied to `GET /notifications`; Idempotency section, the
  general convention Decision 8 explicitly diverges from for a documented, real reason)

---

**End of Document**
