import '../../../provider/domain/models/weekday_availability.dart';
import '../../../../shared/models/provider_type.dart';

/// Mirrors the backend's `PublicProviderProfileResponse`
/// (`backend/app/modules/provider/schemas.py`, CON-001, AC5, Decision 2) --
/// `GET /providers/{provider_id}`'s payload, the Provider Profile screen's
/// (S-09) data.
///
/// [categoryLabels] carries only each label's text (mirrors
/// `RankedProviderResult.categoryLabels`'s `List<String>` shape) --
/// `is_primary` isn't needed for this screen's plain "Plumbing • Cleaning"
/// display.
///
/// Deliberately has no `phoneNumber`/`whatsappNumber` field at all -- the
/// backend response this model mirrors never sends them; those are only
/// ever revealed via the separate Contact Reveal flow
/// (`domain/models/contact_reveal.dart`, `POST /contact-views`, AC2).
class ProviderProfile {
  const ProviderProfile({
    required this.id,
    required this.providerType,
    required this.displayName,
    this.categoryLabels = const [],
    this.description,
    this.primaryPhotoUrl,
    this.averageRating,
    required this.reviewCount,
    required this.isClaimed,
    required this.verificationStatus,
    this.weeklyAvailability = const [],
    this.city,
    this.region,
    this.deliveryRadiusMeters,
    this.serviceRadiusMeters,
  });

  factory ProviderProfile.fromJson(Map<String, dynamic> json) {
    final categoryLabelsJson =
        json['category_labels'] as List<dynamic>? ?? const [];
    final availabilityJson =
        json['weekly_availability'] as List<dynamic>? ?? const [];
    return ProviderProfile(
      id: json['id'] as String,
      providerType: ProviderType.fromWire(json['provider_type'] as String),
      displayName: json['display_name'] as String,
      categoryLabels: categoryLabelsJson
          .cast<Map<String, dynamic>>()
          .map((label) => label['label'] as String)
          .toList(),
      description: json['description'] as String?,
      primaryPhotoUrl: json['primary_photo_url'] as String?,
      averageRating: (json['average_rating'] as num?)?.toDouble(),
      reviewCount: (json['review_count'] as num).toInt(),
      isClaimed: json['is_claimed'] as bool,
      verificationStatus: json['verification_status'] as String,
      weeklyAvailability: availabilityJson
          .cast<Map<String, dynamic>>()
          .map(WeekdayAvailability.fromJson)
          .toList(),
      city: json['city'] as String?,
      region: json['region'] as String?,
      deliveryRadiusMeters: (json['delivery_radius_meters'] as num?)?.toInt(),
      serviceRadiusMeters: (json['service_radius_meters'] as num?)?.toInt(),
    );
  }

  final String id;
  final ProviderType providerType;
  final String displayName;
  final List<String> categoryLabels;
  final String? description;

  /// A relative, served URL path -- resolve against
  /// `ApiConfig.mediaOrigin`, mirroring `RankedProviderResult.
  /// primaryPhotoUrl`. `null` if the provider has no portfolio photos.
  final String? primaryPhotoUrl;

  /// `null` for essentially every provider today (no Review domain exists
  /// yet) -- rendering must show "No reviews yet", never a synthesized
  /// `0.0` (AC5).
  final double? averageRating;
  final int reviewCount;

  /// Raw, server-driven boolean (Decision 8) -- checked *before*
  /// [verificationStatus] when deciding which trust badge (if any) to
  /// render, since a still-unclaimed, Google-seeded listing can have
  /// `verification_status=approved` too.
  final bool isClaimed;

  /// The provider's raw wire verification-status string (`pending`/
  /// `under_review`/`approved`/`rejected`) -- carried through unmodified,
  /// mirroring `ClaimResult.verificationStatus`'s own convention, rather
  /// than a duplicate local enum. Never rendered directly; only consulted
  /// via [isVerified].
  final String verificationStatus;

  final List<WeekdayAvailability> weeklyAvailability;

  /// Business-only (`freelancer_profiles` has neither field).
  final String? city;
  final String? region;

  /// Populated only for `provider_type=business`.
  final int? deliveryRadiusMeters;

  /// Populated only for `provider_type=freelancer`.
  final int? serviceRadiusMeters;

  /// Decision 8's second precedence state: `is_claimed == true &&
  /// verification_status == approved`. Only meaningful to check once
  /// [isClaimed] is already known `true` -- the Provider Profile screen
  /// checks [isClaimed] first (rendering the shared `UnclaimedBanner`
  /// instead, regardless of [verificationStatus]) and only falls through to
  /// this getter otherwise, exactly mirroring Decision 8's three-state
  /// precedence.
  bool get isVerified => isClaimed && verificationStatus == 'approved';
}
