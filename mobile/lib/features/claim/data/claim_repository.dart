import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/claim_exception.dart';
import '../domain/models/claim_result.dart';
import '../domain/models/claim_review_reason.dart';
import '../domain/models/claim_search_result.dart';

/// One page of `GET /claims/search` results, plus the backend's
/// `PaginationMeta.total_items` -- mirrors `search_repository.dart`'s
/// `SearchProvidersPage` record pattern.
typedef ClaimSearchResultsPage = ({
  List<ClaimSearchResult> results,
  int totalItems,
});

/// Wraps the customer-facing claim-flow endpoints (CLM-001,
/// `backend/app/modules/provider/claim_api.py`, mounted at `/claims`).
///
/// Every failure is mapped to a plain-language [ClaimException] -- callers
/// (the state controllers/screens) never see a [DioException], an HTTP
/// status code, or a backend error identifier, following the same
/// convention as `auth_repository.dart`/`provider_repository.dart`.
class ClaimRepository {
  ClaimRepository(this._dio);

  final Dio _dio;

  /// Case-insensitive substring search by business name/address among
  /// still-unclaimed Google-seeded listings only (AC3).
  Future<ClaimSearchResultsPage> searchUnclaimed({
    required String query,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/claims/search',
        queryParameters: {'query': query, 'page': page, 'page_size': pageSize},
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const ClaimException(type: ClaimErrorType.unknown);
      }
      final results = data
          .cast<Map<String, dynamic>>()
          .map(ClaimSearchResult.fromJson)
          .toList();
      final pagination = response.data?['pagination'] as Map<String, dynamic>?;
      final totalItems =
          (pagination?['total_items'] as num?)?.toInt() ?? results.length;
      return (results: results, totalItems: totalItems);
    } on DioException catch (error) {
      throw _mapSearchError(error);
    }
  }

  /// Requests a 6-digit OTP against the **target listing's own stored**
  /// public phone number (AC4) -- there is no phone-number parameter here
  /// or on the underlying endpoint; the number always comes from the
  /// provider row itself, never any caller-supplied value.
  ///
  /// Returns the OTP's `expires_in_seconds`, or `null` if that field is
  /// somehow missing from the response (should be unreachable per the
  /// current contract), mirroring `AuthRepository.requestOtp`'s pattern.
  ///
  /// Throws [ClaimException] with [ClaimErrorType.publicNumberUnavailable]
  /// (never calling anything OTP-related server-side) if the listing has
  /// no public phone number on record at all (AC6).
  Future<int?> requestOtp(String providerId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/claims/$providerId/request-otp',
      );
      final data = response.data?['data'];
      final expiresInSeconds = data is Map<String, dynamic>
          ? data['expires_in_seconds']
          : null;
      return expiresInSeconds is int ? expiresInSeconds : null;
    } on DioException catch (error) {
      throw _mapRequestOtpError(error);
    }
  }

  /// Verifies the submitted OTP code and, only on success, finalizes the
  /// claim (AC5) -- returns the resulting [ClaimResult].
  Future<ClaimResult> verifyOtp({
    required String providerId,
    required String code,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/claims/$providerId/verify-otp',
        data: {'code': code},
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const ClaimException(type: ClaimErrorType.unknown);
      }
      return ClaimResult.fromJson(data);
    } on DioException catch (error) {
      throw _mapVerifyOtpError(error);
    }
  }

  /// AC6's explicit "this isn't working" fallback -- flags the claim
  /// attempt for manual admin review. Called either from the user tapping
  /// a reason on the "This isn't working" sheet, or automatically by
  /// [ClaimOtpController] when [requestOtp] reports
  /// [ClaimErrorType.publicNumberUnavailable].
  Future<void> requestAdminReview({
    required String providerId,
    required ClaimReviewReason reason,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/claims/$providerId/request-admin-review',
        data: {'reason': reason.wireValue},
      );
    } on DioException catch (error) {
      throw _mapAdminReviewError(error);
    }
  }

  ClaimException _mapSearchError(DioException error) {
    if (error.response == null) {
      return const ClaimException(type: ClaimErrorType.network);
    }
    return const ClaimException(type: ClaimErrorType.unknown);
  }

  ClaimException _mapRequestOtpError(DioException error) {
    if (error.response == null) {
      return const ClaimException(type: ClaimErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ClaimException(type: ClaimErrorType.targetNotFound),
      409 => const ClaimException(type: ClaimErrorType.publicNumberUnavailable),
      429 => const ClaimException(type: ClaimErrorType.tooManyAttempts),
      _ => const ClaimException(type: ClaimErrorType.unknown),
    };
  }

  ClaimException _mapVerifyOtpError(DioException error) {
    if (error.response == null) {
      return const ClaimException(type: ClaimErrorType.network);
    }
    return switch (error.response!.statusCode) {
      400 => const ClaimException(type: ClaimErrorType.invalidCode),
      404 => const ClaimException(type: ClaimErrorType.targetNotFound),
      409 => const ClaimException(type: ClaimErrorType.alreadyClaimed),
      429 => const ClaimException(type: ClaimErrorType.tooManyAttempts),
      _ => const ClaimException(type: ClaimErrorType.unknown),
    };
  }

  ClaimException _mapAdminReviewError(DioException error) {
    if (error.response == null) {
      return const ClaimException(type: ClaimErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ClaimException(type: ClaimErrorType.targetNotFound),
      _ => const ClaimException(type: ClaimErrorType.unknown),
    };
  }
}

final claimRepositoryProvider = Provider<ClaimRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ClaimRepository(apiClient.dio);
});
