/// The category of failure behind a [ContactException]. Deliberately
/// coarse-grained, mirroring `claim_exception.dart`'s `ClaimErrorType`
/// pattern -- the UI layer never needs a raw HTTP status code or backend
/// error identifier (`docs/AI/06_SECURITY.md`).
enum ContactErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The requesting Customer's Account is the same Account that owns the
  /// target Provider -- rejected outright (backend 403
  /// `SelfDealingContactError`, AC3/AC4, Decision 10,
  /// `Plan_S08_CON-001.md`).
  selfDealing,

  /// The target provider doesn't exist (or is soft-deleted), or a
  /// caller-supplied `search_request_id` doesn't exist or doesn't belong to
  /// the calling customer (backend 404, Decision 4).
  notFound,

  /// Anything else (401/403-wrong-role the sheet shouldn't normally hit
  /// since it's only reachable while authenticated as a customer, 5xx, or
  /// an unrecognized shape).
  unknown,
}

/// A plain-language Contact Reveal failure, thrown by
/// [ProviderProfileRepository.createContactView]. Carries only [type] --
/// never the backend's raw `message` string, an HTTP status code, or an
/// internal error identifier.
class ContactException implements Exception {
  const ContactException({required this.type});

  final ContactErrorType type;

  @override
  String toString() => 'ContactException(type: $type)';
}
