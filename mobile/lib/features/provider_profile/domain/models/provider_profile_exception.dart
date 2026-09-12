/// The category of failure behind a [ProviderProfileException]. Deliberately
/// coarse-grained, mirroring `search_exception.dart`/`claim_exception.dart`'s
/// `*ErrorType` pattern -- the UI layer never needs a raw HTTP status code
/// or backend error identifier (`docs/AI/06_SECURITY.md`).
enum ProviderProfileErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The target `provider_id` doesn't exist, or is soft-deleted (backend
  /// 404 `ProviderNotFoundError`).
  notFound,

  /// Anything else (401/403 the screen shouldn't normally hit since it's
  /// only reachable while authenticated as a customer, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language Provider Profile load failure, thrown by
/// [ProviderProfileRepository.getProviderProfile]. Carries only [type] --
/// never the backend's raw `message` string, an HTTP status code, or an
/// internal error identifier.
class ProviderProfileException implements Exception {
  const ProviderProfileException({required this.type});

  final ProviderProfileErrorType type;

  @override
  String toString() => 'ProviderProfileException(type: $type)';
}
