import '../../../../shared/models/provider_type.dart';

/// Mirrors the backend's `SearchResultProviderResponse`
/// (`backend/app/modules/search/schemas.py`, DIR-001) -- one row of
/// `GET /search/providers`.
///
/// Uses [ProviderType] from `shared/models/` rather than importing
/// `features/provider/` directly -- `features/search/` must never depend on
/// another feature module directly (`docs/AI/02_ARCHITECTURE.md`; the same
/// cross-feature-coupling bug VER-001's review caught and fixed by moving
/// `ProviderType` into `shared/models/` in the first place).
class SearchResultProvider {
  const SearchResultProvider({
    required this.id,
    required this.displayName,
    required this.slug,
    required this.providerType,
    this.categoryLabels = const [],
    this.primaryPhotoUrl,
    this.averageRating,
    required this.reviewCount,
    required this.distanceMeters,
  });

  factory SearchResultProvider.fromJson(Map<String, dynamic> json) {
    return SearchResultProvider(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      slug: json['slug'] as String,
      providerType: ProviderType.fromWire(json['provider_type'] as String),
      categoryLabels:
          (json['category_labels'] as List<dynamic>?)?.cast<String>() ??
          const [],
      primaryPhotoUrl: json['primary_photo_url'] as String?,
      // Decision 2 (`Plan_S06_DIR-001.md`): `average_rating` is honestly
      // `null` until a Review domain exists -- never synthesized as `0.0`
      // here or anywhere downstream.
      averageRating: (json['average_rating'] as num?)?.toDouble(),
      reviewCount: (json['review_count'] as num).toInt(),
      distanceMeters: (json['distance_meters'] as num).toDouble(),
    );
  }

  final String id;
  final String displayName;
  final String slug;
  final ProviderType providerType;
  final List<String> categoryLabels;

  /// A relative, served URL path (e.g. `/media/portfolios/...`), or `null`
  /// if the provider has no portfolio photos -- resolve against
  /// `ApiConfig.mediaOrigin`, exactly like `PortfolioPhoto.mediaUrl`.
  final String? primaryPhotoUrl;

  /// `null` for essentially every provider today (no Review domain exists
  /// yet, Decision 2) -- rendering must show "No reviews yet" in that case,
  /// never a synthesized `0.0`. See `provider_search_card.dart`.
  final double? averageRating;
  final int reviewCount;

  /// Great-circle distance from the search origin, in meters.
  final double distanceMeters;
}
