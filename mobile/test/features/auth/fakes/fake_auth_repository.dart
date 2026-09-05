import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [AuthRepository] — no real Dio/network calls
/// are ever made. The base [Dio] passed to `super` is never touched since
/// every public method is overridden below.
class FakeAuthRepository extends AuthRepository {
  FakeAuthRepository({
    this.requestOtpError,
    this.verifyOtpError,
    this.requestOtpExpiresInSeconds,
    this.signInWithGoogleError,
    this.signInWithAppleError,
    this.refreshError,
    AuthToken? tokenToReturn,
    AuthToken? refreshTokenToReturn,
  }) : _tokenToReturn = tokenToReturn ?? _defaultToken,
       _refreshTokenToReturn =
           refreshTokenToReturn ?? tokenToReturn ?? _defaultToken,
       super(Dio());

  static final _defaultToken = AuthToken(
    accessToken: 'test-access-token',
    refreshToken: 'test-refresh-token',
    tokenType: 'bearer',
    user: const AuthUser(
      id: 'user-1',
      phoneCountryCode: '+971',
      phoneNumber: '501234567',
      status: 'active',
      preferredLanguage: 'en',
      roles: ['customer'],
    ),
  );

  final AuthException? requestOtpError;
  final AuthException? verifyOtpError;
  final AuthToken _tokenToReturn;

  /// The `expires_in_seconds` this fake's `requestOtp` resolves with —
  /// `null` by default, matching a not-yet-known/unspecified server value
  /// in tests that don't care about it.
  final int? requestOtpExpiresInSeconds;

  /// The failure `signInWithGoogle` throws, if any. Accepts any [Object] so
  /// tests can configure either an [AuthException] (a real failure, AC6) or
  /// an [OAuthCancelledException] (user cancellation, AC7) — the two cases
  /// [OAuthSignInController] must handle differently.
  final Object? signInWithGoogleError;

  /// The failure `signInWithApple` throws, if any. See
  /// [signInWithGoogleError] for the accepted failure types.
  final Object? signInWithAppleError;

  /// The failure `refresh` throws, if any (AUTH-003) — e.g. an expired or
  /// revoked refresh token, surfaced as an [AuthException].
  final Object? refreshError;

  /// The [AuthToken] `refresh` resolves with, if [refreshError] is unset.
  /// Defaults to [_tokenToReturn] so a plain `FakeAuthRepository()` behaves
  /// consistently across login and refresh.
  final AuthToken _refreshTokenToReturn;

  int requestOtpCallCount = 0;
  int verifyOtpCallCount = 0;
  int signInWithGoogleCallCount = 0;
  int signInWithAppleCallCount = 0;
  int refreshCallCount = 0;
  int logoutCallCount = 0;
  String? lastRefreshToken;
  String? lastLogoutAccessToken;

  @override
  Future<int?> requestOtp({
    required String phoneCountryCode,
    required String phoneNumber,
  }) async {
    requestOtpCallCount++;
    if (requestOtpError != null) {
      throw requestOtpError!;
    }
    return requestOtpExpiresInSeconds;
  }

  @override
  Future<AuthToken> verifyOtp({
    required String phoneCountryCode,
    required String phoneNumber,
    required String code,
  }) async {
    verifyOtpCallCount++;
    if (verifyOtpError != null) {
      throw verifyOtpError!;
    }
    return _tokenToReturn;
  }

  @override
  Future<AuthToken> signInWithGoogle() async {
    signInWithGoogleCallCount++;
    if (signInWithGoogleError != null) {
      throw signInWithGoogleError!;
    }
    return _tokenToReturn;
  }

  @override
  Future<AuthToken> signInWithApple() async {
    signInWithAppleCallCount++;
    if (signInWithAppleError != null) {
      throw signInWithAppleError!;
    }
    return _tokenToReturn;
  }

  @override
  Future<AuthToken> refresh(String refreshToken) async {
    refreshCallCount++;
    lastRefreshToken = refreshToken;
    if (refreshError != null) {
      throw refreshError!;
    }
    return _refreshTokenToReturn;
  }

  @override
  Future<void> logout(String? accessToken) async {
    logoutCallCount++;
    lastLogoutAccessToken = accessToken;
  }
}
