import 'package:ai_marketplace_app/features/notifications/data/notification_repository.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_exception.dart';
import 'package:ai_marketplace_app/features/notifications/domain/models/notification_item.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [NotificationRepository] -- no real Dio/
/// network calls are ever made. Mirrors `fake_lead_repository.dart`'s
/// pattern.
///
/// [pages] lets a test pre-seed more than one page of notifications -- page
/// `n` (1-indexed) is served from `pages[n - 1]`, and [totalItems] defaults
/// to the flattened total across every page supplied so `hasMore` derives
/// correctly without a test having to compute it by hand.
///
/// [unreadCounts] lets a test observe [getUnreadCount] being called more
/// than once with different results over time (e.g. before/after a
/// `markRead` call) -- call `n` (1-indexed) returns `unreadCounts[n - 1]`,
/// clamped to the last entry once exhausted.
class FakeNotificationRepository extends NotificationRepository {
  FakeNotificationRepository({
    List<List<NotificationItem>>? pages,
    int? totalItems,
    this.listNotificationsError,
    List<int>? unreadCounts,
    this.getUnreadCountError,
    this.markReadResult,
    this.markReadError,
  }) : _pages = pages ?? const [[]],
       _totalItems =
           totalItems ??
           (pages ?? const [[]]).fold(0, (sum, page) => sum + page.length),
       _unreadCounts = unreadCounts ?? const [0],
       super(Dio());

  final List<List<NotificationItem>> _pages;
  final int _totalItems;
  final List<int> _unreadCounts;

  /// The failure `listNotifications` throws, if any.
  final NotificationException? listNotificationsError;

  /// The failure `getUnreadCount` throws, if any.
  final NotificationException? getUnreadCountError;

  /// The row `markRead` returns on success, if not overridden per-call via
  /// [lastMarkReadId] lookups by the test itself.
  final NotificationItem? markReadResult;

  /// The failure `markRead` throws, if any.
  final NotificationException? markReadError;

  int listNotificationsCallCount = 0;
  int getUnreadCountCallCount = 0;
  int markReadCallCount = 0;

  /// The exact arguments passed to the most recent `listNotifications` call.
  ({int page, int pageSize})? lastArgs;

  /// The exact id passed to the most recent `markRead` call.
  String? lastMarkReadId;

  @override
  Future<NotificationsPage> listNotifications({
    int page = 1,
    int pageSize = 20,
  }) async {
    listNotificationsCallCount++;
    lastArgs = (page: page, pageSize: pageSize);
    if (listNotificationsError != null) {
      throw listNotificationsError!;
    }
    final notifications = page >= 1 && page <= _pages.length
        ? _pages[page - 1]
        : <NotificationItem>[];
    return (notifications: List.of(notifications), totalItems: _totalItems);
  }

  @override
  Future<int> getUnreadCount() async {
    getUnreadCountCallCount++;
    if (getUnreadCountError != null) {
      throw getUnreadCountError!;
    }
    final index = (getUnreadCountCallCount - 1).clamp(
      0,
      _unreadCounts.length - 1,
    );
    return _unreadCounts[index];
  }

  @override
  Future<NotificationItem> markRead(String id) async {
    markReadCallCount++;
    lastMarkReadId = id;
    if (markReadError != null) {
      throw markReadError!;
    }
    return markReadResult ??
        NotificationItem(
          id: id,
          type: 'new_contact_view',
          title: 'title',
          body: 'body',
          readAt: DateTime.utc(2026, 1, 1),
          createdAt: DateTime.utc(2026, 1, 1),
        );
  }
}
