import 'package:ai_marketplace_app/features/search/data/search_repository.dart';
import 'package:ai_marketplace_app/features/search/domain/models/category_option.dart';
import 'package:ai_marketplace_app/features/search/domain/models/search_exception.dart';
import 'package:ai_marketplace_app/features/search/domain/models/search_result_provider.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [SearchRepository] -- no real Dio/network
/// calls are ever made. Mirrors `fake_provider_repository.dart`/
/// `fake_saved_address_repository.dart`'s pattern.
class FakeSearchRepository extends SearchRepository {
  FakeSearchRepository({
    List<CategoryOption>? categories,
    List<SearchResultProvider>? results,
    this.searchProvidersError,
    this.listCategoriesError,
  }) : _categories = categories ?? const [],
       _results = results ?? const [],
       super(Dio());

  final List<CategoryOption> _categories;
  final List<SearchResultProvider> _results;

  /// The failure `searchProviders` throws, if any.
  final SearchException? searchProvidersError;

  /// The failure `listCategories` throws, if any.
  final SearchException? listCategoriesError;

  int searchProvidersCallCount = 0;
  int listCategoriesCallCount = 0;

  /// The exact arguments passed to the most recent `searchProviders` call
  /// -- lets a test assert precisely what filters were submitted.
  ({
    String? category,
    double latitude,
    double longitude,
    double radiusKm,
    int page,
    int pageSize,
  })?
  lastSearchArgs;

  @override
  Future<SearchProvidersPage> searchProviders({
    String? category,
    required double latitude,
    required double longitude,
    required double radiusKm,
    int page = 1,
    int pageSize = 20,
  }) async {
    searchProvidersCallCount++;
    lastSearchArgs = (
      category: category,
      latitude: latitude,
      longitude: longitude,
      radiusKm: radiusKm,
      page: page,
      pageSize: pageSize,
    );
    if (searchProvidersError != null) {
      throw searchProvidersError!;
    }
    return (results: List.of(_results), totalItems: _results.length);
  }

  @override
  Future<List<CategoryOption>> listCategories() async {
    listCategoriesCallCount++;
    if (listCategoriesError != null) {
      throw listCategoriesError!;
    }
    return List.of(_categories);
  }
}
