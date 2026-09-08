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

  /// The caller's provider listing (or, for a portfolio-photo id, the
  /// specific photo) could not be found (backend 404 -- `ProviderNot
  /// FoundError`/`PortfolioPhotoNotFoundError`, PRO-002). The latter
  /// deliberately collapses "doesn't exist" and "not owned by the caller"
  /// into the same case (ADR-015) -- the UI never distinguishes them.
  notFound,

  /// An uploaded portfolio photo failed size/extension/MIME validation
  /// (backend 422 `InvalidPortfolioUploadError`, PRO-002, AC2).
  invalidUpload,

  /// The caller already has the maximum number of portfolio photos
  /// (backend 409 `PortfolioLimitExceededError`, PRO-002).
  portfolioLimitExceeded,

  /// A portfolio reorder request's id set didn't exactly match the
  /// caller's own active photos (backend 422
  /// `InvalidPortfolioReorderError`, PRO-002, Decision 4).
  invalidReorder,

  /// A `category_labels` replace payload had zero or more than one primary
  /// label, or exceeded the 5-label cap (backend 422
  /// `InvalidCategoryLabelsError`, PRO-002, AC4).
  invalidCategoryLabels,

  /// The submitted `business_details`/`freelancer_details` object didn't
  /// match the provider's actual `provider_type` (backend 400
  /// `SubtypeDetailsMismatchError`, PRO-002) -- should be unreachable from
  /// the real UI (each section only ever submits its own provider's
  /// subtype), kept only for defensive completeness.
  subtypeMismatch,

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
