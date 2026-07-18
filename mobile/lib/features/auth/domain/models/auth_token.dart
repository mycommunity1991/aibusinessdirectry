import 'auth_user.dart';

/// A thin client-side model matching the backend's `AuthTokenResponse`
/// (`backend/app/schemas/auth.py`), returned by a successful `verify-otp`.
///
/// Held in memory only (Riverpod state) for this story — persisting it
/// across app restarts is AUTH-003's job.
class AuthToken {
  const AuthToken({
    required this.accessToken,
    required this.tokenType,
    required this.user,
  });

  factory AuthToken.fromJson(Map<String, dynamic> json) {
    return AuthToken(
      accessToken: json['access_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      user: AuthUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }

  final String accessToken;
  final String tokenType;
  final AuthUser user;
}
