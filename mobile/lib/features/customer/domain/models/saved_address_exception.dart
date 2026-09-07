/// The category of failure behind a [SavedAddressException].
///
/// Deliberately coarse-grained, mirroring
/// `customer_profile_exception.dart`'s [CustomerProfileErrorType]: the UI
/// layer never needs a raw HTTP status code or backend error identifier
/// (`docs/AI/06_SECURITY.md`), only enough to pick the right plain-language,
/// localized copy.
enum SavedAddressErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The address doesn't exist, or isn't the caller's own (AC8) — the
  /// backend's `SavedAddressNotFoundError` never reveals which
  /// (`backend/app/core/exceptions/exceptions.py`).
  notFound,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language saved-address failure, thrown by
/// [SavedAddressRepository]. Carries only [type] — never the backend's raw
/// `message` string, an HTTP status code, or an internal error identifier.
class SavedAddressException implements Exception {
  const SavedAddressException({required this.type});

  final SavedAddressErrorType type;

  @override
  String toString() => 'SavedAddressException(type: $type)';
}
