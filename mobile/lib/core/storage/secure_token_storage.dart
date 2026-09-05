import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../features/auth/domain/models/auth_token.dart';

/// Persists the current [AuthToken] (access + refresh token pair, plus the
/// user summary) to secure, on-device storage, so a signed-in session
/// survives an app restart (AUTH-003).
///
/// Wraps the already-approved `flutter_secure_storage` dependency
/// (`docs/AI/12_TECH_STACK.md`), previously added but unused. The whole
/// [AuthToken] is stored as a single JSON blob under one key — round-tripped
/// through [AuthToken.toJson]/[AuthToken.fromJson] rather than a
/// hand-maintained second serialization shape.
///
/// Not `final` so tests can extend it with an in-memory fake (mirroring
/// `FakeAuthRepository`'s pattern) instead of touching the real platform
/// channel — see `test/features/auth/fakes/fake_secure_token_storage.dart`.
class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _sessionKey = 'auth_session_v1';

  /// Reads the persisted session, if any. Returns `null` if nothing is
  /// stored, or if the stored value is somehow malformed (defensive —
  /// treated the same as "no session" rather than crashing the splash
  /// screen).
  Future<AuthToken?> read() async {
    final raw = await _storage.read(key: _sessionKey);
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      return AuthToken.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  /// Persists [token], replacing any previously stored session.
  Future<void> write(AuthToken token) async {
    await _storage.write(key: _sessionKey, value: jsonEncode(token.toJson()));
  }

  /// Removes any persisted session (logout, or a rejected silent refresh).
  Future<void> clear() async {
    await _storage.delete(key: _sessionKey);
  }
}

final secureTokenStorageProvider = Provider<SecureTokenStorage>((ref) {
  return SecureTokenStorage();
});
