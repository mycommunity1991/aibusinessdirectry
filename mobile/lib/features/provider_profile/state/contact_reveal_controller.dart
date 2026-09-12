import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_profile_repository.dart';
import '../domain/models/contact_exception.dart';
import '../domain/models/contact_reveal.dart';
import '../domain/models/provider_profile_args.dart';

/// The Contact Reveal sheet's (CON-001, AC2) status.
enum ContactRevealStatus { loading, loaded, error }

class ContactRevealState {
  const ContactRevealState({
    this.status = ContactRevealStatus.loading,
    this.reveal,
    this.error,
  });

  final ContactRevealStatus status;
  final ContactReveal? reveal;
  final ContactException? error;

  ContactRevealState copyWith({
    ContactRevealStatus? status,
    ContactReveal? reveal,
    ContactException? error,
  }) {
    return ContactRevealState(
      status: status ?? this.status,
      reveal: reveal ?? this.reveal,
      error: error ?? this.error,
    );
  }
}

/// Calls `POST /contact-views` (AC2) the moment the Contact Reveal sheet
/// opens -- no quote request, approval wait, or in-app messaging step
/// exists anywhere in this flow. Kept as its own controller, separate from
/// [ProviderProfileController], so this sheet's own in-flight state never
/// couples to the screen-level profile load underneath it (Plan's Frontend
/// item 1).
class ContactRevealController extends StateNotifier<ContactRevealState> {
  ContactRevealController(this._repository, {required this.args})
    : super(const ContactRevealState()) {
    _reveal();
  }

  final ProviderProfileRepository _repository;
  final ProviderProfileArgs args;

  Future<void> _reveal() async {
    state = state.copyWith(status: ContactRevealStatus.loading);
    try {
      final reveal = await _repository.createContactView(
        providerId: args.providerId,
        searchRequestId: args.searchRequestId,
      );
      state = state.copyWith(
        status: ContactRevealStatus.loaded,
        reveal: reveal,
      );
    } on ContactException catch (error) {
      state = state.copyWith(status: ContactRevealStatus.error, error: error);
    }
  }

  /// Retries the reveal call -- offered from the error state's retry
  /// action.
  Future<void> retry() => _reveal();
}

final contactRevealControllerProvider = StateNotifierProvider.autoDispose
    .family<ContactRevealController, ContactRevealState, ProviderProfileArgs>((
      ref,
      args,
    ) {
      return ContactRevealController(
        ref.watch(providerProfileRepositoryProvider),
        args: args,
      );
    });
