import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/visibility_analytics_repository.dart';
import '../domain/models/visibility_analytics.dart';
import '../domain/models/visibility_analytics_exception.dart';

/// The Visibility Analytics screen's (LEAD-002, AC1-AC4) status -- mirrors
/// `LeadsStatus`'s shape (`features/leads/state/leads_controller.dart`):
/// [idle] before the first load, [loading] for that first load/a
/// pull-to-refresh, [loaded] once the single synthesized object has
/// resolved (possibly with `hasSufficientData == false`, AC4), [error] on
/// failure.
enum VisibilityAnalyticsStatus { idle, loading, error, loaded }

class VisibilityAnalyticsState {
  const VisibilityAnalyticsState({
    this.status = VisibilityAnalyticsStatus.idle,
    this.data,
    this.error,
  });

  final VisibilityAnalyticsStatus status;
  final VisibilityAnalytics? data;
  final VisibilityAnalyticsException? error;

  VisibilityAnalyticsState copyWith({
    VisibilityAnalyticsStatus? status,
    VisibilityAnalytics? data,
    VisibilityAnalyticsException? error,
    bool clearError = false,
  }) {
    return VisibilityAnalyticsState(
      status: status ?? this.status,
      data: data ?? this.data,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Runs `GET /providers/me/visibility-analytics` (LEAD-002). Starts from
/// [VisibilityAnalyticsStatus.idle] -- mirrors `LeadsController`'s own
/// shape exactly, including leaving the first [load] call to the screen
/// (`VisibilityAnalyticsScreen`'s `initState`) rather than firing it from
/// this constructor, so a test can construct this controller and drive
/// [load]/[refresh] deterministically without racing an unawaited
/// constructor-triggered fetch.
class VisibilityAnalyticsController
    extends StateNotifier<VisibilityAnalyticsState> {
  VisibilityAnalyticsController(this._repository)
    : super(const VisibilityAnalyticsState());

  final VisibilityAnalyticsRepository _repository;

  Future<void> load() async {
    state = state.copyWith(
      status: VisibilityAnalyticsStatus.loading,
      clearError: true,
    );
    try {
      final data = await _repository.getMyVisibilityAnalytics();
      state = state.copyWith(
        status: VisibilityAnalyticsStatus.loaded,
        data: data,
        clearError: true,
      );
    } on VisibilityAnalyticsException catch (error) {
      state = state.copyWith(
        status: VisibilityAnalyticsStatus.error,
        error: error,
      );
    }
  }

  /// Backs pull-to-refresh (AC4's still-refreshable "not enough data yet"
  /// state included) -- always re-runs [load] in full.
  Future<void> refresh() => load();
}

final visibilityAnalyticsControllerProvider =
    StateNotifierProvider.autoDispose<
      VisibilityAnalyticsController,
      VisibilityAnalyticsState
    >(
      (ref) => VisibilityAnalyticsController(
        ref.watch(visibilityAnalyticsRepositoryProvider),
      ),
    );
