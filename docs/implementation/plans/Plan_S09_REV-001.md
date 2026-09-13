# Plan for Story REV-001 — Tell the Platform Whether I Hired a Provider

**Sprint:** 09 (Outcome & Reviews) | **Epic:** ML9-EP01 | **Milestone:** ML9 | **Phase:** PH2 | **Priority:**
High | **Depends On:** CON-001 (done, Sprint 8)

---

## Story (verbatim, `Project_Tracker.xlsx`, `REV-001` row — relayed by the orchestrator this session)

"As a customer who contacted a provider, I want to quickly confirm whether I hired them, so that the platform has
a real signal of what actually happened without tracking payment details it has no visibility into. The Outcome
Tag is the platform's only conversion signal given the offline-payment reality of the direct-contact model. It is
deliberately minimal — a yes/no tied to a specific Contact View — and only the Customer who generated that Contact
View may submit it. Scope boundary: does not include the review itself (REV-002), which requires a 'Yes' outcome
tag as its anchor."

## Acceptance Criteria (verbatim, 6 items)

1. `outcome_tags` table exists via migration, with a unique constraint on `contact_view_id` (one outcome tag per
   Contact View).
2. Only the Customer who owns the underlying Contact View can submit an outcome tag for it — attempting to submit
   for someone else's Contact View is rejected.
3. The prompt ("Did you hire them?") is triggered after a Contact View, via a notification, and is dismissible
   ("Maybe later") without penalty.
4. The outcome tag does not attempt to capture payment amount, job completion detail, or scheduling.
5. A "No" or absent outcome tag is still retained as a signal (not discarded) — it is not required to be "Yes" for
   the tag itself to exist, only for a Review to follow.
6. Automated tests cover the ownership restriction and the uniqueness-per-Contact-View constraint.

---

## Verified Current State (read directly from code and docs before writing this Plan)

- **`outcome_tags` is already fully spec'd in `04_DATABASE.md`** (Contact Domain section, same `contact` Postgres
  schema `contact_views` lives in — confirmed by the section heading `# Contact Domain (\`contact\` schema)`
  covering both `contact_views` and `outcome_tags`): `contact_view_id` (UUID, not null, FK → `contact_views.id`,
  unique — 1:1), `hired` (BOOLEAN, not null — "Did you hire them?"), `submitted_at` (TIMESTAMPTZ, not null,
  default `now()`). Constraint: `uq_outcome_tags_contact_view_id`. Service-layer rule (already stated in the spec
  itself): "only the Customer who owns the parent Contact View may submit this row." No deviation from this
  three-column spec is needed — this story builds it exactly as documented.
- **`contact_views` (CON-001) is fully shipped** — `ContactViewRepository` (`backend/app/modules/contact/
  repositories/contact_view_repository.py`) is a thin `BaseRepository[ContactView]` subclass with no custom
  methods, so `get_by_id` is already available for free (inherited from `BaseRepository.get_by_id`, a plain
  `session.get(model, id)`). `ContactService.create_contact_view` (`backend/app/modules/contact/services/
  contact_service.py`) is the one existing writer; read in full — its self-dealing guard, its `customer_profile`
  resolution via `CustomerProfileRepository.get_by_user_id(current_user_id)`, and its `notify_new_contact_view`
  call are all directly relevant precedent for this story's own service and the one small addition this story
  makes to it (Decision 5).
- **The `administration` module's own precedent settles where `outcome_tags` should live.**
  `backend/app/modules/administration/models.py` holds three separate aggregate roots — `AdminActionLog`
  (VER-002), `ClaimReviewRequest` (CLM-001), `ManualMatchAssignment` (AI-002) — all in the same `administration`
  Postgres schema, added incrementally by three different stories to the *same* Python module, never split into
  three separate modules. `outcome_tags` is the exact same shape of situation: it lives in the same `contact`
  Postgres schema `contact_views` already occupies, and CON-001's own Plan already named it as `contact_views`'s
  anchored child ("the future `outcome_tags`/`visit_verifications`/`reviews` domains all anchor to it... giving it
  its own module now avoids a later, disruptive extraction once those stories arrive"). This story extends the
  existing `backend/app/modules/contact/` module in place — new model class, new repository, new service, new
  schemas, new route in the existing `contact/api.py` — rather than creating a new standalone module.
- **AC2's ownership check is the same shape CON-001's `search_request_id` ownership validation (Decision 4)
  already solved**, itself built on ADR-015's "always 404, never 403, for another user's resource" convention
  (`ensure_owner_or_not_found`, `backend/app/core/authorization.py`). This is a **different** shape from CON-001's
  self-dealing guard (403, `SelfDealingContactError`) — self-dealing is a permanent, identity-based block (ADR-044:
  "this specific caller may never create this specific write, regardless of retry timing"), whereas AC2 is
  ordinary resource-ownership over an addressable `contact_view_id` the caller supplies, which this codebase
  always resolves as a non-revealing 404, never a 403. `ensure_owner_or_not_found(contact_view.customer_id if
  contact_view is not None else None, customer_profile.id, not_found_exc=ContactViewNotFoundError())` reuses the
  identical helper CON-001 already uses for `search_request_id`, applied to a new resource.
- **No existing atomic-conditional-write precedent covers an INSERT-shaped uniqueness race** — the three named
  precedents (`try_claim_for_account`, `try_claim_for_review`, `try_resolve`) are all UPDATE-shaped
  (`UPDATE ... WHERE id = :id AND status = 'pending'`, checking `rowcount == 1`). AC1's uniqueness constraint is a
  genuine INSERT-time race (two concurrent submissions for the same `contact_view_id`), which an UPDATE-shaped
  guard doesn't fit. This codebase already has a real, precedented mechanism for exactly this shape:
  `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing(index_elements=[...])`, used today in
  `backend/app/modules/identity/services/seed_data.py` (`seed_roles`) and the `category_domain` migration's own
  seed step — both for idempotent *seeding*, not user-facing conflict rejection, but the underlying SQL mechanism
  (a single atomic statement, no read-then-write gap) is identical to what AC1/AC6 need here. This is the fourth
  application of the "never a read-then-write check" family, and the first INSERT-shaped one (Decision 3).
- **No scheduling/background-job infrastructure exists anywhere in this codebase** — confirmed by a direct search
  (no Celery, no APScheduler, no cron reference in `02_ARCHITECTURE.md` or anywhere in `backend/app`). `14_USER_
  FLOWS.md` Flow 4 step 13's "some time after the Contact View, the app prompts the Customer" is narrative scene-
  setting, not a literal delay requirement — AC3's own verbatim text only requires the prompt be "triggered after
  a Contact View, via a notification," which an immediate, synchronous emission genuinely satisfies (Decision 5).
- **No customer-facing Notifications Inbox (S-13) or any `notification` module `GET` endpoint exists anywhere in
  this codebase** — confirmed directly: `backend/app/modules/notification/` has `models.py`, `repositories/`,
  `services/notification_service.py`, and `dependencies.py`, but **no `api.py`** at all. A repo-wide search for
  "Notifications Inbox"/`NotificationsScreen`/a notification bell also found nothing on mobile. This is the exact
  same gap CON-001's own AC7 already named and worked around ("wired fully in ENG-001, but the event itself must
  be emitted here") — this story inherits that same scope trim for the *notification delivery* half of AC3
  (Decision 6), while still building a real, working, testable prompt UI for the *other* half of AC3 (the sheet
  itself must exist and be dismissible — that part is unambiguously this story's own scope, not deferred).
- **`NotificationService`** (`backend/app/modules/notification/services/notification_service.py`) has exactly one
  existing writer method to mirror for the new one: `notify_new_contact_view(*, user_id, contact_view_id)` —
  hardcoded plain-language `title`/`body`, `type="new_contact_view"`, `related_entity_type="contact_view"`,
  `related_entity_id=contact_view_id`. `04_DATABASE.md`'s own `notifications.type` column documentation already
  lists `outcome_tag_prompt` as one of its example values (`"new_lead | verification_status_change |
  outcome_tag_prompt | others"`) — confirming the exact `type` string this story's new method should use was
  already decided, not invented here.
- **The mobile Contact flow (CON-001) is fully built and directly extensible.** `ProviderProfileScreen.
  _onContactTap` (`mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart`) calls
  `ContactRevealSheet.show(context, args)` and currently discards the returned `Future<void>`. `ContactRevealSheet.
  show` uses `showModalBottomSheet<void>`, which already resolves exactly when the sheet is dismissed (by any
  means — Yes/No action, swipe-down, tap-outside). `ContactRevealController`'s state (`contactRevealControllerProvider
  (args)`) holds the just-created `ContactReveal` (with `.id` = the new `contact_view_id`, `.providerDisplayName`)
  after a successful reveal — directly readable via `ref.read(...)` once the sheet closes, with no new plumbing
  needed to carry the id forward. `ProviderProfile.primaryPhotoUrl` (already loaded by `provider_profile_controller
  Provider`) supplies the "provider photo" half of the new sheet's content.
- **`15_SCREEN_INVENTORY.md` already specs the exact sheet needed**: `*(sheet)* Outcome Tag Prompt | Capture "Did
  you hire them?" | Provider name/photo, Yes/No | Yes / No`. AC3's own verbatim text adds one element the
  inventory's compressed table doesn't spell out: a third, non-committal "Maybe later" dismiss action — a literal
  AC requirement, not a deviation from the inventory (the inventory's "Primary Action" column names only the
  two committal actions; a dismiss/close affordance is implicit on every modal sheet in this codebase's own
  convention, e.g. tap-outside already closes `ContactRevealSheet` without any current explicit close button).
- **No `visit_verifications` or `reviews`/`provider_rating_summaries` work is in scope.** Both remain fully
  unbuilt, confirmed unaffected by this story; `13_OPEN_DECISIONS.md` item 14 (whether `provider_rating_summaries`
  is still needed) is explicitly `REV-002`'s decision to make, not this story's, per `docs/AI/SESSION_HANDOFF.md`'s
  own framing of the two stories' split.
- Current Alembic migration head: `024bcc0fbaf8` (`contact_domain`, CON-001). This story adds the first migration
  since then, on top of it — no new Postgres schema needed (`contact` already exists).

---

## Architecture Decisions

### Decision 1 — `outcome_tags` is added to the existing `contact` module, not a new standalone module

**The problem:** where should the new `OutcomeTag` model/repository/service/schemas/route live?

**Chosen:** extend `backend/app/modules/contact/` in place: a new `OutcomeTag` class in the existing `models.py`
(alongside `ContactView`), a new `repositories/outcome_tag_repository.py`, a new `services/outcome_tag_service.py`,
new request/response schemas added to the existing `schemas.py`, and a new route added to the existing `api.py`'s
router (same `/contact-views` prefix, same `["Contact"]` tag). This mirrors the `administration` module's own
established precedent exactly: `AdminActionLog`/`ClaimReviewRequest`/`ManualMatchAssignment` are three separate
aggregate roots, shipped by three different stories, all living in one Postgres schema and one Python module.

**Alternatives considered and rejected:**
- **A new standalone `outcome` module.** Rejected — `outcome_tags` shares `contact_views`' own Postgres schema
  (`04_DATABASE.md`'s `# Contact Domain (\`contact\` schema)` heading covers both), and a new `OutcomeTagService`
  would need `ContactViewRepository` as a cross-module dependency anyway (to resolve the parent Contact View for
  the ownership check) — an avoidable new cross-module edge for no isolation benefit, when the `administration`
  module's own precedent already establishes that "one Postgres schema, several aggregate roots, one Python
  module, built incrementally" is this codebase's chosen pattern for exactly this situation.

### Decision 2 — AC2's ownership rejection is a 404 (`ContactViewNotFoundError`), reusing `ensure_owner_or_not_found`, never a 403

**The problem:** AC2 says "attempting to submit for someone else's Contact View is rejected" without specifying a
status code; a wrong shape here previously bit no one, but this codebase has two genuinely different existing
shapes for "the caller shouldn't get this" (a permanent identity-based 403, or a non-revealing 404), and picking
the right one for this instance is a real question, not a formality.

**Chosen:** `ContactViewNotFoundError` (404), raised via `ensure_owner_or_not_found(contact_view.customer_id if
contact_view is not None else None, customer_profile.id, not_found_exc=ContactViewNotFoundError())` — the exact
same helper and non-revealing-404 posture CON-001's Decision 4 already uses for `search_request_id` ownership.
This collapses "doesn't exist" and "exists but belongs to someone else" into one response, mirroring ADR-015.

**Alternatives considered and rejected:**
- **A 403, mirroring CON-001's `SelfDealingContactError`.** Rejected — ADR-044's own reasoning for choosing 403
  over 409 there was specifically that self-dealing is a *permanent, identity-based* authorization rule with no
  race/retry window. AC2's ownership check is the opposite shape: an ordinary `{id}`-addressable-resource
  ownership check (ADR-015's own named category), which this codebase always resolves as a non-revealing 404 —
  using 403 here would be an inconsistent, unprecedented departure for the same shape of problem CON-001 (Decision
  4) already solved correctly.

### Decision 3 — Uniqueness-per-Contact-View enforced via atomic `INSERT ... ON CONFLICT DO NOTHING ... RETURNING`, never a pre-check-then-insert

**The problem:** AC1/AC6 require the "one outcome tag per Contact View" constraint to be genuinely race-safe, not
just documented — two concurrent submission attempts for the same `contact_view_id` (e.g., a double-tap) must
never both succeed, and this codebase's own established principle explicitly rules out a read-then-write check for
exactly this kind of race.

**Chosen:** `OutcomeTagRepository.try_create(values: dict) -> OutcomeTag | None` builds a single atomic statement:
`postgresql.insert(OutcomeTag).values(**values).on_conflict_do_nothing(index_elements=["contact_view_id"])
.returning(OutcomeTag.id)`, executed once. If `RETURNING` yields no row (the conflict path), the method returns
`None` and `OutcomeTagService.submit_outcome_tag` raises a new `OutcomeTagAlreadyExistsError` (409 — a genuine
timing conflict, mirroring `ClaimAlreadyClaimedError`'s existing 409 shape, not the self-dealing guard's 403
shape). If a row *is* returned, the method fetches and returns the full `OutcomeTag` via the already-inherited
`get_by_id`. This extends the existing "atomic conditional write, never read-then-write" family
(`try_claim_for_account`/`try_claim_for_review`/`try_resolve`) with its first INSERT-shaped member, reusing the
exact `on_conflict_do_nothing` mechanism already proven in this codebase (`seed_roles`, the `category_domain`
migration's seed step) — applied here to reject a genuine conflict instead of silently no-opping a duplicate seed.

**Alternatives considered and rejected:**
- **`SELECT` for an existing row, then `INSERT` if none found.** Rejected outright — this is precisely the
  read-then-write race shape this codebase's own established principle (`docs/AI/SESSION_HANDOFF.md` §4) already
  forbids for exactly this reason: two concurrent requests can both pass the `SELECT` check before either
  `INSERT` commits.
  - **A plain `INSERT`, catching the resulting `IntegrityError` from the DB's own unique constraint.** Considered
    as functionally equivalent in outcome, but rejected in favor of `ON CONFLICT DO NOTHING` — catching an
    `IntegrityError` mid-request requires an explicit `session.rollback()` before the request-scoped session can
    be used for anything else (a heavier, more disruptive recovery step than a single statement that never raises
    in the conflict case at all), and this codebase already has a proven, non-exception-driven mechanism for
    exactly this "insert, but tolerate an existing conflicting row" shape.

### Decision 4 — An outcome tag is immutable once submitted; no update/resubmission path is exposed

**The problem:** should a customer be able to change a previously-submitted "Yes"/"No" answer?

**Chosen:** no. `OutcomeTagService` exposes only `submit_outcome_tag` (a single create); a second attempt against
the same `contact_view_id` is rejected with `OutcomeTagAlreadyExistsError` (Decision 3), never silently updated.
No AC asks for an edit/resubmit affordance, and an Outcome Tag is meant to be an honest, point-in-time signal —
allowing revision after the fact would need product rules this story was never asked to design (e.g., can it be
changed after a Review already exists against it once REV-002 ships?), for no requested benefit.

**Alternatives considered and rejected:**
- **Allow resubmission to overwrite the previous `hired` value.** Rejected — unrequested scope, and would
  complicate `REV-002`'s future anchor-verification read (which reads `outcome_tags.hired` at Review-submission
  time) with a mutability question that has no product answer yet.

### Decision 5 — Customer-facing prompt notification is a new `NotificationService.notify_outcome_tag_prompt`, fired synchronously and unconditionally from `ContactService.create_contact_view` — a flagged, additive touch-point on CON-001's already-shipped code

**The problem:** AC3 requires the prompt to be "triggered after a Contact View, via a notification." No such
notification exists today; CON-001's `ContactService.create_contact_view` only ever notifies the *provider*
(`notify_new_contact_view`), never the customer.

**Chosen:** add `NotificationService.notify_outcome_tag_prompt(*, user_id, contact_view_id)` — same hardcoded-copy,
same-shape pattern as `notify_new_contact_view` (`type="outcome_tag_prompt"`, already the exact value
`04_DATABASE.md`'s own column documentation names; `related_entity_type="contact_view"`,
`related_entity_id=contact_view_id`). Called once, synchronously, from `ContactService.create_contact_view` —
**a small, additive change to CON-001's already-shipped code**, flagged explicitly per this project's standing
practice for cross-story touch-points: after the `contact_views` row is created, add one unconditional call
(`notification_service.notify_outcome_tag_prompt(user_id=current_user_id, contact_view_id=contact_view.id)`),
alongside (not replacing) the existing conditional provider-lead notification. Unconditional, unlike the provider
notification, because the calling customer always has an owning Account (they are authenticated) — there is no
"unclaimed listing" equivalent gap on the customer side. Fired **immediately**, in the same request/transaction as
Contact View creation — not after a genuine time delay — because no scheduling/background-job infrastructure
exists anywhere in this codebase (Verified Current State), and AC3's own verbatim wording only requires
"triggered after a Contact View," which an immediate emission satisfies literally (flagged as Open Question 1 for
CTO awareness, not a blocker).

**Alternatives considered and rejected:**
- **Building a real delayed/scheduled trigger** (matching `14_USER_FLOWS.md`'s "some time after" narrative
  framing literally). Rejected for this story — it would require introducing new scheduling infrastructure
  (Celery/APScheduler/cron, none of which exists anywhere in this stack) that no AC actually asks for, mirroring
  this codebase's existing discipline against inventing unrequested mechanisms (e.g., "never invent a push-
  notification 'notify the admin team' mechanism" for the admin queue pattern).
- **Firing the notification from a new endpoint the mobile client calls itself, on the Provider Profile screen's
  own timeline, instead of from `ContactService`.** Rejected — the Contact View's creation is the one moment this
  event is unambiguously and reliably known to have happened; deferring it to a second, separate client-triggered
  call would create a window where a client that crashes/backgrounds after Contact View creation but before that
  second call never gets the record at all.

### Decision 6 — The Outcome Tag Prompt sheet is triggered directly after the Contact Reveal sheet closes (same session), not via a Notifications-Inbox tap-through

**The problem:** AC3 requires the prompt to be a real, dismissible UI surface the customer actually sees. The
"via a notification" mechanism (Decision 5) only guarantees a backend record exists — it does not, on its own,
give the customer any way to reach the sheet today, since no Notifications Inbox (S-13) or any notification-
listing endpoint exists anywhere in this codebase (Verified Current State).

**Chosen:** `ProviderProfileScreen._onContactTap` now `await`s `ContactRevealSheet.show(context, args)` (previously
fire-and-forget); once that `Future<void>` resolves (the Contact Reveal sheet has closed, by any means), it reads
`contactRevealControllerProvider(args)`'s state — if `status == loaded` (a real reveal happened, not merely an
error state the user backed out of), it opens the new `OutcomeTagPromptSheet` with the just-created
`contact_view_id` (`reveal.id`), the provider's display name (`reveal.providerDisplayName`), and its photo
(`profile.primaryPhotoUrl`, already loaded by `providerProfileControllerProvider`). This mirrors CON-001's own
AC7 scope trim exactly: the honest backend record (Decision 5) exists now, ready for a future Notifications Inbox
(ENG-001-adjacent work) to tap through to later, while this story's own mobile scope uses the one delivery
mechanism that is genuinely buildable and testable today.

**Alternatives considered and rejected:**
- **Build a minimal Notifications Inbox screen/endpoint now**, just so the prompt has a "real" notification-driven
  entry point end to end. Rejected as unrequested scope creep — no AC asks for a Notifications Inbox, `15_SCREEN_
  INVENTORY.md`'s S-13 is a separate, larger screen with its own filter/grouping requirements, and building even a
  minimal slice of it now would preempt scope that isn't this story's to claim.
- **Show the Outcome Tag Prompt sheet immediately, in parallel with (or instead of) the Contact Reveal sheet**,
  rather than sequentially after it closes. Rejected — a customer who hasn't even seen the phone number yet
  cannot meaningfully answer "did you hire them," and stacking two sheets at once is a confusing interaction
  pattern with no precedent in this codebase's UI conventions.

### Decision 7 — "Maybe later" performs zero network calls and creates no row

**The problem:** AC3 requires the dismiss action to carry "no penalty." What does "no penalty" mean mechanically?

**Chosen:** the sheet's "Maybe later" action (and any other dismiss path — swipe-down, tap-outside) simply closes
the sheet; no API call is made, no row of any kind is written. This is not a special case requiring any backend
support — it is the natural absence of an action, and AC5 already establishes that an absent outcome tag is a
fine, honestly-retained-by-omission state (nothing to "undo" or "flag" later).

**Alternatives considered and rejected:**
- **Recording a "dismissed" marker (e.g., a fourth `hired` state, or a separate dismissal timestamp column).**
  Rejected — no AC asks for this, `04_DATABASE.md`'s spec has no such column, and AC4's "does not attempt to
  capture... scheduling" minimalism principle extends naturally to not inventing a new tracked event for a
  no-op.

---

## Backend — Proposed Changes

1. **New Alembic migration** (`outcome_tags_domain`, on top of `024bcc0fbaf8`): creates `contact.outcome_tags`
   exactly per `04_DATABASE.md`'s spec — full `CommonColumnsMixin` columns (soft-delete is the default; `04_
   DATABASE.md`'s Soft Delete section exempts only `audit_logs`/`search_event_log`) plus `contact_view_id` (FK →
   `contact.contact_views.id`, not null), `hired` (BOOLEAN, not null), `submitted_at` (TIMESTAMPTZ, not null,
   default `now()`), and `uq_outcome_tags_contact_view_id` (a `UniqueConstraint`/unique index on `contact_view_id`).
   Does **not** create a new schema (`contact` already exists) and does **not** touch `visit_verifications` or
   `reviews` — both remain explicitly out of scope.
2. **`backend/app/modules/contact/models.py`** — add `OutcomeTag(CommonColumnsMixin, Base)` alongside the existing
   `ContactView` (Decision 1), `__tablename__ = "outcome_tags"`, `contact_view_id` (FK, not null, unique),
   `hired` (Boolean, not null), `submitted_at` (DateTime, not null, server default `now()`).
3. **New file `backend/app/modules/contact/repositories/outcome_tag_repository.py`** — `OutcomeTagRepository
   (BaseRepository[OutcomeTag])` with one custom method, `try_create(values: dict) -> OutcomeTag | None`
   (Decision 3's atomic `ON CONFLICT DO NOTHING ... RETURNING` insert).
4. **New file `backend/app/modules/contact/services/outcome_tag_service.py`** — `OutcomeTagService.
   submit_outcome_tag(current_user_id, *, contact_view_id, hired) -> OutcomeTag`:
   1. Resolve the caller's `customer_profiles` row via `CustomerProfileRepository.get_by_user_id(current_user_id)`
      — `CustomerProfileNotFoundError` if missing (defensive, mirrors `ContactService`).
   2. Resolve the target `ContactView` via `ContactViewRepository.get_by_id(contact_view_id)`.
   3. `ensure_owner_or_not_found(contact_view.customer_id if contact_view is not None else None,
      customer_profile.id, not_found_exc=ContactViewNotFoundError())` (AC2, Decision 2).
   4. `OutcomeTagRepository.try_create({"contact_view_id": contact_view_id, "hired": hired})` — if `None`,
      raise `OutcomeTagAlreadyExistsError` (Decision 3).
   5. Return the new `OutcomeTag`.
5. **`backend/app/modules/contact/schemas.py`** — add `SubmitOutcomeTagRequest` (`hired: bool`) and
   `OutcomeTagResponse` (`id`, `contact_view_id`, `hired`, `submitted_at`).
6. **`backend/app/modules/contact/api.py`** — add `POST /contact-views/{contact_view_id}/outcome-tag` to the
   existing router (same `/contact-views` prefix, same `["Contact"]` tag, `require_role(ROLE_CUSTOMER)`), 201 on
   success, documented 404 (not found/not owned) and 409 (already submitted) responses.
7. **`backend/app/modules/contact/dependencies.py`** — add `get_outcome_tag_repository`, `get_outcome_tag_service`
   (wires `OutcomeTagRepository`, the existing `ContactViewRepository`, the existing `CustomerProfileRepository`
   — no `NotificationService` dependency needed here, since the prompt notification is emitted at Contact View
   creation time, not at outcome-tag submission time).
8. **`backend/app/core/exceptions/exceptions.py` + `__init__.py`** — new `ContactViewNotFoundError` (404, Decision
   2) and `OutcomeTagAlreadyExistsError` (409, Decision 3).
9. **`backend/app/modules/notification/services/notification_service.py`** — new `notify_outcome_tag_prompt(*,
   user_id, contact_view_id)` (Decision 5), same hardcoded-copy pattern as `notify_new_contact_view`,
   `type="outcome_tag_prompt"`.
10. **`backend/app/modules/contact/services/contact_service.py`** — **flagged touch-point on CON-001's shipped
    code**: `create_contact_view` gains one new, unconditional call after the `contact_views` row is created:
    `await self.notification_service.notify_outcome_tag_prompt(user_id=current_user_id,
    contact_view_id=contact_view.id)` (Decision 5). No other line of this method changes; the existing
    conditional provider-lead notification is untouched.

### Tests

11. `backend/tests/modules/contact/test_outcome_tag_service.py` — ownership rejection (AC2: another customer's
    contact view → `ContactViewNotFoundError`, asserted with no row written); happy path (`hired=True` and
    `hired=False` both succeed and are retained — AC5); uniqueness (AC1/AC6: a second `submit_outcome_tag` call
    against the same `contact_view_id` — including from the *same* customer — raises
    `OutcomeTagAlreadyExistsError`, and a direct row-count query confirms exactly one row exists); a nonexistent
    `contact_view_id` also 404s (collapsed into the same ownership-rejection case, per Decision 2); the
    `CustomerProfileNotFoundError` defensive check.
12. `backend/tests/modules/contact/test_outcome_tag_api.py` — full HTTP round trip: 201 happy path (both `hired`
    values), 404 (not found / not owned), 409 (duplicate submission), 401 unauthenticated, 403 wrong role.
13. `backend/tests/modules/contact/test_contact_service.py` — extend the existing happy-path test(s) to assert a
    second, `type="outcome_tag_prompt"` `Notification` row is now also created for the *customer* at Contact View
    creation time (in addition to the existing provider-lead notification assertion) — direct regression coverage
    for Decision 5's touch-point on already-shipped code, verifying the existing self-dealing/unclaimed-listing/
    search-request-id tests are all otherwise unaffected (the self-dealing rejection path still creates zero
    notifications of either type, since it raises before any row exists).
14. `backend/tests/modules/notification/test_notification_service.py` — extend: `notify_outcome_tag_prompt`
    creates the expected row shape (`type="outcome_tag_prompt"`, `related_entity_type="contact_view"`,
    plain-language copy).
15. Full existing backend suite re-run (not just new tests), plus `ruff check .`.

---

## Frontend — Proposed Changes

No new mobile dependency is required — this reuses `dio`/Riverpod/`showModalBottomSheet`, all already in place
from CON-001.

1. **`mobile/lib/features/provider_profile/`** (the same feature CON-001 built — this is a direct continuation of
   the same contact flow, not a new feature):
   - `domain/models/outcome_tag.dart` — parses `POST .../outcome-tag`'s response.
   - `domain/models/outcome_tag_exception.dart` — mirrors `contact_exception.dart`'s per-feature exception-mapping
     convention (`notFound`, `alreadyExists`, `network`, `unknown`).
   - `data/provider_profile_repository.dart` — add `submitOutcomeTag({required String contactViewId, required
     bool hired})`, calling `POST /contact-views/$contactViewId/outcome-tag`, mapping errors via a new
     `_mapOutcomeTagError` (same shape as `_mapContactError`/`_mapProfileError`). Added to the existing repository
     class rather than a new one — this is the same feature's third small endpoint, not a new concern.
   - `state/outcome_tag_prompt_controller.dart` (Riverpod, `family` keyed by `contact_view_id`) — owns the
     submit action's own loading/error/submitted state, kept separate from `ContactRevealController`/
     `ProviderProfileController` per this codebase's established "each sheet's own in-flight state doesn't couple
     to the screen/other-sheet's" principle.
   - `presentation/widgets/outcome_tag_prompt_sheet.dart` (`OutcomeTagPromptSheet`) — the bottom sheet
     (`showModalBottomSheet`, `07_UI_GUIDELINES.md`/`DESIGN.md`'s `bottom-sheet` convention): provider name/photo
     (per `15_SCREEN_INVENTORY.md`'s sheet row), the "Did you hire them?" title, a Yes button (submits
     `hired=true`, then closes), a No button (submits `hired=false`, then closes), and a "Maybe later" text
     button that closes the sheet with **zero** network calls (Decision 7). Loading state while a Yes/No
     submission is in flight; a lightweight inline error state for a genuine network/unknown failure, with retry
     (mirrors `ContactRevealSheet`'s own error-content shape) — a 404/409 (edge cases that should be effectively
     unreachable in the normal flow) simply close the sheet rather than surfacing a scary error, since both mean
     "there's nothing more to do here" from the customer's point of view.
2. **`mobile/lib/features/provider_profile/presentation/screens/provider_profile_screen.dart`** — `_onContactTap`
   becomes `async`, `await`s `ContactRevealSheet.show(context, args)`, then (guarded by `context.mounted`) reads
   `contactRevealControllerProvider(args)`'s state; if `status == loaded`, opens `OutcomeTagPromptSheet.show(
   context, contactViewId: reveal.id, providerDisplayName: reveal.providerDisplayName, providerPhotoUrl:
   state.profile?.primaryPhotoUrl)` (Decision 6).
3. **`mobile/lib/l10n/app_en.arb` / `app_ar.arb`** — new keys: `outcomeTagPromptTitle` ("Did you hire them?"),
   `outcomeTagPromptYesLabel` ("Yes"), `outcomeTagPromptNoLabel` ("No"), `outcomeTagPromptMaybeLaterLabel` ("Maybe
   later"), and a brief post-submission confirmation copy (e.g. `outcomeTagPromptThanksMessage`) at `frontend`'s
   discretion for basic responsiveness — not itself an AC requirement, a minor UX-completeness detail only.

### Tests

4. `mobile/test/features/provider_profile/` — controller tests for `OutcomeTagPromptController` (submit success
   for both `hired` values, error mapping, "Maybe later"/dismiss performs no repository call at all — asserted via
   a mock repository never being invoked); widget tests for `OutcomeTagPromptSheet` (provider name/photo rendered,
   all three actions present and wired, Yes/No close the sheet after a successful submit, Maybe later closes with
   zero calls).
5. `provider_profile_screen_test.dart` (or equivalent) — updated to assert the sequential chain: after a
   successful Contact Reveal closes, the Outcome Tag Prompt sheet is shown next; after an *error* Contact Reveal
   (never reached `loaded`) closes, no Outcome Tag Prompt sheet appears.
6. Full existing mobile suite re-run (not just new tests), plus `flutter analyze`.

---

## Explicitly Out of Scope (do not implement in this story)

- **The review itself** (`reviews`, `provider_rating_summaries`) — `REV-002`'s own explicit scope boundary, the
  story's own stated line: "does not include the review itself... which requires a 'Yes' outcome tag as its
  anchor."
- **`13_OPEN_DECISIONS.md` item 14** (whether `provider_rating_summaries` is still needed) — explicitly
  `REV-002`'s design question, not this story's, per `docs/AI/SESSION_HANDOFF.md`'s own framing.
- **`visit_verifications`** ("Verified Visit" OTP-based confirmation) — untouched by this story, remains fully
  unbuilt, as it was after CON-001.
- **Any real notification delivery mechanism** (push/SMS/email, a Notifications Inbox screen, a "list my
  notifications" endpoint) — mirrors CON-001's own AC7 scope trim; this story only emits the honest in-app
  `notification.notifications` record (Decision 5/6).
- **A real, scheduled/delayed trigger** for the prompt, matching `14_USER_FLOWS.md`'s "some time after" narrative
  literally — no scheduling infrastructure exists in this codebase; flagged as Open Question 1, not built here
  (Decision 5).
- **Editing or resubmitting a previously-submitted outcome tag** — immutable, one-shot by design (Decision 4).
- **`notification_preferences`-based opt-out of the outcome-tag prompt** — `notification_preferences` remains
  fully unbuilt (confirmed, unaffected by this story); nothing to check yet, mirroring `notify_new_contact_view`'s
  own identical posture.
- **Any change to `providers.average_rating`/`review_count` or the `MAT-001` ranking formula** — this story writes
  only `outcome_tags`; rating data remains entirely `REV-002`'s future write path, unaffected here.

---

## Open Questions (flagged for CTO awareness — do not block `backend`/`frontend` from starting)

1. **Decision 5's "immediate, not delayed" notification timing.** `14_USER_FLOWS.md`'s narrative framing ("some
   time after the Contact View") could imply a genuine delay is eventually wanted, once real scheduling
   infrastructure exists (a later, unscoped story). This Plan fires immediately, synchronously, at Contact View
   creation — satisfying AC3's literal wording but not the flow doc's softer timing suggestion. Flagged for
   awareness; not a blocker, and a one-line change (moving the call to a scheduled job) whenever such
   infrastructure exists.
2. **Decision 2's status code choice (404, not 403) for AC2's ownership rejection.** A direct, mirrored reuse of
   ADR-015/CON-001 Decision 4's existing precedent — confirm this is the intended semantic (it should be, given
   the precedent), or flag a preference.
3. **Decision 4's "immutable, one-shot" outcome tag.** Confirm a customer should never be able to change a
   previously-submitted "Yes"/"No" — no AC requests an edit path, but this is worth an explicit nod before it
   becomes an assumption baked into `REV-002`'s anchor-verification design.

---

## Delegation & Execution Sequence

No Checkpoint exists for this story yet (fresh start).

1. **backend** — Backend Proposed Changes items 1–15. Build order: (a) the migration first (item 1); (b) the
   `OutcomeTag` model/repository/service/schemas/route (items 2–8), with tests 11–12 written alongside, since
   Decision 2 (ownership) and Decision 3 (uniqueness race) are this story's two safety-critical mechanisms; (c)
   the `NotificationService` extension (item 9, with test 14); (d) the flagged `ContactService` touch-point (item
   10, with the regression extension in test 13) last, since it depends on the new `NotificationService` method
   existing first. Read Decision 2 and Decision 3 in full before starting — they are this story's core
   correctness mechanisms, mirroring how CON-001's Decision 1 was called out as its own single most
   safety-critical piece.
2. **frontend** — Frontend Proposed Changes items 1–6. Should start once `backend`'s new `POST .../outcome-tag`
   endpoint is available to integrate against (or in parallel against this Plan's documented response shape, per
   this codebase's established parallelization practice, with a final integration pass once both are done).
3. **tester** — verify all 6 verbatim ACs with real evidence (real DB, real HTTP round trips, real widget tests).
   Particular attention to: AC1/AC6 (a genuine concurrent-submission-shaped test proving the `ON CONFLICT`
   mechanism actually rejects a second insert, not merely "the second call happened to fail for some reason,"
   plus a direct row-count assertion); AC2 (construct a real fixture where a *different* customer's Contact View
   is targeted, confirming 404 and zero rows written); AC3 (the sheet genuinely renders after a real Contact
   Reveal, "Maybe later" is confirmed to make zero network calls via a mock/spy, and the backend notification row
   is genuinely created with the right `type`); AC4 (confirm the schema/request/response shapes carry no
   payment/scheduling/job-detail field anywhere); AC5 (a `hired=false` row is queried back and confirmed still
   present — not deleted or coerced to absent). Also confirm the CON-001 regression: existing self-dealing/
   unclaimed-listing/search-request-id tests in `test_contact_service.py` are unaffected by the new notification
   call.
4. **architect** — review Decision 2's ownership-check-shape choice against `06_SECURITY.md`/ADR-015 (confirm 404
   is correct and no information leak exists); Decision 3's `ON CONFLICT DO NOTHING` mechanism for genuine
   atomicity (confirm no window exists where two concurrent requests could both see a returned row, or where the
   second caller's request silently succeeds with stale data); Decision 5's touch-point on CON-001's shipped
   `ContactService` (confirm it is a pure, additive, non-behavior-changing addition to the existing method, not a
   refactor that risks the self-dealing guard); Decision 1's module-placement choice against `02_ARCHITECTURE.md`
   (confirm no new problematic cross-module edge is introduced — `OutcomeTagService` should only need
   `ContactViewRepository`/`CustomerProfileRepository`, both already-precedented raw-repository edges from CON-001,
   no new edge to `provider`/`search`/`notification`).
5. Once `tester` and `architect` both report clean, **pause and present to the user** before writing the
   Walkthrough or touching `docs/CHANGELOG.md`/tracker, per standing process. If approved:
   - Record Decisions 1–7 as new ADRs (next available: **ADR-048** onward), grouped where several decisions share
     one architectural theme, at `tech-lead`'s discretion at closeout.
   - Update `04_DATABASE.md` to note `outcome_tags` is now shipped (cross-reference this Plan/Walkthrough),
     exactly per its existing spec, no deviation.
   - Update `PROJECT_IMPLEMENTATION_STATE.md`'s Sprint 9 section and `docs/AI/SESSION_HANDOFF.md` — `REV-001`
     becomes Done, `REV-002` becomes the next startable story in Milestone ML9.

---

## Verification Plan (mapped to the 6 verbatim ACs)

| AC | Verified by |
|---|---|
| 1 | The real migration (item 1) plus `test_outcome_tag_service.py`'s uniqueness test (a second `submit_outcome_tag` against the same `contact_view_id` is rejected, with a direct row-count assertion confirming exactly one row exists). |
| 2 | `test_outcome_tag_service.py`'s ownership-rejection fixture (a second customer's `contact_view_id`, or a nonexistent one) asserting `ContactViewNotFoundError` and zero rows written; `test_outcome_tag_api.py`'s matching 404 HTTP case. |
| 3 | A mobile widget test confirming `OutcomeTagPromptSheet` renders after a successful Contact Reveal (Decision 6) and that "Maybe later" triggers zero repository calls (a mock-repository-never-called assertion); `test_notification_service.py`'s `notify_outcome_tag_prompt` unit test plus `test_contact_service.py`'s integration assertion that Contact View creation now also creates a `type="outcome_tag_prompt"` notification for the customer. |
| 4 | A direct inspection of `outcome_tags`' migration/model columns, `SubmitOutcomeTagRequest`/`OutcomeTagResponse` schemas, and the mobile request/response models — confirming no payment, job-completion, or scheduling field exists anywhere in this story's new surface. |
| 5 | `test_outcome_tag_service.py`'s `hired=False` happy-path test, directly querying the row back afterward to confirm it exists and was not deleted/coerced; a separate test confirming a Contact View with **no** outcome tag at all is a valid, unexceptional state (no error, no synthesized row). |
| 6 | `test_outcome_tag_service.py`/`test_outcome_tag_api.py`'s ownership-rejection and uniqueness-rejection tests are both present as explicit, separately-named test cases (not merged into one parameterized test), satisfying AC6's literal wording. |

---

## Related Documents

- `docs/AI/03_DOMAIN_MODEL.md` (Outcome Tag domain — the exact business rules this Plan implements: Customer-only
  submission, "Yes" as a Review prerequisite, deliberate minimalism)
- `docs/AI/04_DATABASE.md` (Contact Domain — `outcome_tags`' full column/constraint spec; Notifications Domain —
  the `outcome_tag_prompt` `type` value already named there; Common Columns/Soft Delete sections)
- `docs/AI/09_DECISIONS.md` (ADR-015 — the `{id}`-addressable-collection-always-404 convention Decision 2 reuses;
  ADR-044 — the self-dealing 403 shape Decision 2 deliberately does *not* reuse; ADR-047 — the services-only
  cross-module convention this story's `contact` module continues to follow)
- `docs/AI/13_OPEN_DECISIONS.md` (item 14 — explicitly not this story's decision, `REV-002`'s instead)
- `docs/AI/14_USER_FLOWS.md` (Flow 4 steps 12–14, the Notification Triggers table — the "Outcome Tag prompt |
  Customer | Flow 4, step 13" row this Plan's Decision 5/6 implement)
- `docs/AI/15_SCREEN_INVENTORY.md` (the Outcome Tag Prompt sheet row this Plan's mobile work builds)
- `docs/implementation/plans/Plan_S08_CON-001.md` / `Walkthrough_S08_CON-001.md` (the `contact` module, `Contact
  Service`, `NotificationService.notify_new_contact_view`, and the mobile Contact Reveal flow this Plan directly
  extends; ADR-044's self-dealing 403 precedent Decision 2 contrasts against)
- `docs/implementation/plans/Plan_S07_AI-002.md` / `Plan_S06_CLM-001.md` (the atomic-conditional-write family
  Decision 3 extends: `try_claim_for_account`, `try_claim_for_review`, `try_resolve`)
- `docs/implementation/plans/Plan_S07_CTG-001.md` (the `ON CONFLICT DO NOTHING ... RETURNING` mechanism Decision 3
  reuses, there for idempotent seeding)

---

**End of Document**
