import 'package:ai_marketplace_app/features/notifications/data/notification_repository.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_exception.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_item.dart';
import 'package:ai_marketplace_app/features/notifications/state/notifications_controller.dart';
import 'package:ai_marketplace_app/shared/data/unread_notification_count_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../shared/fakes/fake_unread_notification_count_repository.dart';
import 'fakes/fake_notification_repository.dart';

/// `ENG-001` -- `NotificationsController` (`Plan_S12_ENG-001.md`, Frontend
/// item 1, Tests item 6). Exercised directly via a [ProviderContainer], with
/// no widget tree involved, mirroring `leads_controller_test.dart`'s
/// pattern.
void main() {
  ProviderContainer buildContainer(
    FakeNotificationRepository repository, {
    FakeUnreadNotificationCountRepository? unreadCountRepository,
  }) {
    final container = ProviderContainer(
      overrides: [
        notificationRepositoryProvider.overrideWithValue(repository),
        if (unreadCountRepository != null)
          unreadNotificationCountRepositoryProvider.overrideWithValue(
            unreadCountRepository,
          ),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  NotificationItem buildNotification(
    String id, {
    String type = 'new_contact_view',
    String? relatedEntityType = 'contact_view',
    String? relatedEntityId = 'contact-view-1',
    DateTime? readAt,
  }) {
    return NotificationItem(
      id: id,
      type: type,
      title: 'title-$id',
      body: 'body-$id',
      relatedEntityType: relatedEntityType,
      relatedEntityId: relatedEntityId,
      readAt: readAt,
      createdAt: DateTime.utc(2026, 1, 1),
    );
  }

  test('load() reaches loaded status with the fetched notifications', () async {
    final notifications = [buildNotification('n-1'), buildNotification('n-2')];
    final fakeRepository = FakeNotificationRepository(pages: [notifications]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(notificationsControllerProvider);
    expect(state.status, NotificationsStatus.loaded);
    expect(state.notifications, notifications);
    expect(state.hasMore, isFalse);
  });

  test('load() with zero notifications reaches loaded status with an empty '
      'list, never error', () async {
    final fakeRepository = FakeNotificationRepository(pages: const [[]]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(notificationsControllerProvider);
    expect(state.status, NotificationsStatus.loaded);
    expect(state.notifications, isEmpty);
  });

  test('a load failure maps to the error status, carrying the exception '
      'unchanged', () async {
    final fakeRepository = FakeNotificationRepository(
      listNotificationsError: const NotificationException(
        type: NotificationErrorType.network,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(notificationsControllerProvider);
    expect(state.status, NotificationsStatus.error);
    expect(state.error?.type, NotificationErrorType.network);
  });

  test('loadMore() appends the next page to the already-loaded list '
      '(pagination page-append behavior)', () async {
    final page1 = [buildNotification('n-1'), buildNotification('n-2')];
    final page2 = [buildNotification('n-3'), buildNotification('n-4')];
    final fakeRepository = FakeNotificationRepository(pages: [page1, page2]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();
    expect(container.read(notificationsControllerProvider).hasMore, isTrue);

    await notifier.loadMore();

    final state = container.read(notificationsControllerProvider);
    expect(state.notifications, [...page1, ...page2]);
    expect(state.page, 2);
    expect(state.hasMore, isFalse);
    expect(fakeRepository.listNotificationsCallCount, 2);
  });

  test('loadMore() is a no-op once hasMore is false', () async {
    final page1 = [buildNotification('n-1')];
    final fakeRepository = FakeNotificationRepository(pages: [page1]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();
    expect(container.read(notificationsControllerProvider).hasMore, isFalse);

    await notifier.loadMore();

    expect(fakeRepository.listNotificationsCallCount, 1);
    expect(
      container.read(notificationsControllerProvider).notifications,
      page1,
    );
  });

  test('refresh() resets to page 1, replacing the accumulated list rather '
      'than appending to it', () async {
    final page1 = [buildNotification('n-1'), buildNotification('n-2')];
    final page2 = [buildNotification('n-3'), buildNotification('n-4')];
    final fakeRepository = FakeNotificationRepository(pages: [page1, page2]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);

    await notifier.load();
    await notifier.loadMore();
    expect(
      container.read(notificationsControllerProvider).notifications.length,
      4,
    );

    await notifier.refresh();

    final state = container.read(notificationsControllerProvider);
    expect(state.notifications, page1);
    expect(state.page, 1);
    expect(fakeRepository.lastArgs, (page: 1, pageSize: 20));
  });

  test('markRead() updates the targeted notification in place with the '
      "repository's returned row, leaving every other row untouched", () async {
    final notifications = [buildNotification('n-1'), buildNotification('n-2')];
    final updated = buildNotification('n-1', readAt: DateTime.utc(2026, 1, 2));
    final fakeRepository = FakeNotificationRepository(
      pages: [notifications],
      markReadResult: updated,
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(notificationsControllerProvider.notifier);
    await notifier.load();

    await notifier.markRead('n-1');

    final state = container.read(notificationsControllerProvider);
    expect(state.notifications[0].readAt, updated.readAt);
    expect(state.notifications[1].readAt, isNull);
    expect(fakeRepository.lastMarkReadId, 'n-1');
  });

  test(
    'a markRead() failure is swallowed from the list state\'s own point of '
    'view -- the list is left unchanged rather than surfacing an error',
    () async {
      final notifications = [buildNotification('n-1')];
      final fakeRepository = FakeNotificationRepository(
        pages: [notifications],
        markReadError: const NotificationException(
          type: NotificationErrorType.unknown,
        ),
      );
      final container = buildContainer(fakeRepository);
      final notifier = container.read(notificationsControllerProvider.notifier);
      await notifier.load();

      await notifier.markRead('n-1');

      final state = container.read(notificationsControllerProvider);
      expect(state.status, NotificationsStatus.loaded);
      expect(state.notifications[0].readAt, isNull);
    },
  );

  group(
    'shared unreadNotificationCountProvider refresh (Plan Frontend item 1)',
    () {
      // Every test in this group reads `unreadNotificationCountProvider`
      // once up front, before triggering `load()`/`markRead()` -- this
      // "pre-warms" the provider so it's already mounted by the time
      // `NotificationsController` invalidates it, mirroring the real app's
      // own usage shape (the Home screen's badge is already watching this
      // provider well before a user ever opens the Inbox). Riverpod's
      // `Ref.invalidate` (unlike `ProviderContainer.invalidate`) mounts an
      // as-yet-uninitialized provider as a side effect of its own
      // debug-mode circular-dependency assertion, which would otherwise
      // make a bare call-count assertion misleading in a test-only way
      // that never occurs for an already-watched provider in the real app.
      test(
        'is refreshed on a page-1 load (Inbox open/pull-to-refresh)',
        () async {
          final fakeRepository = FakeNotificationRepository(pages: const [[]]);
          final fakeUnreadCountRepository =
              FakeUnreadNotificationCountRepository(counts: const [3, 1]);
          final container = buildContainer(
            fakeRepository,
            unreadCountRepository: fakeUnreadCountRepository,
          );
          final notifier = container.read(
            notificationsControllerProvider.notifier,
          );

          expect(
            await container.read(unreadNotificationCountProvider.future),
            3,
          );

          await notifier.load();

          expect(
            await container.read(unreadNotificationCountProvider.future),
            1,
          );
          expect(fakeUnreadCountRepository.getUnreadCountCallCount, 2);
        },
      );

      test('is refreshed after each markRead() call', () async {
        final notifications = [buildNotification('n-1')];
        final fakeRepository = FakeNotificationRepository(
          pages: [notifications],
        );
        // `counts[0]` backs the pre-warm read below (its value is never
        // itself asserted); `counts[1]`/`counts[2]` back the two reads
        // under test, after `load()` and after `markRead()` respectively.
        final fakeUnreadCountRepository = FakeUnreadNotificationCountRepository(
          counts: const [0, 2, 1],
        );
        final container = buildContainer(
          fakeRepository,
          unreadCountRepository: fakeUnreadCountRepository,
        );
        final notifier = container.read(
          notificationsControllerProvider.notifier,
        );
        // Pre-warm (see the group doc above).
        await container.read(unreadNotificationCountProvider.future);

        await notifier.load();
        expect(await container.read(unreadNotificationCountProvider.future), 2);

        await notifier.markRead('n-1');
        expect(await container.read(unreadNotificationCountProvider.future), 1);
        expect(fakeUnreadCountRepository.getUnreadCountCallCount, 3);
      });

      test('loadMore() (page 2+) does not itself trigger an extra unread-count '
          'refresh -- only page-1 loads do', () async {
        final page1 = [buildNotification('n-1')];
        final page2 = [buildNotification('n-2')];
        final fakeRepository = FakeNotificationRepository(
          pages: [page1, page2],
        );
        final fakeUnreadCountRepository = FakeUnreadNotificationCountRepository(
          count: 5,
        );
        final container = buildContainer(
          fakeRepository,
          unreadCountRepository: fakeUnreadCountRepository,
        );
        final notifier = container.read(
          notificationsControllerProvider.notifier,
        );
        // Pre-warm (see the group doc above).
        await container.read(unreadNotificationCountProvider.future);
        expect(fakeUnreadCountRepository.getUnreadCountCallCount, 1);

        await notifier.load();
        // Flushes `load()`'s page-1 invalidation.
        await container.read(unreadNotificationCountProvider.future);
        expect(fakeUnreadCountRepository.getUnreadCountCallCount, 2);

        await notifier.loadMore();
        // Flush any scheduled-but-not-yet-applied invalidation before
        // asserting the call count didn't change -- `loadMore()` (page
        // 2+) never itself calls `invalidate`, so this should be a no-op
        // read of the still-fresh cached value.
        await container.read(unreadNotificationCountProvider.future);

        expect(fakeUnreadCountRepository.getUnreadCountCallCount, 2);
      });
    },
  );
}
