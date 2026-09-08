import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/verification_repository.dart';
import '../domain/models/verification_exception.dart';
import '../domain/models/verification_record.dart';

/// S-20 (Verification Status)'s load state -- a thin wrapper around
/// `VerificationRepository.getMyCurrentStatus()`, following the existing
/// `features/provider/state/` convention (`Plan_S05_VER-001.md` item 31).
class VerificationStatusState {
  const VerificationStatusState({
    this.isLoading = true,
    this.record,
    this.error,
  });

  final bool isLoading;

  /// `null` means "never submitted" (a normal, expected state, backend
  /// 404) -- distinct from [error], which means the load itself failed.
  final VerificationRecord? record;
  final VerificationException? error;

  VerificationStatusState copyWith({
    bool? isLoading,
    VerificationRecord? record,
    bool clearRecord = false,
    VerificationException? error,
    bool clearError = false,
  }) {
    return VerificationStatusState(
      isLoading: isLoading ?? this.isLoading,
      record: clearRecord ? null : (record ?? this.record),
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Loads the caller's own current verification cycle (AC6) -- a provider
/// can view their own status but this controller never accepts or sends
/// any field that could change it (no `PATCH`/`PUT` call exists anywhere
/// in `VerificationRepository`).
class VerificationStatusController
    extends StateNotifier<VerificationStatusState> {
  VerificationStatusController(this._repository)
    : super(const VerificationStatusState()) {
    load();
  }

  final VerificationRepository _repository;

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final record = await _repository.getMyCurrentStatus();
      state = VerificationStatusState(isLoading: false, record: record);
    } on VerificationException catch (error) {
      state = state.copyWith(isLoading: false, error: error);
    }
  }
}

final verificationStatusControllerProvider =
    StateNotifierProvider.autoDispose<
      VerificationStatusController,
      VerificationStatusState
    >(
      (ref) => VerificationStatusController(
        ref.watch(verificationRepositoryProvider),
      ),
    );
