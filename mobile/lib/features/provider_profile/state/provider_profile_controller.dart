import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_profile_repository.dart';
import '../domain/models/provider_profile.dart';
import '../domain/models/provider_profile_exception.dart';

/// The Provider Profile screen's (S-09) load status.
enum ProviderProfileStatus { loading, loaded, error }

class ProviderProfileState {
  const ProviderProfileState({
    this.status = ProviderProfileStatus.loading,
    this.profile,
    this.error,
  });

  final ProviderProfileStatus status;
  final ProviderProfile? profile;
  final ProviderProfileException? error;

  ProviderProfileState copyWith({
    ProviderProfileStatus? status,
    ProviderProfile? profile,
    ProviderProfileException? error,
  }) {
    return ProviderProfileState(
      status: status ?? this.status,
      profile: profile ?? this.profile,
      error: error ?? this.error,
    );
  }
}

/// Loads `GET /providers/{providerId}` (CON-001, AC5) the moment the
/// Provider Profile screen is reached -- kept as its own controller,
/// separate from [ContactRevealController], so the Contact Reveal sheet's
/// own in-flight state never couples to this screen-level load (Plan's
/// Frontend item 1).
class ProviderProfileController extends StateNotifier<ProviderProfileState> {
  ProviderProfileController(this._repository, {required this.providerId})
    : super(const ProviderProfileState()) {
    _load();
  }

  final ProviderProfileRepository _repository;
  final String providerId;

  Future<void> _load() async {
    state = state.copyWith(status: ProviderProfileStatus.loading);
    try {
      final profile = await _repository.getProviderProfile(providerId);
      state = state.copyWith(
        status: ProviderProfileStatus.loaded,
        profile: profile,
      );
    } on ProviderProfileException catch (error) {
      state = state.copyWith(status: ProviderProfileStatus.error, error: error);
    }
  }

  /// Retries the initial load -- offered from the error state's retry
  /// action, mirroring `SearchResultsScreen`/`ClaimOtpController`'s own
  /// load-error/retry pattern.
  Future<void> retry() => _load();
}

final providerProfileControllerProvider = StateNotifierProvider.autoDispose
    .family<ProviderProfileController, ProviderProfileState, String>((
      ref,
      providerId,
    ) {
      return ProviderProfileController(
        ref.watch(providerProfileRepositoryProvider),
        providerId: providerId,
      );
    });
