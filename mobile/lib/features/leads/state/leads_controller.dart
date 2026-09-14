import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/lead_repository.dart';
import '../domain/models/lead.dart';
import '../domain/models/lead_exception.dart';

/// The Leads screen's (LEAD-001, AC1/AC2) status -- mirrors
/// `SearchResultsStatus`'s shape (`features/search/state/
/// search_results_controller.dart`): [idle] before the first load,
/// [loading] for that first load/a pull-to-refresh, [loaded] once a page
/// (possibly empty, AC2) has resolved, [error] on failure.
enum LeadsStatus { idle, loading, error, loaded }

class LeadsState {
  const LeadsState({
    this.status = LeadsStatus.idle,
    this.leads = const [],
    this.error,
    this.page = 1,
    this.hasMore = false,
    this.isLoadingMore = false,
  });

  final LeadsStatus status;
  final List<Lead> leads;
  final LeadException? error;

  /// The most recently, successfully loaded page number.
  final int page;

  /// Whether a further page exists beyond [leads]'s current length.
  final bool hasMore;

  /// A second page (or later) is being appended -- kept separate from
  /// [status] so loading page 2+ never blanks the already-loaded list back
  /// to a full-screen spinner.
  final bool isLoadingMore;

  LeadsState copyWith({
    LeadsStatus? status,
    List<Lead>? leads,
    LeadException? error,
    bool clearError = false,
    int? page,
    bool? hasMore,
    bool? isLoadingMore,
  }) {
    return LeadsState(
      status: status ?? this.status,
      leads: leads ?? this.leads,
      error: clearError ? null : (error ?? this.error),
      page: page ?? this.page,
      hasMore: hasMore ?? this.hasMore,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
    );
  }
}

/// Runs `GET /providers/me/leads` (LEAD-001). Starts from
/// [LeadsStatus.idle] -- mirrors `SearchResultsController`'s own shape
/// exactly, including leaving the first [load] call to the screen
/// (`LeadsScreen`'s `initState`, mirroring `SearchResultsScreen`'s own
/// post-frame-callback pattern) rather than firing it from this
/// constructor, so a test can construct this controller and drive [load]/
/// [refresh]/[loadMore] deterministically without racing an unawaited
/// constructor-triggered fetch.
class LeadsController extends StateNotifier<LeadsState> {
  LeadsController(this._repository) : super(const LeadsState());

  final LeadRepository _repository;

  static const _pageSize = 20;

  /// Loads [page] (default 1). Page 1 always replaces [LeadsState.leads]
  /// wholesale (used for the initial load); any later page appends to the
  /// existing list (pagination page-append behavior) rather than
  /// replacing it.
  Future<void> load({int page = 1}) async {
    if (page == 1) {
      state = state.copyWith(status: LeadsStatus.loading, clearError: true);
    } else {
      if (!state.hasMore || state.isLoadingMore) return;
      state = state.copyWith(isLoadingMore: true, clearError: true);
    }
    try {
      final result = await _repository.listMyLeads(
        page: page,
        pageSize: _pageSize,
      );
      final leads = page == 1
          ? result.leads
          : [...state.leads, ...result.leads];
      state = state.copyWith(
        status: LeadsStatus.loaded,
        leads: leads,
        page: page,
        hasMore: leads.length < result.totalItems,
        isLoadingMore: false,
        clearError: true,
      );
    } on LeadException catch (error) {
      state = state.copyWith(
        status: page == 1 ? LeadsStatus.error : state.status,
        error: error,
        isLoadingMore: false,
      );
    }
  }

  /// Loads the page immediately after the most recently loaded one --
  /// appends to [LeadsState.leads] (a no-op if [LeadsState.hasMore] is
  /// already `false`).
  Future<void> loadMore() => load(page: state.page + 1);

  /// Backs pull-to-refresh (AC2) -- always resets to page 1, replacing
  /// [LeadsState.leads] with a fresh page 1, never appending to whatever
  /// was already loaded.
  Future<void> refresh() => load(page: 1);
}

final leadsControllerProvider =
    StateNotifierProvider.autoDispose<LeadsController, LeadsState>(
      (ref) => LeadsController(ref.watch(leadRepositoryProvider)),
    );
