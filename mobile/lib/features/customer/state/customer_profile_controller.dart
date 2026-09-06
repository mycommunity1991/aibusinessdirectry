import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/language_controller.dart';
import '../data/customer_repository.dart';
import '../domain/models/customer_profile.dart';
import '../domain/models/customer_profile_exception.dart';

class CustomerProfileState {
  const CustomerProfileState({
    this.profile,
    this.isLoading = true,
    this.isSaving = false,
    this.error,
  });

  /// `null` only until the initial `GET /customers/me` resolves (or fails).
  final CustomerProfile? profile;

  /// True only for the initial load — not re-set to true by [profile]
  /// edits (those use [isSaving] instead), so the form is never replaced
  /// by a full-screen spinner mid-edit.
  final bool isLoading;

  final bool isSaving;
  final CustomerProfileException? error;

  CustomerProfileState copyWith({
    CustomerProfile? profile,
    bool? isLoading,
    bool? isSaving,
    CustomerProfileException? error,
    bool clearError = false,
  }) {
    return CustomerProfileState(
      profile: profile ?? this.profile,
      isLoading: isLoading ?? this.isLoading,
      isSaving: isSaving ?? this.isSaving,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the Profile & Settings screen's (S-14) load and field edits.
///
/// [updateLanguage] is the one method that touches a second provider
/// ([languageControllerProvider]) — it calls the `PATCH` endpoint **and**
/// applies the new locale to the running app in the same call, so AC6
/// ("changing language ... reflected immediately ... without requiring an
/// app restart") can never be satisfied by only half of that pair.
class CustomerProfileController extends StateNotifier<CustomerProfileState> {
  CustomerProfileController(this._ref, this._repository)
    : super(const CustomerProfileState()) {
    _load();
  }

  final Ref _ref;
  final CustomerRepository _repository;

  Future<void> _load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final profile = await _repository.getMyProfile();
      state = state.copyWith(profile: profile, isLoading: false);
    } on CustomerProfileException catch (error) {
      state = state.copyWith(isLoading: false, error: error);
    }
  }

  /// Re-runs the initial load — exposed for a "try again" retry action
  /// when the first `GET` fails.
  Future<void> retry() => _load();

  Future<bool> updateDisplayName(String displayName) {
    return _save(() => _repository.updateMyProfile(displayName: displayName));
  }

  /// `null`/empty [avatarUrl] explicitly clears the stored avatar rather
  /// than leaving it untouched (Decision 6, `Plan_S03_CUS-001.md` — a
  /// plain string URL field, not a file upload).
  Future<bool> updateAvatarUrl(String? avatarUrl) {
    final normalized = (avatarUrl == null || avatarUrl.isEmpty)
        ? null
        : avatarUrl;
    return _save(
      () => _repository.updateMyProfile(
        avatarUrl: normalized,
        clearAvatarUrl: normalized == null,
      ),
    );
  }

  Future<bool> updateNotificationChannel(NotificationChannel channel) {
    return _save(
      () => _repository.updateMyProfile(notificationChannel: channel),
    );
  }

  /// Updates `customer_preferences.language` server-side **and** applies
  /// [locale] to the running app immediately (AC6) — see class doc.
  Future<bool> updateLanguage(Locale locale) async {
    final succeeded = await _save(
      () => _repository.updateMyProfile(language: locale.languageCode),
    );
    if (succeeded) {
      await _ref.read(languageControllerProvider.notifier).setLanguage(locale);
    }
    return succeeded;
  }

  Future<bool> _save(Future<CustomerProfile> Function() action) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final profile = await action();
      state = state.copyWith(profile: profile, isSaving: false);
      return true;
    } on CustomerProfileException catch (error) {
      state = state.copyWith(isSaving: false, error: error);
      return false;
    }
  }
}

final customerProfileControllerProvider =
    StateNotifierProvider.autoDispose<
      CustomerProfileController,
      CustomerProfileState
    >(
      (ref) =>
          CustomerProfileController(ref, ref.watch(customerRepositoryProvider)),
    );
