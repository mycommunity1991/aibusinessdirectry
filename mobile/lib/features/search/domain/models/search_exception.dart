/// The category of failure behind a [SearchException].
///
/// Deliberately coarse-grained, mirroring `provider_exception.dart`'s
/// [ProviderErrorType]/`saved_address_exception.dart`'s
/// [SavedAddressErrorType]: the UI layer never needs a raw HTTP status code
/// or backend error identifier (`docs/AI/06_SECURITY.md`), only enough to
/// pick the right plain-language, localized copy (see
/// `presentation/utils/search_error_copy.dart`).
enum SearchErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// `radius_km` was outside the backend's configured bounds (backend 422
  /// `InvalidSearchRadiusError`, `Plan_S06_DIR-001.md` Decision 8).
  invalidRadius,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language search failure, thrown by [SearchRepository]. Carries
/// only [type] -- never the backend's raw `message` string, an HTTP status
/// code, or an internal error identifier.
class SearchException implements Exception {
  const SearchException({required this.type});

  final SearchErrorType type;

  @override
  String toString() => 'SearchException(type: $type)';
}
