import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/secure_token_storage.dart';
import '../domain/models/auth_token.dart';

/// Holds the current session's [AuthToken] in memory only. Callers should
/// go through [authSessionControllerProvider] (`setSession`/`clear`) rather
/// than writing to this provider's notifier directly, so a change is never
/// forgotten to be mirrored to secure storage (AUTH-003).
final authSessionProvider = StateProvider<AuthToken?>((ref) => null);

/// Keeps [authSessionProvider]'s in-memory state and
/// [SecureTokenStorage]'s persisted copy in sync — the single place a
/// session change (login, silent refresh, logout) is applied, so "stay
/// signed in across app restarts" (AUTH-003) can never be broken by a call
/// site that updates one and forgets the other.
class AuthSessionController {
  AuthSessionController(this._ref, this._storage);

  final Ref _ref;
  final SecureTokenStorage _storage;

  /// Populates in-memory session state and persists it — called on a
  /// successful login or a successful silent/explicit refresh.
  Future<void> setSession(AuthToken token) async {
    _ref.read(authSessionProvider.notifier).state = token;
    await _storage.write(token);
  }

  /// Clears in-memory session state and persisted storage — called on
  /// logout, and when a persisted session fails silent refresh at splash.
  Future<void> clear() async {
    _ref.read(authSessionProvider.notifier).state = null;
    await _storage.clear();
  }
}

final authSessionControllerProvider = Provider<AuthSessionController>((ref) {
  return AuthSessionController(ref, ref.watch(secureTokenStorageProvider));
});
