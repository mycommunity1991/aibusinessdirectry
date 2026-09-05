/// The category of failure behind an [AuthException].
///
/// Deliberately coarse-grained: the UI layer never needs to know the raw
/// HTTP status code or backend error identifier (`docs/AI/06_SECURITY.md`,
/// AC10) — only enough to pick the right plain-language, localized copy
/// (see `auth_error_copy.dart`; FU-3, `Walkthrough_S02_AUTH-001.md`).
enum AuthErrorType {
  /// The OTP code was wrong, expired, or already used (backend 400,
  /// `InvalidOtpError`). Deliberately generic per AC5 — never reveals which.
  invalidCode,

  /// The OTP has reached its maximum verification attempts (backend 429,
  /// `OtpLockedError`), **or** the client has been rate-limited (backend
  /// 429, `RateLimitExceededError` — `backend/app/core/rate_limit.py`).
  /// Both are collapsed into one type: the response carries no
  /// machine-readable field distinguishing them (only the human-readable
  /// `message`, which isn't a stable contract to parse), so this type's
  /// copy is deliberately phrased to read sensibly for either "slow down"
  /// condition.
  tooManyAttempts,

  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// A Google/Apple sign-in could not be completed: the backend rejected
  /// the provider's ID token (invalid, expired, or tampered — backend 401,
  /// `InvalidIdentityTokenError`), or the native plugin failed for a reason
  /// other than user cancellation (AUTH-002 AC6/AC7). Deliberately generic,
  /// mirroring the backend's own non-revealing copy — never distinguishes
  /// *why* verification failed, and never surfaced for a plain user
  /// cancellation (see [OAuthCancelledException], which is not an
  /// [AuthErrorType] at all, per `Plan_S02_AUTH-002.md` Decision 13).
  identityVerificationFailed,

  /// Anything else (422 validation, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language auth failure, thrown by [AuthRepository].
///
/// Carries only [type] — every failure is rendered from a client-owned,
/// localized string (`auth_error_copy.dart`), never a raw backend message,
/// status code, stack trace, or internal identifier.
class AuthException implements Exception {
  const AuthException({required this.type});

  final AuthErrorType type;

  @override
  String toString() => 'AuthException(type: $type)';
}

/// Thrown by [AuthRepository.signInWithGoogle]/[AuthRepository.signInWithApple]
/// when the user cancels the native Google/Apple consent screen mid-flow.
///
/// A benign, non-error outcome (AC7) — deliberately **not** an
/// [AuthException]/[AuthErrorType] value, so a cancellation can never
/// accidentally render user-facing error copy. Callers (`OAuthSignInController`)
/// catch this specifically and reset to idle with no error shown, per
/// `Plan_S02_AUTH-002.md` Decision 13.
class OAuthCancelledException implements Exception {
  const OAuthCancelledException();

  @override
  String toString() => 'OAuthCancelledException()';
}
