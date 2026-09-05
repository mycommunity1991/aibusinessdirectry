import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/oauth_config.dart';
import '../domain/models/auth_exception.dart';
import '../domain/models/auth_token.dart';

/// Wraps the mobile-OTP auth endpoints (`POST /auth/request-otp`,
/// `POST /auth/verify-otp`) and the Google/Apple OAuth endpoints
/// (`POST /auth/google`, `POST /auth/apple`, AUTH-002).
///
/// Every failure is mapped to a plain-language [AuthException] — callers
/// (state controllers/screens) never see a [DioException], an HTTP status
/// code, or a backend error identifier (AC10, `docs/AI/06_SECURITY.md`). The
/// one deliberate exception is [OAuthCancelledException] (AC7): a benign,
/// non-error outcome that is never wrapped in [AuthException].
class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  /// Guards [GoogleSignIn.instance.initialize] — the plugin requires this be
  /// called exactly once, and awaited, before any other method.
  bool _googleSignInInitialized = false;

  /// Requests a 6-digit OTP for the given phone number. Always resolves
  /// successfully for a well-formed number — the backend never confirms or
  /// denies whether the number is already registered.
  ///
  /// Returns the OTP's `expires_in_seconds` from the response
  /// (`RequestOtpResponse` — `backend/app/modules/identity/schemas.py`), so
  /// callers can size a resend countdown from the real server value (FU-2).
  /// Returns `null` only if that field is somehow missing from the response
  /// — a should-be-unreachable, defensive case per the current contract.
  Future<int?> requestOtp({
    required String phoneCountryCode,
    required String phoneNumber,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/request-otp',
        data: {
          'phone_country_code': phoneCountryCode,
          'phone_number': phoneNumber,
        },
      );
      final data = response.data?['data'];
      final expiresInSeconds = data is Map<String, dynamic>
          ? data['expires_in_seconds']
          : null;
      return expiresInSeconds is int ? expiresInSeconds : null;
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Verifies a 6-digit OTP and returns the resulting [AuthToken]. The
  /// backend transparently creates-or-fetches the user — the client never
  /// needs to know in advance whether this is a registration or a login.
  Future<AuthToken> verifyOtp({
    required String phoneCountryCode,
    required String phoneNumber,
    required String code,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/verify-otp',
        data: {
          'phone_country_code': phoneCountryCode,
          'phone_number': phoneNumber,
          'code': code,
        },
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const AuthException(type: AuthErrorType.unknown);
      }
      return AuthToken.fromJson(data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Signs in with Google: runs the native Google sign-in flow to obtain an
  /// ID token, then exchanges it with the backend via `POST /auth/google`.
  ///
  /// Throws [OAuthCancelledException] if the user closes the Google consent
  /// screen (AC7) — never an [AuthException] for that case. Any other
  /// failure (native plugin error, or the backend rejecting the token)
  /// throws an [AuthException], most commonly
  /// [AuthErrorType.identityVerificationFailed].
  Future<AuthToken> signInWithGoogle() async {
    final idToken = await _obtainGoogleIdToken();
    return _exchangeIdToken('/auth/google', idToken);
  }

  /// Signs in with Apple: runs the native Sign in with Apple flow to obtain
  /// an identity token, then exchanges it with the backend via
  /// `POST /auth/apple`. See [signInWithGoogle] for the failure contract.
  Future<AuthToken> signInWithApple() async {
    final idToken = await _obtainAppleIdToken();
    return _exchangeIdToken('/auth/apple', idToken);
  }

  Future<void> _ensureGoogleSignInInitialized() async {
    if (_googleSignInInitialized) return;
    await GoogleSignIn.instance.initialize(
      serverClientId: OAuthConfig.googleServerClientId.isEmpty
          ? null
          : OAuthConfig.googleServerClientId,
    );
    _googleSignInInitialized = true;
  }

  Future<String> _obtainGoogleIdToken() async {
    try {
      await _ensureGoogleSignInInitialized();
      final account = await GoogleSignIn.instance.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw const AuthException(
          type: AuthErrorType.identityVerificationFailed,
        );
      }
      return idToken;
    } on GoogleSignInException catch (error) {
      if (error.code == GoogleSignInExceptionCode.canceled) {
        throw const OAuthCancelledException();
      }
      throw const AuthException(type: AuthErrorType.identityVerificationFailed);
    }
  }

  Future<String> _obtainAppleIdToken() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: const [AppleIDAuthorizationScopes.email],
        webAuthenticationOptions: _appleWebAuthenticationOptions(),
      );
      final idToken = credential.identityToken;
      if (idToken == null) {
        throw const AuthException(
          type: AuthErrorType.identityVerificationFailed,
        );
      }
      return idToken;
    } on SignInWithAppleAuthorizationException catch (error) {
      if (error.code == AuthorizationErrorCode.canceled) {
        throw const OAuthCancelledException();
      }
      throw const AuthException(type: AuthErrorType.identityVerificationFailed);
    }
  }

  /// Only Apple's Android/web fallback flow needs a Services ID/redirect URI
  /// (native iOS/macOS uses the app's Bundle ID and needs none of this) —
  /// `null` is a valid, supported value when that hasn't been configured
  /// (Plan Decision 10).
  WebAuthenticationOptions? _appleWebAuthenticationOptions() {
    if (OAuthConfig.appleServiceId.isEmpty ||
        OAuthConfig.appleRedirectUri.isEmpty) {
      return null;
    }
    return WebAuthenticationOptions(
      clientId: OAuthConfig.appleServiceId,
      redirectUri: Uri.parse(OAuthConfig.appleRedirectUri),
    );
  }

  /// Exchanges a provider ID token for the same [AuthToken] shape
  /// [verifyOtp] returns — both endpoints reuse the backend's
  /// `AuthTokenResponse` unchanged (Plan Decision 7).
  Future<AuthToken> _exchangeIdToken(String path, String idToken) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        path,
        data: {'id_token': idToken},
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const AuthException(type: AuthErrorType.unknown);
      }
      return AuthToken.fromJson(data);
    } on DioException catch (error) {
      throw _mapOAuthError(error);
    }
  }

  /// Maps a Dio failure from `/auth/google`/`/auth/apple` to a
  /// plain-language [AuthException]. A 401 is always
  /// `InvalidIdentityTokenError` (AC6) — collapsed into
  /// [AuthErrorType.identityVerificationFailed], never a detailed reason.
  AuthException _mapOAuthError(DioException error) {
    final response = error.response;
    if (response == null) {
      return const AuthException(type: AuthErrorType.network);
    }

    final statusCode = response.statusCode;
    if (statusCode == 429) {
      return const AuthException(type: AuthErrorType.tooManyAttempts);
    }
    if (statusCode == 401) {
      return const AuthException(
        type: AuthErrorType.identityVerificationFailed,
      );
    }
    return const AuthException(type: AuthErrorType.unknown);
  }

  /// Maps a Dio failure to a plain-language [AuthException].
  ///
  /// Only [AuthErrorType] is carried across — never the backend's raw
  /// `message` string, an HTTP status code, or an internal error
  /// identifier. Every type is rendered from client-owned, localized copy
  /// (`auth_error_copy.dart`, FU-3). A 429 always maps to
  /// [AuthErrorType.tooManyAttempts]: it covers both `OtpLockedError`
  /// (too many wrong attempts) and `RateLimitExceededError` (too many
  /// requests) — see [AuthErrorType.tooManyAttempts] for why they're not
  /// distinguished further.
  AuthException _mapError(DioException error) {
    final response = error.response;
    if (response == null) {
      return const AuthException(type: AuthErrorType.network);
    }

    final statusCode = response.statusCode;
    if (statusCode == 429) {
      return const AuthException(type: AuthErrorType.tooManyAttempts);
    }
    if (statusCode == 400) {
      return const AuthException(type: AuthErrorType.invalidCode);
    }
    return const AuthException(type: AuthErrorType.unknown);
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient.dio);
});
