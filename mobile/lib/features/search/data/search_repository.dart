import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/category_option.dart';
import '../domain/models/search_exception.dart';
import '../domain/models/search_result_provider.dart';

/// One page of `GET /search/providers` results, plus the backend's
/// `PaginationMeta.total_items` -- a plain record (mirrors
/// `AddressFormArgs`/`OtpEntryArgs`'s typedef-record pattern) rather than a
/// new named class, since it carries nothing beyond these two values.
typedef SearchProvidersPage = ({
  List<SearchResultProvider> results,
  int totalItems,
});

/// Wraps `GET /search/providers` and `GET /search/categories` (DIR-001,
/// `backend/app/modules/search/api.py`).
///
/// Every failure is mapped to a plain-language [SearchException] -- callers
/// (the state controllers/screens) never see a [DioException], an HTTP
/// status code, or a backend error identifier, following the same
/// convention as `provider_repository.dart`/`saved_address_repository.dart`.
class SearchRepository {
  SearchRepository(this._dio);

  final Dio _dio;

  /// Browses `is_discoverable=true` providers by optional [category] and
  /// geospatial radius around ([latitude], [longitude]) (AC2/AC3). Results
  /// are ordered nearest-first by the backend -- this method never
  /// re-sorts them.
  Future<SearchProvidersPage> searchProviders({
    String? category,
    required double latitude,
    required double longitude,
    required double radiusKm,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/search/providers',
        queryParameters: {
          'latitude': latitude,
          'longitude': longitude,
          'radius_km': radiusKm,
          'page': page,
          'page_size': pageSize,
          'category': ?category,
        },
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const SearchException(type: SearchErrorType.unknown);
      }
      final results = data
          .cast<Map<String, dynamic>>()
          .map(SearchResultProvider.fromJson)
          .toList();
      final pagination = response.data?['pagination'] as Map<String, dynamic>?;
      final totalItems =
          (pagination?['total_items'] as num?)?.toInt() ?? results.length;
      return (results: results, totalItems: totalItems);
    } on DioException catch (error) {
      throw _mapSearchError(error);
    }
  }

  /// Returns the distinct set of category labels in use by discoverable
  /// providers (Decision 1) -- backs the Search Filters screen's category
  /// chip picker. Deliberately unpaginated, mirroring the backend's own
  /// ADR-012-style exception.
  Future<List<CategoryOption>> listCategories() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/search/categories',
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const SearchException(type: SearchErrorType.unknown);
      }
      return data
          .cast<Map<String, dynamic>>()
          .map(CategoryOption.fromJson)
          .toList();
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  SearchException _mapSearchError(DioException error) {
    if (error.response == null) {
      return const SearchException(type: SearchErrorType.network);
    }
    if (error.response!.statusCode == 422) {
      return const SearchException(type: SearchErrorType.invalidRadius);
    }
    return const SearchException(type: SearchErrorType.unknown);
  }

  SearchException _mapError(DioException error) {
    if (error.response == null) {
      return const SearchException(type: SearchErrorType.network);
    }
    return const SearchException(type: SearchErrorType.unknown);
  }
}

final searchRepositoryProvider = Provider<SearchRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SearchRepository(apiClient.dio);
});
