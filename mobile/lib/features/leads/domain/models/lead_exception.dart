/// The category of failure behind a [LeadException]. Deliberately
/// coarse-grained, mirroring `provider_exception.dart`'s
/// [ProviderErrorType] pattern -- the UI layer never needs a raw HTTP
/// status code or backend error identifier (`docs/AI/06_SECURITY.md`).
enum LeadErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The caller has no Provider listing yet (backend 404
  /// `ProviderNotFoundError`, AC4) -- mirrors `PortfolioService.
  /// list_my_portfolio`'s identical 404 meaning for the same underlying
  /// "does this caller even have a Provider yet" check.
  notFound,

  /// Anything else (401 the screen shouldn't normally hit since it's only
  /// reachable while authenticated, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language Leads load failure, thrown by [LeadRepository].
/// Carries only [type] -- never the backend's raw `message` string, an
/// HTTP status code, or an internal error identifier.
class LeadException implements Exception {
  const LeadException({required this.type});

  final LeadErrorType type;

  @override
  String toString() => 'LeadException(type: $type)';
}
