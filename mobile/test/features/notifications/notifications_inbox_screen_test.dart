import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/notifications/data/notification_repository.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_exception.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_item.dart';
import 'package:ai_marketplace_app/features/notifications/presentation/screens/notifications_inbox_screen.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'fakes/fake_notification_repository.dart';

/// `ENG-001` -- `NotificationsInboxScreen`
/// (`Plan_S12_ENG-001.md`, AC5/AC6, Decision 10, Tests item 6).
void main() {
  NotificationItem buildNotification(
    String id, {
    String type = 'new_contact_view',
    String? relatedEntityType = 'contact_view',
    String? relatedEntityId = 'contact-view-1',
    DateTime? readAt,
    DateTime? createdAt,
  }) {
    return NotificationItem(
      id: id,
      type: type,
      title: 'title-$id',
      body: 'body-$id',
      relatedEntityType: relatedEntityType,
      relatedEntityId: relatedEntityId,
      readAt: readAt,
      createdAt: createdAt ?? DateTime.utc(2026, 1, 1),
    );
  }

  /// A minimal `GoRouter` shell -- `NotificationsInboxScreen` at its own
  /// path, plus stub destinations for [AppRoutes.verificationStatus]/
  /// [AppRoutes.leads] (Decision 10's deep-link targets) -- so a row's real
  /// `context.push(...)` call has a router ancestor to resolve against,
  /// mirroring `storefront_screen_test.dart`'s own stub-destination
  /// pattern rather than rendering the real target screens (which would
  /// need their own provider overrides, out of scope for a
  /// Notifications-Inbox-focused test file).
  Future<void> pumpInbox(
    WidgetTester tester,
    FakeNotificationRepository repository,
  ) async {
    final router = GoRouter(
      initialLocation: '/notifications-inbox-under-test',
      routes: [
        GoRoute(
          path: '/notifications-inbox-under-test',
          builder: (context, state) => const NotificationsInboxScreen(),
        ),
        GoRoute(
          path: AppRoutes.verificationStatus,
          builder: (context, state) =>
              const Scaffold(body: Text('verification-status-stub')),
        ),
        GoRoute(
          path: AppRoutes.leads,
          builder: (context, state) => const Scaffold(body: Text('leads-stub')),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          notificationRepositoryProvider.overrideWithValue(repository),
        ],
        child: MaterialApp.router(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          routerConfig: router,
        ),
      ),
    );
  }

  testWidgets('shows a loading indicator before the first page resolves', (
    tester,
  ) async {
    final fakeRepository = FakeNotificationRepository(pages: const [[]]);
    await pumpInbox(tester, fakeRepository);

    // Deliberately no `pumpAndSettle` yet -- asserts the very first
    // rendered frame, before `NotificationsController.load()`'s
    // post-frame-callback trigger has resolved.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();
  });

  testWidgets('a load failure shows a plain-language error, with a working '
      'retry', (tester) async {
    final fakeRepository = FakeNotificationRepository(
      listNotificationsError: const NotificationException(
        type: NotificationErrorType.network,
      ),
    );
    await pumpInbox(tester, fakeRepository);
    await tester.pumpAndSettle();

    expect(
      find.text(
        "We couldn't connect. Check your internet connection and try again.",
      ),
      findsOneWidget,
    );
    expect(find.text('Try again'), findsOneWidget);

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(fakeRepository.listNotificationsCallCount, 2);
  });

  testWidgets(
    'the empty state renders textually distinct copy and is genuinely '
    'pull-to-refresh-able, not merely styled',
    (tester) async {
      final fakeRepository = FakeNotificationRepository(pages: const [[]]);
      await pumpInbox(tester, fakeRepository);
      await tester.pumpAndSettle();

      expect(find.text('No notifications yet'), findsOneWidget);
      expect(find.byType(RefreshIndicator), findsOneWidget);
      expect(fakeRepository.listNotificationsCallCount, 1);

      await tester.fling(
        find.byType(SingleChildScrollView),
        const Offset(0, 300),
        1000,
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(fakeRepository.listNotificationsCallCount, 2);
    },
  );

  testWidgets(
    'groups unread notifications under "New" and read ones under "Earlier" '
    '(AC6\'s literal grouping requirement, from fixed readAt fixtures)',
    (tester) async {
      final fakeRepository = FakeNotificationRepository(
        pages: [
          [
            buildNotification('unread-1', readAt: null),
            buildNotification('read-1', readAt: DateTime.utc(2026, 1, 1, 12)),
          ],
        ],
      );
      await pumpInbox(tester, fakeRepository);
      await tester.pumpAndSettle();

      expect(find.text('New'), findsOneWidget);
      expect(find.text('Earlier'), findsOneWidget);
      expect(find.text('title-unread-1'), findsOneWidget);
      expect(find.text('title-read-1'), findsOneWidget);

      // The unread row alone carries the unread-indicator dot.
      expect(
        find.byKey(const ValueKey('notification-unread-dot')),
        findsOneWidget,
      );

      // "New" appears above "Earlier" -- verified via the top offset of
      // each header's rendered position.
      final newHeaderY = tester.getTopLeft(find.text('New')).dy;
      final earlierHeaderY = tester.getTopLeft(find.text('Earlier')).dy;
      expect(newHeaderY, lessThan(earlierHeaderY));
    },
  );

  testWidgets(
    'when every notification is unread, only the "New" header renders',
    (tester) async {
      final fakeRepository = FakeNotificationRepository(
        pages: [
          [buildNotification('unread-1', readAt: null)],
        ],
      );
      await pumpInbox(tester, fakeRepository);
      await tester.pumpAndSettle();

      expect(find.text('New'), findsOneWidget);
      expect(find.text('Earlier'), findsNothing);
    },
  );

  group('deep-link on tap (Decision 10)', () {
    testWidgets('a verification_record row marks it read and navigates to '
        'AppRoutes.verificationStatus', (tester) async {
      final fakeRepository = FakeNotificationRepository(
        pages: [
          [
            buildNotification(
              'n-1',
              type: 'verification_status_change',
              relatedEntityType: 'verification_record',
              relatedEntityId: 'verification-1',
            ),
          ],
        ],
      );
      await pumpInbox(tester, fakeRepository);
      await tester.pumpAndSettle();

      await tester.tap(find.text('title-n-1'));
      await tester.pumpAndSettle();

      expect(find.text('verification-status-stub'), findsOneWidget);
      expect(fakeRepository.markReadCallCount, 1);
      expect(fakeRepository.lastMarkReadId, 'n-1');
    });

    testWidgets(
      'a contact_view/new_contact_view row marks it read and navigates to '
      'AppRoutes.leads',
      (tester) async {
        final fakeRepository = FakeNotificationRepository(
          pages: [
            [
              buildNotification(
                'n-1',
                type: 'new_contact_view',
                relatedEntityType: 'contact_view',
                relatedEntityId: 'contact-view-1',
              ),
            ],
          ],
        );
        await pumpInbox(tester, fakeRepository);
        await tester.pumpAndSettle();

        await tester.tap(find.text('title-n-1'));
        await tester.pumpAndSettle();

        expect(find.text('leads-stub'), findsOneWidget);
        expect(fakeRepository.markReadCallCount, 1);
      },
    );

    testWidgets(
      'a contact_view/outcome_tag_prompt row marks it read and opens the '
      'existing OutcomeTagPromptSheet as a modal, reused as-is',
      (tester) async {
        final fakeRepository = FakeNotificationRepository(
          pages: [
            [
              buildNotification(
                'n-1',
                type: 'outcome_tag_prompt',
                relatedEntityType: 'contact_view',
                relatedEntityId: 'contact-view-1',
              ),
            ],
          ],
        );
        await pumpInbox(tester, fakeRepository);
        await tester.pumpAndSettle();

        await tester.tap(find.text('title-n-1'));
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('outcome-tag-prompt-provider-name')),
          findsOneWidget,
        );
        expect(fakeRepository.markReadCallCount, 1);

        // Still on the Inbox underneath the modal -- no `push` navigation
        // happened for this case.
        expect(find.text('verification-status-stub'), findsNothing);
        expect(find.text('leads-stub'), findsNothing);
      },
    );

    testWidgets(
      'a manual_match_assignment row marks it read but never navigates '
      "anywhere (Decision 9's no-admin-mobile-surface scope)",
      (tester) async {
        final notification = buildNotification(
          'n-1',
          type: 'manual_match_assignment_created',
          relatedEntityType: 'manual_match_assignment',
          relatedEntityId: 'assignment-1',
        );
        final fakeRepository = FakeNotificationRepository(
          pages: [
            [notification],
          ],
          // `markReadResult` mirrors the row unchanged apart from `readAt`
          // -- proves the title/body persist post-tap (still the same row,
          // just moved from New to Earlier), rather than the fake's own
          // generic placeholder default.
          markReadResult: NotificationItem(
            id: notification.id,
            type: notification.type,
            title: notification.title,
            body: notification.body,
            relatedEntityType: notification.relatedEntityType,
            relatedEntityId: notification.relatedEntityId,
            readAt: DateTime.utc(2026, 1, 2),
            createdAt: notification.createdAt,
          ),
        );
        await pumpInbox(tester, fakeRepository);
        await tester.pumpAndSettle();

        await tester.tap(find.text('title-n-1'));
        await tester.pumpAndSettle();

        expect(fakeRepository.markReadCallCount, 1);
        expect(fakeRepository.lastMarkReadId, 'n-1');
        expect(find.text('verification-status-stub'), findsNothing);
        expect(find.text('leads-stub'), findsNothing);
        // Still on the Inbox screen itself.
        expect(find.text('title-n-1'), findsOneWidget);
      },
    );
  });
}
