import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_profile_repository.dart';
import '../domain/models/outcome_tag_exception.dart';

/// The Outcome Tag Prompt sheet's (REV-001, AC3) submit-action status.
/// [idle] covers both "not yet answered" and "Maybe later" -- that dismiss
/// path never touches this controller at all (Decision 7), so no dedicated
/// status exists for it.
enum OutcomeTagPromptStatus { idle, submitting, submitted, error }

class OutcomeTagPromptState {
  const OutcomeTagPromptState({
    this.status = OutcomeTagPromptStatus.idle,
    this.error,
    this.lastHired,
  });

  final OutcomeTagPromptStatus status;
  final OutcomeTagException? error;

  /// The `hired` value of the most recent submit attempt -- kept so the
  /// error state's retry action can re-submit the same answer, without the
  /// sheet needing to remember which button the customer tapped.
  final bool? lastHired;

  OutcomeTagPromptState copyWith({
    OutcomeTagPromptStatus? status,
    OutcomeTagException? error,
    bool? lastHired,
  }) {
    return OutcomeTagPromptState(
      status: status ?? this.status,
      error: error ?? this.error,
      lastHired: lastHired ?? this.lastHired,
    );
  }
}

/// Calls `POST /contact-views/{contact_view_id}/outcome-tag` (REV-001,
/// AC1) only when the customer taps Yes or No -- unlike
/// [ContactRevealController], nothing is submitted automatically when the
/// sheet opens, since "Maybe later" must perform zero network calls
/// (Decision 7). Kept as its own controller, separate from
/// `ContactRevealController`/`ProviderProfileController`, per this
/// codebase's established "each sheet's own in-flight state doesn't couple
/// to the screen/other-sheet's" principle (Plan's Frontend item 1).
class OutcomeTagPromptController extends StateNotifier<OutcomeTagPromptState> {
  OutcomeTagPromptController(this._repository, {required this.contactViewId})
    : super(const OutcomeTagPromptState());

  final ProviderProfileRepository _repository;
  final String contactViewId;

  Future<void> submit({required bool hired}) async {
    state = state.copyWith(
      status: OutcomeTagPromptStatus.submitting,
      lastHired: hired,
    );
    try {
      await _repository.submitOutcomeTag(
        contactViewId: contactViewId,
        hired: hired,
      );
      state = state.copyWith(status: OutcomeTagPromptStatus.submitted);
    } on OutcomeTagException catch (error) {
      state = state.copyWith(
        status: OutcomeTagPromptStatus.error,
        error: error,
      );
    }
  }

  /// Retries the last Yes/No submission -- offered from the error state's
  /// retry action. Only meaningful once [OutcomeTagPromptState.lastHired]
  /// has been set by a prior [submit] call.
  Future<void> retry() => submit(hired: state.lastHired!);
}

final outcomeTagPromptControllerProvider = StateNotifierProvider.autoDispose
    .family<OutcomeTagPromptController, OutcomeTagPromptState, String>((
      ref,
      contactViewId,
    ) {
      return OutcomeTagPromptController(
        ref.watch(providerProfileRepositoryProvider),
        contactViewId: contactViewId,
      );
    });
