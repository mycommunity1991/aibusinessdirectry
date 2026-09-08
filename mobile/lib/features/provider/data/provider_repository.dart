import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/create_provider_request.dart';
import '../domain/models/provider.dart' as domain;
import '../domain/models/provider_exception.dart';

/// Wraps `GET`/`POST /providers/me` (PRO-001,
/// `backend/app/modules/provider/api.py`).
///
/// Every failure is mapped to a plain-language [ProviderException] —
/// callers (`ProviderOnboardingController`/the screens) never see a
/// [DioException], an HTTP status code, or a backend error identifier,
/// following the same convention as `saved_address_repository.dart`.
class ProviderRepository {
  ProviderRepository(this._dio);

  final Dio _dio;

  /// Returns the caller's own provider listing, or `null` if they don't
  /// have one yet (backend 404 `ProviderNotFoundError`) — mirrors how
  /// `SavedAddressRepository` treats "not found" as a normal, expected
  /// state rather than an exception (Decision 9, `Plan_S04_PRO-001.md`).
  Future<domain.Provider?> getMyProvider() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/providers/me');
      return _parseResponse(response);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      throw _mapError(error);
    }
  }

  /// Creates the caller's provider listing (AC1-AC7) — the onboarding
  /// wizard's single, end-of-flow submission (Decision 2,
  /// `Plan_S04_PRO-001.md`).
  Future<domain.Provider> createProvider(CreateProviderRequest request) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/providers/me',
        data: request.toJson(),
      );
      return _parseResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  domain.Provider _parseResponse(Response<Map<String, dynamic>> response) {
    final data = response.data?['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw const ProviderException(type: ProviderErrorType.unknown);
    }
    return domain.Provider.fromJson(data);
  }

  ProviderException _mapError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    if (error.response!.statusCode == 409) {
      return const ProviderException(type: ProviderErrorType.alreadyExists);
    }
    return const ProviderException(type: ProviderErrorType.unknown);
  }
}

final providerRepositoryProvider = Provider<ProviderRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ProviderRepository(apiClient.dio);
});
