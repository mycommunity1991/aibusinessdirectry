import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/contact_exception.dart';
import '../domain/models/contact_reveal.dart';
import '../domain/models/provider_profile.dart';
import '../domain/models/provider_profile_exception.dart';

/// Wraps the Provider Profile screen's (S-09) and Contact Reveal sheet's
/// two backend endpoints (CON-001): `GET /providers/{provider_id}`
/// (`backend/app/modules/provider/public_api.py`) and
/// `POST /contact-views` (`backend/app/modules/contact/api.py`).
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
}

final providerProfileRepositoryProvider = Provider<ProviderProfileRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return ProviderProfileRepository(apiClient.dio);
});
