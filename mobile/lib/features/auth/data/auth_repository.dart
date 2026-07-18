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
  ///
  /// Returns the OTP's `expires_in_seconds` from the response
  /// (`RequestOtpResponse` — `backend/app/modules/identity/schemas.py`), so
  /// callers can size a resend countdown from the real server value (FU-2).
  /// Returns `null` only if that field is somehow missing from the response
  /// — a should-be-unreachable, defensive case per the current contract.
  Future<int?> requestOtp({
    required String phoneCountryCode,
    required String phoneNumber,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/request-otp',
        data: {
          'phone_country_code': phoneCountryCode,
          'phone_number': phoneNumber,
        },
      );
      final data = response.data?['data'];
      final expiresInSeconds = data is Map<String, dynamic>
          ? data['expires_in_seconds']
          : null;
      return expiresInSeconds is int ? expiresInSeconds : null;
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
  /// Only [AuthErrorType] is carried across — never the backend's raw
  /// `message` string, an HTTP status code, or an internal error
  /// identifier. Every type is rendered from client-owned, localized copy
  /// (`auth_error_copy.dart`, FU-3). A 429 always maps to
  /// [AuthErrorType.tooManyAttempts]: it covers both `OtpLockedError`
  /// (too many wrong attempts) and `RateLimitExceededError` (too many
  /// requests) — see [AuthErrorType.tooManyAttempts] for why they're not
  /// distinguished further.
  AuthException _mapError(DioException error) {
    final response = error.response;
    if (response == null) {
      return const AuthException(type: AuthErrorType.network);
    }

    final statusCode = response.statusCode;
    if (statusCode == 429) {
      return const AuthException(type: AuthErrorType.tooManyAttempts);
    }
    if (statusCode == 400) {
      return const AuthException(type: AuthErrorType.invalidCode);
    }
    return const AuthException(type: AuthErrorType.unknown);
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient.dio);
});
