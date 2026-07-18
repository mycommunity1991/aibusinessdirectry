/// The category of failure behind an [AuthException].
///
/// Deliberately coarse-grained: the UI layer never needs to know the raw
/// HTTP status code or backend error identifier (`docs/AI/06_SECURITY.md`,
/// AC10) — only enough to pick the right plain-language copy.
enum AuthErrorType {
  /// The OTP code was wrong, expired, or already used (backend 400,
  /// `InvalidOtpError`). Deliberately generic per AC5 — never reveals which.
  invalidCode,

  /// The OTP has reached its maximum verification attempts (backend 429,
  /// `OtpLockedError`).
  tooManyAttempts,

  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// Anything else (422 validation, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language auth failure, thrown by [AuthRepository].
///
/// [serverMessage] is only ever populated for [AuthErrorType.invalidCode]
/// and [AuthErrorType.tooManyAttempts], where the backend already crafts a
/// safe, plain-language, non-revealing message (see `exceptions.py`). It is
/// never a raw status code, stack trace, or internal identifier.
class AuthException implements Exception {
  const AuthException({required this.type, this.serverMessage});

  final AuthErrorType type;
  final String? serverMessage;

  @override
  String toString() => 'AuthException(type: $type)';
}
