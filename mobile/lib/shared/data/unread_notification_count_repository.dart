import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';

/// A minimal, shared read of the caller's own unread notification count
/// from `GET /notifications/unread-count`
/// (`backend/app/modules/notification/api.py`, `ENG-001`, AC5) --
/// deliberately independent of `features/notifications/`'s full
/// `NotificationRepository`/`NotificationItem` model, mirroring
/// `verification_status_summary_repository.dart`'s exact "minimal, shared,
/// deliberately-independent read" shape (`docs/AI/02_ARCHITECTURE.md`:
/// "Features must not depend directly on each other. Shared functionality
/// belongs in shared modules.").
///
/// Any feature that only needs the coarse unread-count badge -- not the
/// full Inbox list -- should depend on this instead of importing
/// `features/notifications/`. Today, `features/home/`'s Notifications
/// entry-point tile is the only such consumer.
class UnreadNotificationCountRepository {
  UnreadNotificationCountRepository(this._dio);

  final Dio _dio;

  /// Returns the caller's current unread notification count, or `0` on any
  /// failure -- a badge count is inherently best-effort, non-critical
  /// information; a transient error here should never block or clutter the
  /// Home screen with an error state for a stray count.
  Future<int> getUnreadCount() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/notifications/unread-count',
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      return (data?['count'] as num?)?.toInt() ?? 0;
    } on DioException {
      return 0;
    }
  }
}

final unreadNotificationCountRepositoryProvider =
    Provider<UnreadNotificationCountRepository>((ref) {
      final apiClient = ref.watch(apiClientProvider);
      return UnreadNotificationCountRepository(apiClient.dio);
    });

/// Loads the caller's own unread notification count for the Home
/// placeholder's Notifications entry-point badge -- an `autoDispose`
/// `FutureProvider` since this is a one-shot read with no need to persist
/// state once the screen reading it is gone, mirroring
/// `verificationStatusSummaryProvider`'s identical shape.
final unreadNotificationCountProvider = FutureProvider.autoDispose<int>((ref) {
  return ref.watch(unreadNotificationCountRepositoryProvider).getUnreadCount();
});
