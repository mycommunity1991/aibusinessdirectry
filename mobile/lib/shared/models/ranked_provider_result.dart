import 'provider_type.dart';

/// One ranked provider result row, shared by two backend response shapes
/// that are otherwise identical except for whether `distance_meters` can be
/// `null`:
///
/// - `GET /search/providers` (DIR-001, `SearchResultProviderResponse`) --
///   `distance_meters` is always present (a search origin always exists).
/// - `GET /search-requests/{id}` (AI-002, `MatchedProviderResponse`,
///   `Plan_S07_AI-002.md` Decision 6) -- `distance_meters` is nullable,
///   `null` only when the customer had no default saved address to match
///   against (Decision 2c), never estimated.
///
/// This shared, nullable-superset shape lives in `shared/models/` (not
/// either feature) so `features/search` and `features/conversation` can
/// both render results through the same `shared/widgets/
/// ranked_provider_results_list.dart` widget without one feature importing
/// the other's screen/widget file directly (`13_OPEN_DECISIONS.md` item 12
/// -- this must not become a third instance of that same debt).
class RankedProviderResult {
  const RankedProviderResult({
    required this.id,
    required this.displayName,
    required this.slug,
    required this.providerType,
    this.categoryLabels = const [],
    this.primaryPhotoUrl,
    this.averageRating,
    required this.reviewCount,
    this.distanceMeters,
    required this.isClaimed,
  });

  /// Parses `MatchedProviderResponse` (AI-002, `GET /search-requests/{id}`)
  /// -- this endpoint's shape is this class's native, nullable-distance
  /// shape, so no separate feature-owned model is needed for it.
  factory RankedProviderResult.fromJson(Map<String, dynamic> json) {
    return RankedProviderResult(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      slug: json['slug'] as String,
      providerType: ProviderType.fromWire(json['provider_type'] as String),
      categoryLabels:
          (json['category_labels'] as List<dynamic>?)?.cast<String>() ??
          const [],
      primaryPhotoUrl: json['primary_photo_url'] as String?,
      averageRating: (json['average_rating'] as num?)?.toDouble(),
      reviewCount: (json['review_count'] as num).toInt(),
      distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
      isClaimed: json['is_claimed'] as bool,
    );
  }

  final String id;
  final String displayName;
  final String slug;
  final ProviderType providerType;
  final List<String> categoryLabels;

  /// A relative, served URL path (e.g. `/media/portfolios/...`), or `null`
  /// if the provider has no portfolio photos -- resolve against
  /// `ApiConfig.mediaOrigin`.
  final String? primaryPhotoUrl;

  /// `null` for essentially every provider today (no Review domain exists
  /// yet) -- rendering must show "No reviews yet" in that case, never a
  /// synthesized `0.0`.
  final double? averageRating;
  final int reviewCount;

  /// Great-circle distance from the search origin, in meters -- `null` only
  /// when no origin/provider location could be resolved (AI-002, Decision
  /// 2c), never estimated.
  final double? distanceMeters;

  /// `false` for a still-unclaimed Google-seeded listing (CLM-001, Decision
  /// 8) -- drives the shared unclaimed banner. Server-driven off this one
  /// boolean; never inferred client-side from any other field.
  final bool isClaimed;
}
