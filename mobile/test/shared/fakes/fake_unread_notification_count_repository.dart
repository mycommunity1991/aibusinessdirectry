import 'package:ai_marketplace_app/shared/data/unread_notification_count_repository.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [UnreadNotificationCountRepository] -- no
/// real Dio/network calls are ever made. Mirrors
/// `fake_verification_status_summary_repository.dart`'s pattern.
///
/// [counts] lets a test observe [getUnreadCount] being called more than
/// once with different results over time (e.g. before/after a `markRead`
/// call, `ENG-001`) -- call `n` (1-indexed) returns `counts[n - 1]`,
/// clamped to the last entry once exhausted. Defaults to always returning
/// [count] for every call.
class FakeUnreadNotificationCountRepository
    extends UnreadNotificationCountRepository {
  FakeUnreadNotificationCountRepository({int count = 0, List<int>? counts})
    : _counts = counts ?? [count],
      super(Dio());

  final List<int> _counts;

  int getUnreadCountCallCount = 0;

  @override
  Future<int> getUnreadCount() async {
    getUnreadCountCallCount++;
    final index = (getUnreadCountCallCount - 1).clamp(0, _counts.length - 1);
    return _counts[index];
  }
}
