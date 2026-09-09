import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/claim_repository.dart';
import '../domain/models/claim_exception.dart';
import '../domain/models/claim_search_result.dart';

/// The Claim Search screen's (S-21, CLM-001, AC3) status -- distinguishes
/// "no search has been performed yet" ([idle]) from "a search ran and
/// returned zero results" ([loaded] with an empty
/// [ClaimSearchState.results]), mirroring `SearchResultsController`'s
/// identical idle-vs-empty distinction.
enum ClaimSearchStatus { idle, loading, loaded, error }

class ClaimSearchState {
  const ClaimSearchState({
    this.status = ClaimSearchStatus.idle,
    this.results = const [],
    this.error,
  });

  final ClaimSearchStatus status;
  final List<ClaimSearchResult> results;
  final ClaimException? error;

  ClaimSearchState copyWith({
    ClaimSearchStatus? status,
    List<ClaimSearchResult>? results,
    ClaimException? error,
    bool clearError = false,
  }) {
    return ClaimSearchState(
      status: status ?? this.status,
      results: results ?? this.results,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Runs `GET /claims/search` for a given free-text [query] (AC3), starting
/// from [ClaimSearchStatus.idle] -- the screen itself decides when to call
/// [search] (on the user submitting the search field), mirroring
/// `SearchResultsController`'s own screen-driven trigger.
class ClaimSearchController extends StateNotifier<ClaimSearchState> {
  ClaimSearchController(this._repository) : super(const ClaimSearchState());

  final ClaimRepository _repository;

  Future<void> search(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      state = const ClaimSearchState();
      return;
    }
    state = state.copyWith(status: ClaimSearchStatus.loading, clearError: true);
    try {
      final page = await _repository.searchUnclaimed(query: trimmed);
      state = state.copyWith(
        status: ClaimSearchStatus.loaded,
        results: page.results,
      );
    } on ClaimException catch (error) {
      state = state.copyWith(status: ClaimSearchStatus.error, error: error);
    }
  }
}

final claimSearchControllerProvider =
    StateNotifierProvider.autoDispose<ClaimSearchController, ClaimSearchState>(
      (ref) => ClaimSearchController(ref.watch(claimRepositoryProvider)),
    );
