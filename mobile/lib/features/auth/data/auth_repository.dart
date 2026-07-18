import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/auth_exception.dart';
import '../domain/models/auth_token.dart';

/// Wraps the two mobile-OTP auth endpoints
/// (`POST /auth/request-otp`, `POST /auth/verify-otp`).
///
/// Every failure is mapped to a plain-language [AuthException] — callers
/// (state controllers/screens) never see a [DioException], an HTTP status
/// code, or a backend error identifier (AC10, `docs/AI/06_SECURITY.md`).
class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  /// Requests a 6-digit OTP for the given phone number. Always resolves
  /// successfully for a well-formed number — the backend never confirms or
  /// denies whether the number is already registered.
  Future<void> requestOtp({
    required String phoneCountryCode,
    required String phoneNumber,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/request-otp',
        data: {
          'phone_country_code': phoneCountryCode,
          'phone_number': phoneNumber,
        },
      );
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Verifies a 6-digit OTP and returns the resulting [AuthToken]. The
  /// backend transparently creates-or-fetches the user — the client never
  /// needs to know in advance whether this is a registration or a login.
  Future<AuthToken> verifyOtp({
    required String phoneCountryCode,
    required String phoneNumber,
    required String code,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/verify-otp',
        data: {
          'phone_country_code': phoneCountryCode,
          'phone_number': phoneNumber,
          'code': code,
        },
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const AuthException(type: AuthErrorType.unknown);
      }
      return AuthToken.fromJson(data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Maps a Dio failure to a plain-language [AuthException].
  ///
  /// The backend's `request-otp`/`verify-otp` 400/429 responses already
  /// carry a plain-language, non-revealing message (`InvalidOtpError` /
  /// `OtpLockedError` in `backend/app/core/exceptions/exceptions.py`), so
  /// that message is safe to surface directly. Every other status (422
  /// validation, 5xx, or no response at all) maps to a generic, localized,
  /// client-owned message — never the raw status code, an internal error
  /// identifier, or a technical validation string.
  AuthException _mapError(DioException error) {
    final response = error.response;
    if (response == null) {
      return const AuthException(type: AuthErrorType.network);
    }

    final statusCode = response.statusCode;
    final body = response.data;
    final message = body is Map<String, dynamic> && body['message'] is String
        ? body['message'] as String
        : null;

    if (statusCode == 429) {
      return AuthException(
        type: AuthErrorType.tooManyAttempts,
        serverMessage: message,
      );
    }
    if (statusCode == 400) {
      return AuthException(
        type: AuthErrorType.invalidCode,
        serverMessage: message,
      );
    }
    return const AuthException(type: AuthErrorType.unknown);
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient.dio);
});
