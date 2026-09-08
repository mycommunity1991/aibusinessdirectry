import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/create_provider_request.dart';
import '../domain/models/portfolio_photo.dart';
import '../domain/models/provider.dart' as domain;
import '../domain/models/provider_exception.dart';
import '../domain/models/update_provider_request.dart';
import '../domain/models/weekday_availability.dart';

/// Wraps `/providers/me` and its PRO-002 sub-resources
/// (`backend/app/modules/provider/api.py`): the storefront singleton
/// itself, portfolio photos, and weekly availability.
///
/// Every failure is mapped to a plain-language [ProviderException] —
/// callers (`ProviderOnboardingController`/`StorefrontController`/the
/// screens) never see a [DioException], an HTTP status code, or a backend
/// error identifier, following the same convention as
/// `saved_address_repository.dart`.
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
      return _parseProviderResponse(response);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      throw _mapCreateOrFetchError(error);
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
      return _parseProviderResponse(response);
    } on DioException catch (error) {
      throw _mapCreateOrFetchError(error);
    }
  }

  /// Partially updates the caller's own storefront (PRO-002, AC5) — only
  /// the fields set on [request] are sent, so a single Storefront section's
  /// Save action never touches another section's fields.
  Future<domain.Provider> updateProvider(UpdateProviderRequest request) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/providers/me',
        data: request.toJson(),
      );
      return _parseProviderResponse(response);
    } on DioException catch (error) {
      throw _mapUpdateProviderError(error);
    }
  }

  /// Lists the caller's own active portfolio photos, ordered by
  /// `sort_order` (PRO-002, AC2).
  Future<List<PortfolioPhoto>> listPortfolio() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/me/portfolio',
      );
      return _parsePortfolioCollection(response);
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  /// Uploads a new portfolio photo (`multipart/form-data`, PRO-002, AC2).
  /// [imageFile]'s own filename is sent only as a hint to the multipart
  /// part -- the server never trusts or reuses it (`06_SECURITY.md`; the
  /// stored filename is always server-generated).
  Future<PortfolioPhoto> uploadPortfolioPhoto(
    File imageFile, {
    String? caption,
  }) async {
    try {
      final fileName = imageFile.uri.pathSegments.isNotEmpty
          ? imageFile.uri.pathSegments.last
          : 'photo';
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          imageFile.path,
          filename: fileName,
        ),
        'caption': ?caption,
      });
      final response = await _dio.post<Map<String, dynamic>>(
        '/providers/me/portfolio',
        data: formData,
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const ProviderException(type: ProviderErrorType.unknown);
      }
      return PortfolioPhoto.fromJson(data);
    } on DioException catch (error) {
      throw _mapUploadError(error);
    }
  }

  /// Soft-deletes one of the caller's own portfolio photos (PRO-002, AC2).
  Future<void> deletePortfolioPhoto(String id) async {
    try {
      await _dio.delete<Map<String, dynamic>>('/providers/me/portfolio/$id');
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  /// Reorders the caller's own active photos (PRO-002, Decision 4) --
  /// [orderedIds] must be exactly the full set of the caller's own active
  /// photo ids, or the backend rejects it (422) before any row is touched.
  Future<List<PortfolioPhoto>> reorderPortfolio(List<String> orderedIds) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/providers/me/portfolio/order',
        data: {'ordered_ids': orderedIds},
      );
      return _parsePortfolioCollection(response);
    } on DioException catch (error) {
      throw _mapReorderError(error);
    }
  }

  /// Returns the caller's weekly availability -- always exactly 7 entries,
  /// one per weekday (PRO-002, AC3, Decision 3).
  Future<List<WeekdayAvailability>> getAvailability() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/me/availability',
      );
      return _parseAvailabilityCollection(response);
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  /// Upserts the caller's weekly availability in one call (PRO-002, AC3,
  /// Decision 3).
  Future<List<WeekdayAvailability>> updateAvailability(
    List<WeekdayAvailability> entries,
  ) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/providers/me/availability',
        data: {'entries': entries.map((entry) => entry.toJson()).toList()},
      );
      return _parseAvailabilityCollection(response);
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  domain.Provider _parseProviderResponse(
    Response<Map<String, dynamic>> response,
  ) {
    final data = response.data?['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw const ProviderException(type: ProviderErrorType.unknown);
    }
    return domain.Provider.fromJson(data);
  }

  List<PortfolioPhoto> _parsePortfolioCollection(
    Response<Map<String, dynamic>> response,
  ) {
    final data = response.data?['data'] as List<dynamic>?;
    if (data == null) {
      throw const ProviderException(type: ProviderErrorType.unknown);
    }
    return data
        .map((item) => PortfolioPhoto.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  List<WeekdayAvailability> _parseAvailabilityCollection(
    Response<Map<String, dynamic>> response,
  ) {
    final data = response.data?['data'] as List<dynamic>?;
    if (data == null) {
      throw const ProviderException(type: ProviderErrorType.unknown);
    }
    return data
        .map(
          (item) => WeekdayAvailability.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

  ProviderException _mapCreateOrFetchError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    if (error.response!.statusCode == 409) {
      return const ProviderException(type: ProviderErrorType.alreadyExists);
    }
    return const ProviderException(type: ProviderErrorType.unknown);
  }

  ProviderException _mapUpdateProviderError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    return switch (error.response!.statusCode) {
      400 => const ProviderException(type: ProviderErrorType.subtypeMismatch),
      404 => const ProviderException(type: ProviderErrorType.notFound),
      422 => const ProviderException(
        type: ProviderErrorType.invalidCategoryLabels,
      ),
      _ => const ProviderException(type: ProviderErrorType.unknown),
    };
  }

  ProviderException _mapUploadError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ProviderException(type: ProviderErrorType.notFound),
      409 => const ProviderException(
        type: ProviderErrorType.portfolioLimitExceeded,
      ),
      422 => const ProviderException(type: ProviderErrorType.invalidUpload),
      _ => const ProviderException(type: ProviderErrorType.unknown),
    };
  }

  ProviderException _mapReorderError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ProviderException(type: ProviderErrorType.notFound),
      422 => const ProviderException(type: ProviderErrorType.invalidReorder),
      _ => const ProviderException(type: ProviderErrorType.unknown),
    };
  }

  ProviderException _mapNotFoundOnlyError(DioException error) {
    if (error.response == null) {
      return const ProviderException(type: ProviderErrorType.network);
    }
    if (error.response!.statusCode == 404) {
      return const ProviderException(type: ProviderErrorType.notFound);
    }
    return const ProviderException(type: ProviderErrorType.unknown);
  }
}

final providerRepositoryProvider = Provider<ProviderRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ProviderRepository(apiClient.dio);
});
