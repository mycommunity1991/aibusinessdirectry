import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/search_repository.dart';
import '../domain/models/search_exception.dart';
import '../domain/models/search_filters_args.dart';
import '../domain/models/search_result_provider.dart';

/// The Search Results screen's (S-08, `Plan_S06_DIR-001.md` Decision 6/7)
/// status -- deliberately distinguishes "no search has been performed yet"
/// ([idle]) from "a search ran and returned zero results" ([loaded] with an
/// empty [SearchResultsState.results]), per AC4/Decision 7. The two states
/// must never share the same rendered copy (see `search_results_screen.dart`).
enum SearchResultsStatus { idle, loading, loaded, error }

class SearchResultsState {
  const SearchResultsState({
    this.status = SearchResultsStatus.idle,
    this.results = const [],
    this.error,
  });

  final SearchResultsStatus status;
  final List<SearchResultProvider> results;
  final SearchException? error;

  SearchResultsState copyWith({
    SearchResultsStatus? status,
    List<SearchResultProvider>? results,
    SearchException? error,
    bool clearError = false,
  }) {
    return SearchResultsState(
      status: status ?? this.status,
      results: results ?? this.results,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Runs `GET /search/providers` for a given [SearchFiltersArgs] (AC2/AC3),
/// starting from [SearchResultsStatus.idle] -- the Search Results screen
/// itself decides when to call [search] (immediately, if reached with
/// filters already chosen; never, if reached with none -- Decision 7's
/// pre-search state).
class SearchResultsController extends StateNotifier<SearchResultsState> {
  SearchResultsController(this._repository) : super(const SearchResultsState());

  final SearchRepository _repository;

  Future<void> search(SearchFiltersArgs args) async {
    state = state.copyWith(
      status: SearchResultsStatus.loading,
      clearError: true,
    );
    try {
      final page = await _repository.searchProviders(
        category: args.category,
        latitude: args.latitude,
        longitude: args.longitude,
        radiusKm: args.radiusKm,
      );
      state = state.copyWith(
        status: SearchResultsStatus.loaded,
        results: page.results,
      );
    } on SearchException catch (error) {
      state = state.copyWith(status: SearchResultsStatus.error, error: error);
    }
  }
}

final searchResultsControllerProvider =
    StateNotifierProvider.autoDispose<
      SearchResultsController,
      SearchResultsState
    >((ref) => SearchResultsController(ref.watch(searchRepositoryProvider)));
