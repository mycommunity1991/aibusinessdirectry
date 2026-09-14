/// The category of failure behind a [VisibilityAnalyticsException].
/// Deliberately coarse-grained, mirroring `lead_exception.dart`'s
/// [LeadErrorType] pattern -- the UI layer never needs a raw HTTP status
/// code or backend error identifier (`docs/AI/06_SECURITY.md`).
enum VisibilityAnalyticsErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The caller has no Provider listing yet (backend 404
  /// `ProviderNotFoundError`, AC3) -- mirrors `LeadRepository.
  /// listMyLeads`'s identical 404 meaning for the same underlying "does
  /// this caller even have a Provider yet" check.
  notFound,

  /// Anything else (401 the screen shouldn't normally hit since it's only
  /// reachable while authenticated, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language Visibility Analytics load failure, thrown by
/// [VisibilityAnalyticsRepository]. Carries only [type] -- never the
/// backend's raw `message` string, an HTTP status code, or an internal
/// error identifier.
class VisibilityAnalyticsException implements Exception {
  const VisibilityAnalyticsException({required this.type});

  final VisibilityAnalyticsErrorType type;

  @override
  String toString() => 'VisibilityAnalyticsException(type: $type)';
}
