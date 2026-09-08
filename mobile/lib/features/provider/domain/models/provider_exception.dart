/// The category of failure behind a [ProviderException].
///
/// Deliberately coarse-grained, mirroring
/// `saved_address_exception.dart`'s [SavedAddressErrorType]: the UI layer
/// never needs a raw HTTP status code or backend error identifier
/// (`docs/AI/06_SECURITY.md`), only enough to pick the right plain-language,
/// localized copy (see `presentation/utils/provider_error_copy.dart`).
enum ProviderErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The caller already has a provider listing (backend 409
  /// `ProviderAlreadyExistsError`, AC8/AC10) -- one Provider per Account.
  alreadyExists,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language provider failure, thrown by [ProviderRepository].
/// Carries only [type] — never the backend's raw `message` string, an HTTP
/// status code, or an internal error identifier.
class ProviderException implements Exception {
  const ProviderException({required this.type});

  final ProviderErrorType type;

  @override
  String toString() => 'ProviderException(type: $type)';
}
