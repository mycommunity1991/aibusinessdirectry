import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/data/unread_notification_count_repository.dart';
import '../data/notification_repository.dart';
import '../domain/models/notification_exception.dart';
import '../domain/models/notification_item.dart';

/// The Notifications Inbox screen's (`ENG-001`, AC6) status -- mirrors
/// `LeadsStatus`'s shape (`features/leads/state/leads_controller.dart`):
/// [idle] before the first load, [loading] for that first load/a
/// pull-to-refresh, [loaded] once a page (possibly empty) has resolved,
/// [error] on failure.
enum NotificationsStatus { idle, loading, error, loaded }

class NotificationsState {
  const NotificationsState({
    this.status = NotificationsStatus.idle,
    this.notifications = const [],
    this.error,
    this.page = 1,
    this.hasMore = false,
    this.isLoadingMore = false,
  });

  final NotificationsStatus status;
  final List<NotificationItem> notifications;
  final NotificationException? error;

  /// The most recently, successfully loaded page number.
  final int page;

  /// Whether a further page exists beyond [notifications]'s current
  /// length.
  final bool hasMore;

  /// A second page (or later) is being appended -- kept separate from
  /// [status] so loading page 2+ never blanks the already-loaded list back
  /// to a full-screen spinner.
  final bool isLoadingMore;

  NotificationsState copyWith({
    NotificationsStatus? status,
    List<NotificationItem>? notifications,
    NotificationException? error,
    bool clearError = false,
    int? page,
    bool? hasMore,
    bool? isLoadingMore,
  }) {
    return NotificationsState(
      status: status ?? this.status,
      notifications: notifications ?? this.notifications,
      error: clearError ? null : (error ?? this.error),
      page: page ?? this.page,
      hasMore: hasMore ?? this.hasMore,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
    );
  }
}

/// Runs `GET /notifications` (`ENG-001`, AC6). Starts from
/// [NotificationsStatus.idle] -- mirrors `LeadsController`'s own shape
/// exactly, including leaving the first [load] call to the screen
/// (`NotificationsInboxScreen`'s `initState`) rather than firing it from
/// this constructor, so a test can construct this controller and drive
/// [load]/[refresh]/[loadMore]/[markRead] deterministically without racing
/// an unawaited constructor-triggered fetch.
class NotificationsController extends StateNotifier<NotificationsState> {
  NotificationsController(this._repository, this._ref)
    : super(const NotificationsState());

  final NotificationRepository _repository;
  final Ref _ref;

  static const _pageSize = 20;

  /// Loads [page] (default 1). Page 1 always replaces
  /// [NotificationsState.notifications] wholesale (used for the initial
  /// load and pull-to-refresh); any later page appends to the existing list
  /// (pagination page-append behavior) rather than replacing it. A page-1
  /// load also refreshes the shared [unreadNotificationCountProvider]
  /// (Plan Frontend item 1 -- "refreshed on Inbox open/pull-to-refresh"),
  /// so `features/home/`'s Notifications badge stays in sync if it's still
  /// mounted underneath this screen's route.
  Future<void> load({int page = 1}) async {
    if (page == 1) {
      state = state.copyWith(
        status: NotificationsStatus.loading,
        clearError: true,
      );
    } else {
      if (!state.hasMore || state.isLoadingMore) return;
      state = state.copyWith(isLoadingMore: true, clearError: true);
    }
    try {
      final result = await _repository.listNotifications(
        page: page,
        pageSize: _pageSize,
      );
      final notifications = page == 1
          ? result.notifications
          : [...state.notifications, ...result.notifications];
      state = state.copyWith(
        status: NotificationsStatus.loaded,
        notifications: notifications,
        page: page,
        hasMore: notifications.length < result.totalItems,
        isLoadingMore: false,
        clearError: true,
      );
      if (page == 1) {
        _ref.invalidate(unreadNotificationCountProvider);
      }
    } on NotificationException catch (error) {
      state = state.copyWith(
        status: page == 1 ? NotificationsStatus.error : state.status,
        error: error,
        isLoadingMore: false,
      );
    }
  }

  /// Loads the page immediately after the most recently loaded one --
  /// appends to [NotificationsState.notifications] (a no-op if
  /// [NotificationsState.hasMore] is already `false`).
  Future<void> loadMore() => load(page: state.page + 1);

  /// Backs pull-to-refresh -- always resets to page 1, replacing
  /// [NotificationsState.notifications] with a fresh page 1, never
  /// appending to whatever was already loaded.
  Future<void> refresh() => load(page: 1);

  /// Marks one notification read (a row tap, AC6) -- updates it in place
  /// (moving it from New to Earlier on the next render, with no full
  /// reload needed), then refreshes the shared [unreadNotificationCountProvider]
  /// (Plan Frontend item 1 -- "refreshed... after each `markRead` call").
  /// A failure here is silently swallowed from the list's own point of
  /// view -- the screen's own deep-link navigation after tapping a row
  /// proceeds regardless (Decision 10's "tap always deep-links" contract
  /// isn't gated on a successful mark-read).
  Future<void> markRead(String id) async {
    try {
      final updated = await _repository.markRead(id);
      state = state.copyWith(
        notifications: [
          for (final notification in state.notifications)
            if (notification.id == id) updated else notification,
        ],
      );
    } on NotificationException {
      // Best-effort -- see doc above.
    } finally {
      _ref.invalidate(unreadNotificationCountProvider);
    }
  }
}

final notificationsControllerProvider =
    StateNotifierProvider.autoDispose<
      NotificationsController,
      NotificationsState
    >(
      (ref) => NotificationsController(
        ref.watch(notificationRepositoryProvider),
        ref,
      ),
    );
