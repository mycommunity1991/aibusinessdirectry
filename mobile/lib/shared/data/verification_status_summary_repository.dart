import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../models/verification_status_summary.dart';

/// A minimal, shared read of the caller's own verification status from
/// `GET /providers/me/verification`
/// (`backend/app/modules/verification/api.py`) -- deliberately
/// independent of `features/verification/`'s full `VerificationRepository`/
/// `VerificationRecord` model (`docs/AI/02_ARCHITECTURE.md`: "Features
/// must not depend directly on each other. Shared functionality belongs
/// in shared modules.").
///
/// Any feature that only needs a coarse status-chip/badge summary -- not
/// the full record (rejection reason, documents, timestamps) -- should
/// depend on this instead of importing `features/verification/`.
class VerificationStatusSummaryRepository {
  VerificationStatusSummaryRepository(this._dio);

  final Dio _dio;

  /// Returns the caller's own current [VerificationStatusSummary], or
  /// `null` if they've never submitted (backend 404) -- mirrors
  /// `VerificationRepository.getMyCurrentStatus()`'s null-on-404
  /// convention: "not yet submitted" is a normal state here, not a
  /// failure.
  Future<VerificationStatusSummary?> getMyVerificationStatusSummary() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/me/verification',
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      final wireValue = data?['status'] as String?;
      return switch (wireValue) {
        'pending' || 'under_review' => VerificationStatusSummary.underReview,
        'approved' => VerificationStatusSummary.approved,
        'rejected' => VerificationStatusSummary.rejected,
        _ => null,
      };
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      return null;
    }
  }
}

final verificationStatusSummaryRepositoryProvider =
    Provider<VerificationStatusSummaryRepository>((ref) {
      final apiClient = ref.watch(apiClientProvider);
      return VerificationStatusSummaryRepository(apiClient.dio);
    });

/// Loads the caller's own [VerificationStatusSummary] for the Storefront's
/// verification-status chip -- an `autoDispose` `FutureProvider` since
/// this is a one-shot read with no need to persist state once the
/// Storefront screen is gone.
final verificationStatusSummaryProvider =
    FutureProvider.autoDispose<VerificationStatusSummary?>((ref) {
      return ref
          .watch(verificationStatusSummaryRepositoryProvider)
          .getMyVerificationStatusSummary();
    });
