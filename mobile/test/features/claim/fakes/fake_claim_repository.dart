import 'package:ai_marketplace_app/features/claim/data/claim_repository.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_exception.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_result.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_review_reason.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_search_result.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [ClaimRepository] -- no real Dio/network
/// calls are ever made. Mirrors `fake_search_repository.dart`/
/// `fake_provider_repository.dart`'s pattern.
class FakeClaimRepository extends ClaimRepository {
  FakeClaimRepository({
    List<ClaimSearchResult>? searchResults,
    this.searchUnclaimedError,
    this.requestOtpError,
    this.verifyOtpError,
    this.requestAdminReviewError,
    this.requestOtpExpiresInSeconds = 300,
    this.claimResult,
  }) : _searchResults = searchResults ?? const [],
       super(Dio());

  final List<ClaimSearchResult> _searchResults;

  /// The failure `searchUnclaimed` throws, if any.
  final ClaimException? searchUnclaimedError;

  /// The failure `requestOtp` throws, if any -- e.g.
  /// `ClaimErrorType.publicNumberUnavailable` to exercise AC6's
  /// no-public-number edge case.
  final ClaimException? requestOtpError;

  /// The failure `verifyOtp` throws, if any.
  final ClaimException? verifyOtpError;

  /// The failure `requestAdminReview` throws, if any.
  final ClaimException? requestAdminReviewError;

  /// The `expires_in_seconds` a successful `requestOtp` call returns.
  final int? requestOtpExpiresInSeconds;

  /// The [ClaimResult] a successful `verifyOtp` call returns.
  final ClaimResult? claimResult;

  int searchUnclaimedCallCount = 0;
  int requestOtpCallCount = 0;
  int verifyOtpCallCount = 0;
  int requestAdminReviewCallCount = 0;

  String? lastSearchQuery;
  String? lastRequestOtpProviderId;
  ({String providerId, String code})? lastVerifyOtpArgs;
  ({String providerId, ClaimReviewReason reason})? lastAdminReviewArgs;

  @override
  Future<ClaimSearchResultsPage> searchUnclaimed({
    required String query,
    int page = 1,
    int pageSize = 20,
  }) async {
    searchUnclaimedCallCount++;
    lastSearchQuery = query;
    if (searchUnclaimedError != null) {
      throw searchUnclaimedError!;
    }
    return (
      results: List.of(_searchResults),
      totalItems: _searchResults.length,
    );
  }

  @override
  Future<int?> requestOtp(String providerId) async {
    requestOtpCallCount++;
    lastRequestOtpProviderId = providerId;
    if (requestOtpError != null) {
      throw requestOtpError!;
    }
    return requestOtpExpiresInSeconds;
  }

  @override
  Future<ClaimResult> verifyOtp({
    required String providerId,
    required String code,
  }) async {
    verifyOtpCallCount++;
    lastVerifyOtpArgs = (providerId: providerId, code: code);
    if (verifyOtpError != null) {
      throw verifyOtpError!;
    }
    return claimResult ??
        ClaimResult(
          providerId: providerId,
          isClaimed: true,
          verificationStatus: 'pending',
        );
  }

  @override
  Future<void> requestAdminReview({
    required String providerId,
    required ClaimReviewReason reason,
  }) async {
    requestAdminReviewCallCount++;
    lastAdminReviewArgs = (providerId: providerId, reason: reason);
    if (requestAdminReviewError != null) {
      throw requestAdminReviewError!;
    }
  }
}
