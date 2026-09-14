import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_profile_repository.dart';
import '../domain/models/review_exception.dart';

/// The Write-a-Review screen's (S-10, REV-002) submit-action status.
enum WriteReviewStatus { idle, submitting, submitted, error }

class WriteReviewState {
  const WriteReviewState({
    this.status = WriteReviewStatus.idle,
    this.rating,
    this.error,
  });

  final WriteReviewStatus status;

  /// The customer's selected star rating, 1-5 (AC3) -- `null` until the
  /// customer taps a star. Submission is only possible once this is
  /// non-null (Plan's Frontend item 1, "no default selection").
  final int? rating;
  final ReviewException? error;

  WriteReviewState copyWith({
    WriteReviewStatus? status,
    int? rating,
    ReviewException? error,
  }) {
    return WriteReviewState(
      status: status ?? this.status,
      rating: rating ?? this.rating,
      error: error ?? this.error,
    );
  }
}

/// Calls `POST /contact-views/{contact_view_id}/review` (REV-002, AC1)
/// only once the customer taps Submit with a star rating already chosen.
/// Kept as its own controller, separate from
/// `OutcomeTagPromptController`/`ContactRevealController`/
/// `ProviderProfileController`, per this codebase's established "each
/// screen/sheet's own in-flight state doesn't couple to another's"
/// principle (Plan's Frontend item 1).
class WriteReviewController extends StateNotifier<WriteReviewState> {
  WriteReviewController(this._repository, {required this.contactViewId})
    : super(const WriteReviewState());

  final ProviderProfileRepository _repository;
  final String contactViewId;

  /// Selects (or changes) the star rating -- never submits by itself.
  void selectRating(int rating) {
    state = state.copyWith(rating: rating);
  }

  /// Submits the currently-selected [WriteReviewState.rating] with an
  /// optional [comment]. A no-op, performing zero repository calls, if no
  /// rating has been selected yet -- the screen's Submit button is already
  /// disabled in that state, but this guard keeps the controller itself
  /// honest independent of the UI (AC3).
  Future<void> submit({String? comment}) async {
    final rating = state.rating;
    if (rating == null) return;

    state = state.copyWith(status: WriteReviewStatus.submitting);
    try {
      await _repository.submitReview(
        contactViewId: contactViewId,
        rating: rating,
        comment: comment,
      );
      state = state.copyWith(status: WriteReviewStatus.submitted);
    } on ReviewException catch (error) {
      state = state.copyWith(status: WriteReviewStatus.error, error: error);
    }
  }
}

final writeReviewControllerProvider = StateNotifierProvider.autoDispose
    .family<WriteReviewController, WriteReviewState, String>((
      ref,
      contactViewId,
    ) {
      return WriteReviewController(
        ref.watch(providerProfileRepositoryProvider),
        contactViewId: contactViewId,
      );
    });
