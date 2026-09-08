/// The category of failure behind a [VerificationException].
///
/// Deliberately coarse-grained, mirroring `provider_exception.dart`'s
/// `ProviderErrorType`: the UI layer never needs a raw HTTP status code or
/// backend error identifier (`docs/AI/06_SECURITY.md`), only enough to
/// pick the right plain-language, localized copy (see
/// `presentation/utils/verification_error_copy.dart`).
enum VerificationErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The caller has not created a provider listing yet (backend 404
  /// `ProviderNotFoundError` on preview/submit) -- defensive only; this
  /// feature is only reachable once a listing already exists (PRO-001),
  /// so this should be unreachable from the real UI.
  providerNotFound,

  /// An uploaded document exceeded the maximum size (backend 422
  /// `VerificationDocumentTooLargeError`, VER-001, AC3).
  documentTooLarge,

  /// An uploaded document's extension/content didn't match an allowed
  /// type (backend 422 `VerificationDocumentInvalidTypeError`, VER-001,
  /// AC3) -- covers both "wrong extension" and "magic-byte mismatch".
  documentInvalidType,

  /// The resolved verification requirement needs a document (always true
  /// for Freelancer; configurable for Business) but none was previewed,
  /// or the previewed `document_type` didn't satisfy the requirement
  /// (backend 422 `VerificationDocumentRequiredError`, AC2).
  documentRequired,

  /// The caller already has an active (pending/under_review/approved)
  /// verification cycle (backend 409
  /// `VerificationSubmissionNotAllowedError`).
  submissionNotAllowed,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language verification failure, thrown by
/// [VerificationRepository]. Carries only [type] -- never the backend's
/// raw `message` string, an HTTP status code, or an internal error
/// identifier.
class VerificationException implements Exception {
  const VerificationException({required this.type});

  final VerificationErrorType type;

  @override
  String toString() => 'VerificationException(type: $type)';
}
