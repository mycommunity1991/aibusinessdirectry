import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/auth_repository.dart';
import '../domain/models/auth_exception.dart';
import '../domain/models/auth_token.dart';

/// Which OAuth provider — if any — is currently signing in.
///
/// Client-side only; distinct from the backend's `AuthProvider` enum (which
/// also covers `mobile_otp`/`email_password`).
enum OAuthProvider { google, apple }

class OAuthSignInState {
  const OAuthSignInState({this.loadingProvider, this.error});

  /// The provider currently running its native sign-in flow, or `null` if
  /// idle. Only one sign-in can be in flight at a time.
  final OAuthProvider? loadingProvider;

  final AuthException? error;

  bool isLoading(OAuthProvider provider) => loadingProvider == provider;

  OAuthSignInState copyWith({
    OAuthProvider? loadingProvider,
    bool clearLoadingProvider = false,
    AuthException? error,
    bool clearError = false,
  }) {
    return OAuthSignInState(
      loadingProvider: clearLoadingProvider
          ? null
          : (loadingProvider ?? this.loadingProvider),
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the Sign In / Sign Up screen's (S-03) Google/Apple buttons —
/// separate from [PhoneEntryController] (`phone_entry_controller.dart`),
/// which owns the mobile-number path only; a distinct responsibility per
/// `08_CODING_STANDARDS.md`'s single-responsibility guidance
/// (`Plan_S02_AUTH-002.md`, "Mobile — Proposed Changes").
class OAuthSignInController extends StateNotifier<OAuthSignInState> {
  OAuthSignInController(this._repository) : super(const OAuthSignInState());

  final AuthRepository _repository;

  /// Runs the Google sign-in flow. Returns the resulting [AuthToken] on
  /// success, or `null` if a sign-in is already in flight, the user
  /// cancelled (AC7 — no error surfaced), or it failed (in which case
  /// [OAuthSignInState.error] carries the plain-language cause).
  Future<AuthToken?> signInWithGoogle() =>
      _signIn(OAuthProvider.google, _repository.signInWithGoogle);

  /// Runs the Apple sign-in flow. See [signInWithGoogle] for the contract.
  Future<AuthToken?> signInWithApple() =>
      _signIn(OAuthProvider.apple, _repository.signInWithApple);

  Future<AuthToken?> _signIn(
    OAuthProvider provider,
    Future<AuthToken> Function() signIn,
  ) async {
    if (state.loadingProvider != null) {
      return null;
    }

    state = state.copyWith(loadingProvider: provider, clearError: true);
    try {
      final token = await signIn();
      state = const OAuthSignInState();
      return token;
    } on OAuthCancelledException {
      // AC7 — cancellation is benign: reset to idle with no error shown,
      // never routed through AuthException/error copy (Plan Decision 13).
      state = const OAuthSignInState();
      return null;
    } on AuthException catch (error) {
      state = OAuthSignInState(error: error);
      return null;
    }
  }
}

final oauthSignInControllerProvider =
    StateNotifierProvider.autoDispose<OAuthSignInController, OAuthSignInState>(
      (ref) => OAuthSignInController(ref.watch(authRepositoryProvider)),
    );
