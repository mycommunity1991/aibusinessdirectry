# Checkpoint — Sprint 12, ENG-001 (Receive Marketplace Notifications In My Preferred Channel)

**Owner of this checkpoint:** `frontend` (mobile engineer)
**Status:** Frontend (mobile) implementation complete. Backend already merged (commit `2442b9f`, 929/929 backend tests passing). Awaiting `tester` and `architect` review.

## What's done (this session, frontend only)

Implemented per `docs/implementation/plans/Plan_S12_ENG-001.md`'s "Frontend — Proposed Changes" (items 1-5) and "Tests" (items 6-8) sections, against the already-merged backend endpoints (`GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`, confirmed directly against `backend/app/modules/notification/schemas.py` and `api.py`).

### New feature folder `mobile/lib/features/notifications/`
- `domain/models/notification_item.dart` — mirrors `NotificationResponse`.
- `domain/models/notification_exception.dart` — `network`/`unknown` only (per literal task spec).
- `data/notification_repository.dart` — `listNotifications`, `getUnreadCount`, `markRead`.
- `state/notifications_controller.dart` — `NotificationsController` (list/status, mirrors `LeadsController`); invalidates the **shared** `unreadNotificationCountProvider` (see below) on page-1 load and after `markRead` — a deliberate deviation from the Plan's literal "state file owns the unread-count provider" wording, explained below.
- `presentation/screens/notifications_inbox_screen.dart` (`NotificationsInboxScreen`) — New/Earlier sectioned list, loading/error/empty states, deep-links per `relatedEntityType` (verification_record → verificationStatus, contact_view+new_contact_view → leads, contact_view+outcome_tag_prompt → reopens the existing `OutcomeTagPromptSheet`, manual_match_assignment → read-only, no nav).
- `presentation/utils/notification_error_copy.dart`.

### Shared cross-feature badge
- `mobile/lib/shared/data/unread_notification_count_repository.dart` (new) — `UnreadNotificationCountRepository` + `unreadNotificationCountProvider`, mirroring `verification_status_summary_repository.dart`'s "minimal, independent, shared read" precedent. This is what `features/home/`'s new entry-point tile watches, and what `NotificationsController` invalidates — kept in `shared/` (not `features/notifications/`) per `docs/AI/02_ARCHITECTURE.md`'s "features must not depend on each other" rule, since `features/home/` would otherwise have to import `features/notifications/`.

### Routing
- `AppRoutes.notificationsInbox = '/notifications-inbox'` added.
- `GoRoute` registered in `app_router.dart`.

### Home entry point
- `home_placeholder_screen.dart` — new `_NotificationsEntryPointCard` (mirrors `_LeadsEntryPointCard`'s shape) + `_UnreadCountBadge`, reading the shared provider above.

### l10n
- Added to both `app_en.arb`/`app_ar.arb`: `notificationsInboxTitle`, `notificationsNewSectionHeader`, `notificationsEarlierSectionHeader`, `notificationsEmptyStateMessage`, `homeNotificationsEntryLabel` (all five requested), plus one extra key not in the original literal list — `notificationsOutcomeTagPromptGenericProviderLabel` (see deviations below). Ran `flutter gen-l10n` after editing.

### Tests (all new, all passing)
- `mobile/test/features/notifications/notifications_controller_test.dart` (11 cases) — loaded/error/empty/pagination/markRead + shared unread-count-refresh behavior.
- `mobile/test/features/notifications/notifications_inbox_screen_test.dart` (9 cases) — loading/error/empty/New-Earlier-grouping + all four `relatedEntityType` tap cases.
- `mobile/test/features/notifications/fakes/fake_notification_repository.dart`, `mobile/test/shared/fakes/fake_unread_notification_count_repository.dart`.
- Extended `mobile/test/features/home/home_placeholder_screen_test.dart` (+3 cases) — entry tile presence, badge-from-fixture, zero-badge-when-zero, navigation.

## Final numbers
- Mobile suite: **303/303 passing** (was 280/280 baseline before this story — 23 net new tests, zero regressions).
- `flutter analyze`: clean, no issues.
- `dart format`: clean on every file this story touched (two pre-existing, untouched files elsewhere in the repo have their own pre-existing formatting drift, left as-is — out of this story's scope).

## Deviations from the Plan's literal text (flagged for `tester`/`architect`)
1. **Unread-count provider location.** The Plan's Frontend item 1 literally says the "separate, lightweight unread-count provider" lives in `state/notifications_controller.dart`. Implemented instead as a **shared** provider (`shared/data/unread_notification_count_repository.dart`), with `NotificationsController` invalidating it, because `features/home/`'s badge tile watching a `features/notifications/`-owned provider would violate this codebase's own standing "features must not depend on each other" rule (`docs/AI/02_ARCHITECTURE.md`, already enforced by the `_VerificationStatusChip` precedent in `storefront_screen.dart`). `NotificationRepository.getUnreadCount()` itself is still implemented exactly as the Plan specifies (part of the repository's public contract) — only the *provider* wiring for the badge was relocated to `shared/`.
2. **One extra l10n key beyond the five named**: `notificationsOutcomeTagPromptGenericProviderLabel`. The reused `OutcomeTagPromptSheet` requires a non-null `providerDisplayName` argument, but a notification's own payload (id/type/title/body/relatedEntityType/relatedEntityId) carries no real provider name to pass — added one honest, generic fallback string rather than fabricating a name or hardcoding a literal.

## Not started / explicitly out of scope for `frontend`
- No backend changes (already merged).
- No Walkthrough, ADRs, tracker, or changelog updates — per instruction, deferred until after `tester`/`architect` review and explicit user sign-off.

## Next step
Hand off to `tester` to verify AC6 (and the mobile half of AC5) against this implementation, then `architect` review, per the Plan's Delegation & Execution Sequence.
