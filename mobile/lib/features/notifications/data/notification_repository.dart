import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/notification_exception.dart';
import '../domain/models/notification_item.dart';

/// One page of `GET /notifications` results, plus the backend's
/// `PaginationMeta.total_items` -- a plain record (mirrors `LeadsPage`'s own
/// typedef-record pattern, `features/leads/data/lead_repository.dart`)
/// rather than a new named class, since it carries nothing beyond these two
/// values.
typedef NotificationsPage = ({
  List<NotificationItem> notifications,
  int totalItems,
});

/// Wraps `GET /notifications`, `GET /notifications/unread-count`, and
/// `PATCH /notifications/{id}/read` (`ENG-001`, Decision 10,
/// `backend/app/modules/notification/api.py`).
///
/// Every failure is mapped to a plain-language [NotificationException] --
/// callers (`NotificationsController`/`NotificationsInboxScreen`) never see
/// a [DioException], an HTTP status code, or a backend error identifier,
/// following the same convention as `lead_repository.dart`/
/// `visibility_analytics_repository.dart`.
class NotificationRepository {
  NotificationRepository(this._dio);

  final Dio _dio;

  /// Lists the caller's own notifications, newest first (AC6) -- ownership
  /// is enforced entirely server-side; this method never accepts or sends a
  /// user id.
  Future<NotificationsPage> listNotifications({
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/notifications',
        queryParameters: {'page': page, 'page_size': pageSize},
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const NotificationException(type: NotificationErrorType.unknown);
      }
      final notifications = data
          .cast<Map<String, dynamic>>()
          .map(NotificationItem.fromJson)
          .toList();
      final pagination = response.data?['pagination'] as Map<String, dynamic>?;
      final totalItems =
          (pagination?['total_items'] as num?)?.toInt() ?? notifications.length;
      return (notifications: notifications, totalItems: totalItems);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Returns the caller's current unread notification count (AC5's
  /// "badge").
  Future<int> getUnreadCount() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/notifications/unread-count',
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      final count = (data?['count'] as num?)?.toInt();
      if (count == null) {
        throw const NotificationException(type: NotificationErrorType.unknown);
      }
      return count;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Marks one notification read, returning the updated row (AC6) --
  /// idempotent on the backend, so calling this twice for an already-read
  /// row is a harmless no-op.
  Future<NotificationItem> markRead(String id) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/notifications/$id/read',
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const NotificationException(type: NotificationErrorType.unknown);
      }
      return NotificationItem.fromJson(data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  NotificationException _mapError(DioException error) {
    if (error.response == null) {
      return const NotificationException(type: NotificationErrorType.network);
    }
    return const NotificationException(type: NotificationErrorType.unknown);
  }
}

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return NotificationRepository(apiClient.dio);
});
