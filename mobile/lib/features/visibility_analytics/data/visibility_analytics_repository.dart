import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/visibility_analytics.dart';
import '../domain/models/visibility_analytics_exception.dart';

/// Wraps `GET /providers/me/visibility-analytics` (LEAD-002,
/// `backend/app/modules/contact/provider_visibility_api.py`). Unlike
/// `LeadRepository.listMyLeads`, the response is a single, unwrapped JSON
/// object (Decision 3) -- there is no `data`/`pagination` envelope to
/// unwrap.
///
/// Every failure is mapped to a plain-language [VisibilityAnalyticsException]
/// -- callers (`VisibilityAnalyticsController`/`VisibilityAnalyticsScreen`)
/// never see a [DioException], an HTTP status code, or a backend error
/// identifier, following the same convention as `lead_repository.dart`.
class VisibilityAnalyticsRepository {
  VisibilityAnalyticsRepository(this._dio);

  final Dio _dio;

  /// Fetches the caller's own visibility analytics -- ownership is enforced
  /// entirely server-side (AC3); this method never accepts or sends a
  /// provider id.
  Future<VisibilityAnalytics> getMyVisibilityAnalytics() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/me/visibility-analytics',
      );
      final data = response.data;
      if (data == null) {
        throw const VisibilityAnalyticsException(
          type: VisibilityAnalyticsErrorType.unknown,
        );
      }
      return VisibilityAnalytics.fromJson(data);
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  VisibilityAnalyticsException _mapNotFoundOnlyError(DioException error) {
    if (error.response == null) {
      return const VisibilityAnalyticsException(
        type: VisibilityAnalyticsErrorType.network,
      );
    }
    if (error.response!.statusCode == 404) {
      return const VisibilityAnalyticsException(
        type: VisibilityAnalyticsErrorType.notFound,
      );
    }
    return const VisibilityAnalyticsException(
      type: VisibilityAnalyticsErrorType.unknown,
    );
  }
}

final visibilityAnalyticsRepositoryProvider =
    Provider<VisibilityAnalyticsRepository>((ref) {
      final apiClient = ref.watch(apiClientProvider);
      return VisibilityAnalyticsRepository(apiClient.dio);
    });
