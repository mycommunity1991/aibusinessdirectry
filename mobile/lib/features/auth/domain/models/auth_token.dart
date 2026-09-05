import 'auth_user.dart';

/// A thin client-side model matching the backend's `AuthTokenResponse`
/// (`backend/app/modules/identity/schemas.py`), returned by a successful
/// `verify-otp`/`google`/`apple`/`refresh` call (AUTH-003 adds
/// [refreshToken] and the `refresh` case).
///
/// Held in memory ([authSessionProvider]) *and* persisted to secure,
/// on-device storage (`core/storage/secure_token_storage.dart`) so a
/// signed-in session survives an app restart — see
/// `AuthSessionController` for the single place both are kept in sync.
class AuthToken {
  const AuthToken({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.user,
  });

  factory AuthToken.fromJson(Map<String, dynamic> json) {
    return AuthToken(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      user: AuthUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }

  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final AuthUser user;

  /// Mirrors [fromJson]'s field names — used to persist this token to
  /// secure storage as JSON, so [SecureTokenStorage.read] can parse it
  /// back through the exact same [fromJson] the network layer uses.
  Map<String, dynamic> toJson() => {
    'access_token': accessToken,
    'refresh_token': refreshToken,
    'token_type': tokenType,
    'user': user.toJson(),
  };
}
