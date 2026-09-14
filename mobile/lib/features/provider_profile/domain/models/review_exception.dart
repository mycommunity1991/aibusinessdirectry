/// The category of failure behind a [ReviewException]. Deliberately
/// coarse-grained, mirroring `outcome_tag_exception.dart`'s
/// `OutcomeTagErrorType` pattern -- the UI layer never needs a raw HTTP
/// status code or backend error identifier (`docs/AI/06_SECURITY.md`).
enum ReviewErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// `contact_view_id` doesn't exist, or doesn't belong to the calling
  /// customer (backend 404 `ContactViewNotFoundError`, REV-002, AC2,
  /// Decision 5 -- collapsed into one non-revealing 404). Effectively
  /// unreachable in the normal flow (this screen is only ever reached with
  /// the same `contact_view_id` this session just anchored a `hired=true`
  /// outcome tag against) -- shown as a plain-language inline error on the
  /// Write-a-Review screen, same as every other type here.
  notFound,

  /// The anchoring Contact View has no confirmed hire outcome (no outcome
  /// tag, or `hired=false`) (backend 409 `ReviewAnchorNotVerifiedError`,
  /// REV-002, AC2, Decision 5). Also effectively unreachable in the normal
  /// flow (AC6's own guard already means this screen is never reached
  /// without a real `hired=true` submission).
  anchorNotVerified,

  /// A Review was already submitted for this Contact View (backend 409
  /// `ReviewAlreadyExistsError`, REV-002, AC1 -- immutable, one-shot). Also
  /// effectively unreachable in the normal flow. The backend's plain
  /// `{success, message, errors}` `ErrorResponse` shape carries no
  /// structured identifier distinguishing this from [anchorNotVerified]
  /// (both are a bare 409), so [ProviderProfileRepository]'s mapping never
  /// actually produces this value today -- kept for documentation/
  /// forward-compatibility (Decision 5's taxonomy).
  alreadyExists,

  /// Anything else (401/403-wrong-role the screen shouldn't normally hit
  /// since it's only reachable while authenticated as a customer, 5xx, or
  /// an unrecognized shape).
  unknown,
}

/// A plain-language Review submission failure, thrown by
/// [ProviderProfileRepository.submitReview]. Carries only [type] -- never
/// the backend's raw `message` string, an HTTP status code, or an internal
/// error identifier.
class ReviewException implements Exception {
  const ReviewException({required this.type});

  final ReviewErrorType type;

  @override
  String toString() => 'ReviewException(type: $type)';
}
