import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/contact_exception.dart';
import '../domain/models/contact_reveal.dart';
import '../domain/models/outcome_tag.dart';
import '../domain/models/outcome_tag_exception.dart';
import '../domain/models/provider_profile.dart';
import '../domain/models/provider_profile_exception.dart';
import '../domain/models/review.dart';
import '../domain/models/review_exception.dart';

/// Wraps the Provider Profile screen's (S-09), Contact Reveal sheet's,
/// Outcome Tag Prompt sheet's, and Write-a-Review screen's backend
/// endpoints (CON-001/REV-001/REV-002):
/// `GET /providers/{provider_id}`
/// (`backend/app/modules/provider/public_api.py`),
/// `POST /contact-views`,
/// `POST /contact-views/{contact_view_id}/outcome-tag`
/// (`backend/app/modules/contact/api.py`), and
/// `POST /contact-views/{contact_view_id}/review`
/// (`backend/app/modules/review/api.py`).
///
/// Every failure is mapped to a plain-language exception -- callers (the
/// state controllers/screens) never see a [DioException], an HTTP status
/// code, or a backend error identifier, following the same convention as
/// `claim_repository.dart`/`search_repository.dart`.
class ProviderProfileRepository {
  ProviderProfileRepository(this._dio);

  final Dio _dio;

  /// `GET /providers/{provider_id}` (AC5) -- deliberately does **not**
  /// return a phone/WhatsApp number; those only ever come from
  /// [createContactView].
  Future<ProviderProfile> getProviderProfile(String providerId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/$providerId',
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const ProviderProfileException(
          type: ProviderProfileErrorType.unknown,
        );
      }
      return ProviderProfile.fromJson(data);
    } on DioException catch (error) {
      throw _mapProfileError(error);
    }
  }

  /// `POST /contact-views` (AC2/AC3/AC4) -- creates a Contact View and
  /// immediately reveals the target provider's phone number. [searchRequestId]
  /// is omitted from the request body entirely when `null` (the structured
  /// search path, Decision 4), never sent as a literal JSON `null`.
  Future<ContactReveal> createContactView({
    required String providerId,
    String? searchRequestId,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/contact-views',
        data: {
          'provider_id': providerId,
          'search_request_id': ?searchRequestId,
        },
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const ContactException(type: ContactErrorType.unknown);
      }
      return ContactReveal.fromJson(data);
    } on DioException catch (error) {
      throw _mapContactError(error);
    }
  }

  /// `POST /contact-views/{contact_view_id}/outcome-tag` (REV-001, AC1) --
  /// records a minimal yes/no "did you hire them?" signal against a
  /// specific Contact View. Carries no payment amount, job-completion
  /// detail, or scheduling information (AC4).
  Future<OutcomeTag> submitOutcomeTag({
    required String contactViewId,
    required bool hired,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/contact-views/$contactViewId/outcome-tag',
        data: {'hired': hired},
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const OutcomeTagException(type: OutcomeTagErrorType.unknown);
      }
      return OutcomeTag.fromJson(data);
    } on DioException catch (error) {
      throw _mapOutcomeTagError(error);
    }
  }

  /// `POST /contact-views/{contact_view_id}/review` (REV-002, AC1) --
  /// rates the provider after a confirmed ('Yes') hire outcome. [comment]
  /// is omitted from the request body entirely when `null`, never sent as
  /// a literal JSON `null` (mirrors [createContactView]'s
  /// `search_request_id` handling).
  Future<Review> submitReview({
    required String contactViewId,
    required int rating,
    String? comment,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/contact-views/$contactViewId/review',
        data: {'rating': rating, 'comment': ?comment},
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const ReviewException(type: ReviewErrorType.unknown);
      }
      return Review.fromJson(data);
    } on DioException catch (error) {
      throw _mapReviewError(error);
    }
  }

  ProviderProfileException _mapProfileError(DioException error) {
    if (error.response == null) {
      return const ProviderProfileException(
        type: ProviderProfileErrorType.network,
      );
    }
    return switch (error.response!.statusCode) {
      404 => const ProviderProfileException(
        type: ProviderProfileErrorType.notFound,
      ),
      _ => const ProviderProfileException(
        type: ProviderProfileErrorType.unknown,
      ),
    };
  }

  ContactException _mapContactError(DioException error) {
    if (error.response == null) {
      return const ContactException(type: ContactErrorType.network);
    }
    return switch (error.response!.statusCode) {
      403 => const ContactException(type: ContactErrorType.selfDealing),
      404 => const ContactException(type: ContactErrorType.notFound),
      _ => const ContactException(type: ContactErrorType.unknown),
    };
  }

  OutcomeTagException _mapOutcomeTagError(DioException error) {
    if (error.response == null) {
      return const OutcomeTagException(type: OutcomeTagErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const OutcomeTagException(type: OutcomeTagErrorType.notFound),
      409 => const OutcomeTagException(type: OutcomeTagErrorType.alreadyExists),
      _ => const OutcomeTagException(type: OutcomeTagErrorType.unknown),
    };
  }

  /// `POST .../review` has two distinct 409 causes (Decision 5,
  /// `Plan_S09_REV-002.md`): `ReviewAnchorNotVerifiedError` and
  /// `ReviewAlreadyExistsError`. The backend's `ErrorResponse` body carries
  /// only `{success, message, errors}` -- no structured error identifier
  /// (`backend/app/shared/schemas/response.py`) -- so the two can't be
  /// told apart over the wire without parsing the raw `message` string,
  /// which `docs/AI/06_SECURITY.md`'s "never surface/rely on the backend's
  /// raw message" convention (already followed by every other repository
  /// in this codebase) rules out. Both are collapsed into
  /// [ReviewErrorType.anchorNotVerified] here -- functionally low-stakes in
  /// practice, since [WriteReviewScreen] shows the same plain-language
  /// inline error (with no type-specific copy or retry semantics) for every
  /// failure type, unlike [OutcomeTagPromptSheet]'s own quiet-close
  /// treatment of its 404/409 cases -- a full-screen form the customer just
  /// filled in deserves explicit feedback rather than silently closing.
  /// [ReviewErrorType.alreadyExists] is kept in the domain model for
  /// documentation/forward-compatibility (Decision 5's taxonomy), should the
  /// backend ever add a distinguishing field.
  ReviewException _mapReviewError(DioException error) {
    if (error.response == null) {
      return const ReviewException(type: ReviewErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ReviewException(type: ReviewErrorType.notFound),
      409 => const ReviewException(type: ReviewErrorType.anchorNotVerified),
      _ => const ReviewException(type: ReviewErrorType.unknown),
    };
  }
}

final providerProfileRepositoryProvider = Provider<ProviderProfileRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return ProviderProfileRepository(apiClient.dio);
});
