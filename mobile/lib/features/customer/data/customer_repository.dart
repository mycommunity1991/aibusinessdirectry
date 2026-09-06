import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/customer_profile.dart';
import '../domain/models/customer_profile_exception.dart';

/// Wraps `GET`/`PATCH /customers/me` (CUS-001,
/// `backend/app/modules/customer/api.py`).
///
/// Every failure is mapped to a plain-language [CustomerProfileException] —
/// callers (the state controller/screen) never see a [DioException], an
/// HTTP status code, or a backend error identifier, following the same
/// convention as `features/auth/data/auth_repository.dart`.
class CustomerRepository {
  CustomerRepository(this._dio);

  final Dio _dio;

  /// Returns the caller's own customer profile and preferences. Never 404s
  /// for an authenticated `customer`-role caller — the backend lazily
  /// provisions a default profile for any pre-CUS-001 account on first
  /// access (`Plan_S03_CUS-001.md` Decision 4).
  Future<CustomerProfile> getMyProfile() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/customers/me');
      return _parseResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Partially updates the caller's own profile/preferences — only the
  /// fields passed here are sent, matching the backend's
  /// `exclude_unset=True` partial-update semantics. Pass [clearAvatarUrl]
  /// to explicitly clear a previously-set avatar (sends `avatar_url: null`)
  /// rather than leaving it untouched.
  Future<CustomerProfile> updateMyProfile({
    String? displayName,
    String? avatarUrl,
    bool clearAvatarUrl = false,
    String? language,
    NotificationChannel? notificationChannel,
  }) async {
    final payload = <String, dynamic>{
      'display_name': ?displayName,
      if (avatarUrl != null || clearAvatarUrl) 'avatar_url': avatarUrl,
      'language': ?language,
      if (notificationChannel != null)
        'notification_channel': notificationChannel.wireValue,
    };
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/customers/me',
        data: payload,
      );
      return _parseResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  CustomerProfile _parseResponse(Response<Map<String, dynamic>> response) {
    final data = response.data?['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw const CustomerProfileException(
        type: CustomerProfileErrorType.unknown,
      );
    }
    return CustomerProfile.fromJson(data);
  }

  CustomerProfileException _mapError(DioException error) {
    if (error.response == null) {
      return const CustomerProfileException(
        type: CustomerProfileErrorType.network,
      );
    }
    return const CustomerProfileException(
      type: CustomerProfileErrorType.unknown,
    );
  }
}

final customerRepositoryProvider = Provider<CustomerRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CustomerRepository(apiClient.dio);
});
