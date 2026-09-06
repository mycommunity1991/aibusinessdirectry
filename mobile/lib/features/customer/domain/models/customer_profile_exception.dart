/// The category of failure behind a [CustomerProfileException].
///
/// Deliberately coarse-grained, mirroring
/// `features/auth/domain/models/auth_exception.dart`'s [AuthErrorType]: the
/// UI layer never needs a raw HTTP status code or backend error identifier
/// (`docs/AI/06_SECURITY.md`), only enough to pick the right plain-language,
/// localized copy (see `presentation/utils/customer_error_copy.dart`).
enum CustomerProfileErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// Anything else (validation, 401/403 the screen shouldn't normally hit
  /// since it's only reachable while authenticated, 5xx, or an
  /// unrecognized shape).
  unknown,
}

/// A plain-language customer-profile failure, thrown by
/// [CustomerRepository]. Carries only [type] — never the backend's raw
/// `message` string, an HTTP status code, or an internal error identifier.
class CustomerProfileException implements Exception {
  const CustomerProfileException({required this.type});

  final CustomerProfileErrorType type;

  @override
  String toString() => 'CustomerProfileException(type: $type)';
}
