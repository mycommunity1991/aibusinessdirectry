/// The category of failure behind an [OutcomeTagException]. Deliberately
/// coarse-grained, mirroring `contact_exception.dart`'s `ContactErrorType`
/// pattern -- the UI layer never needs a raw HTTP status code or backend
/// error identifier (`docs/AI/06_SECURITY.md`).
enum OutcomeTagErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// `contact_view_id` doesn't exist, or doesn't belong to the calling
  /// customer (backend 404 `ContactViewNotFoundError`, REV-001, AC2,
  /// Decision 2 -- collapsed into one non-revealing 404). Effectively
  /// unreachable in the normal flow (the sheet is only ever opened with a
  /// `contact_view_id` this same session just created), so the sheet
  /// simply closes rather than surfacing this as a scary error.
  notFound,

  /// An Outcome Tag was already submitted for this Contact View (backend
  /// 409 `OutcomeTagAlreadyExistsError`, REV-001, AC1/AC6/Decision 4 --
  /// immutable, one-shot). Also effectively unreachable in the normal
  /// flow; the sheet simply closes.
  alreadyExists,

  /// Anything else (401/403-wrong-role the sheet shouldn't normally hit
  /// since it's only reachable while authenticated as a customer, 5xx, or
  /// an unrecognized shape).
  unknown,
}

/// A plain-language Outcome Tag submission failure, thrown by
/// [ProviderProfileRepository.submitOutcomeTag]. Carries only [type] --
/// never the backend's raw `message` string, an HTTP status code, or an
/// internal error identifier.
class OutcomeTagException implements Exception {
  const OutcomeTagException({required this.type});

  final OutcomeTagErrorType type;

  @override
  String toString() => 'OutcomeTagException(type: $type)';
}
