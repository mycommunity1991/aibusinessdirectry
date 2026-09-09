/// The category of failure behind a [ClaimException].
///
/// Deliberately coarse-grained, mirroring `auth_exception.dart`'s
/// [AuthErrorType]/`provider_exception.dart`'s [ProviderErrorType]: the UI
/// layer never needs a raw HTTP status code or backend error identifier
/// (`docs/AI/06_SECURITY.md`), only enough to pick the right plain-language,
/// localized copy.
enum ClaimErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The target `provider_id` either doesn't exist at all, or is not a
  /// still-unclaimed Google-seeded listing (backend 404
  /// `ClaimTargetNotFoundError`).
  targetNotFound,

  /// The listing has no public phone number on record -- the OTP trust
  /// gate is structurally unusable (backend 409
  /// `ClaimPublicNumberUnavailableError`, AC6). Raised only by
  /// `ClaimRepository.requestOtp` -- `ClaimOtpController` catches this
  /// specifically and skips the OTP-entry UI entirely, auto-submitting
  /// `request-admin-review` with `reason=no_public_number`
  /// (`claim_review_reason.dart`).
  publicNumberUnavailable,

  /// The submitted OTP code didn't match, was expired, or was already
  /// used (backend 400). Deliberately generic, mirroring
  /// `AuthErrorType.invalidCode` -- never reveals which.
  invalidCode,

  /// The listing was already claimed by someone else, or the caller's
  /// account already owns a different provider listing (backend 409
  /// `ClaimAlreadyClaimedError`).
  alreadyClaimed,

  /// The OTP has reached its maximum verification attempts, **or** the
  /// client has been rate-limited (backend 429) -- collapsed into one
  /// type, mirroring `AuthErrorType.tooManyAttempts`'s identical reasoning.
  tooManyAttempts,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language claim-flow failure, thrown by [ClaimRepository].
/// Carries only [type] -- never the backend's raw `message` string, an
/// HTTP status code, or an internal error identifier.
class ClaimException implements Exception {
  const ClaimException({required this.type});

  final ClaimErrorType type;

  @override
  String toString() => 'ClaimException(type: $type)';
}
