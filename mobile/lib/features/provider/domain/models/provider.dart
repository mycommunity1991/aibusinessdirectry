import 'provider_type.dart';

/// One weekday's open/close time — mirrors the backend's
/// `OperatingHoursEntry` (`backend/app/modules/provider/schemas.py`, AC5).
class OperatingHoursEntry {
  const OperatingHoursEntry({required this.open, required this.close});

  factory OperatingHoursEntry.fromJson(Map<String, dynamic> json) {
    return OperatingHoursEntry(
      open: json['open'] as String,
      close: json['close'] as String,
    );
  }

  /// 24-hour "HH:MM", e.g. "09:00".
  final String open;

  /// 24-hour "HH:MM", e.g. "18:00".
  final String close;

  Map<String, dynamic> toJson() => {'open': open, 'close': close};
}

/// Mirrors the backend's `BusinessProfileResponse`.
class BusinessProfile {
  const BusinessProfile({
    required this.addressLine,
    this.city,
    this.region,
    required this.latitude,
    required this.longitude,
    this.operatingHours,
    this.deliveryRadiusMeters,
    this.tradeLicenseNumber,
  });

  factory BusinessProfile.fromJson(Map<String, dynamic> json) {
    final rawHours = json['operating_hours'] as Map<String, dynamic>?;
    return BusinessProfile(
      addressLine: json['address_line'] as String,
      city: json['city'] as String?,
      region: json['region'] as String?,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      operatingHours: rawHours?.map(
        (day, value) => MapEntry(
          day,
          value == null
              ? null
              : OperatingHoursEntry.fromJson(value as Map<String, dynamic>),
        ),
      ),
      deliveryRadiusMeters: (json['delivery_radius_meters'] as num?)?.toInt(),
      tradeLicenseNumber: json['trade_license_number'] as String?,
    );
  }

  final String addressLine;
  final String? city;
  final String? region;
  final double latitude;
  final double longitude;
  final Map<String, OperatingHoursEntry?>? operatingHours;
  final int? deliveryRadiusMeters;
  final String? tradeLicenseNumber;
}

/// Mirrors the backend's `FreelancerProfileResponse`.
class FreelancerProfile {
  const FreelancerProfile({
    required this.baseLatitude,
    required this.baseLongitude,
    required this.serviceRadiusMeters,
    this.skills,
    this.yearsExperience,
  });

  factory FreelancerProfile.fromJson(Map<String, dynamic> json) {
    return FreelancerProfile(
      baseLatitude: (json['base_latitude'] as num).toDouble(),
      baseLongitude: (json['base_longitude'] as num).toDouble(),
      serviceRadiusMeters: (json['service_radius_meters'] as num).toInt(),
      skills: (json['skills'] as List<dynamic>?)?.cast<String>(),
      yearsExperience: (json['years_experience'] as num?)?.toInt(),
    );
  }

  final double baseLatitude;
  final double baseLongitude;
  final int serviceRadiusMeters;
  final List<String>? skills;
  final int? yearsExperience;
}

/// A thin client-side model matching the backend's `ProviderResponse`
/// (`backend/app/modules/provider/schemas.py`, PRO-001) — returned by
/// `GET`/`POST /providers/me`.
class Provider {
  const Provider({
    required this.id,
    required this.providerType,
    required this.displayName,
    this.phoneCountryCode,
    this.phoneNumber,
    this.whatsappNumber,
    required this.categoryLabel,
    this.description,
    required this.slug,
    required this.verificationStatus,
    required this.isDiscoverable,
    required this.countryCode,
    this.businessProfile,
    this.freelancerProfile,
  });

  factory Provider.fromJson(Map<String, dynamic> json) {
    final businessProfileJson =
        json['business_profile'] as Map<String, dynamic>?;
    final freelancerProfileJson =
        json['freelancer_profile'] as Map<String, dynamic>?;
    return Provider(
      id: json['id'] as String,
      providerType: ProviderType.fromWire(json['provider_type'] as String),
      displayName: json['display_name'] as String,
      phoneCountryCode: json['phone_country_code'] as String?,
      phoneNumber: json['phone_number'] as String?,
      whatsappNumber: json['whatsapp_number'] as String?,
      categoryLabel: json['category_label'] as String,
      description: json['description'] as String?,
      slug: json['slug'] as String,
      verificationStatus: json['verification_status'] as String,
      isDiscoverable: json['is_discoverable'] as bool,
      countryCode: json['country_code'] as String,
      businessProfile: businessProfileJson == null
          ? null
          : BusinessProfile.fromJson(businessProfileJson),
      freelancerProfile: freelancerProfileJson == null
          ? null
          : FreelancerProfile.fromJson(freelancerProfileJson),
    );
  }

  final String id;
  final ProviderType providerType;
  final String displayName;
  final String? phoneCountryCode;
  final String? phoneNumber;
  final String? whatsappNumber;
  final String categoryLabel;
  final String? description;
  final String slug;

  /// Raw wire value ("pending"/"under_review"/"approved"/"rejected") — kept
  /// as a plain string since no screen in this story renders or branches
  /// on it (the Verification gate, VER-001, is out of scope here).
  final String verificationStatus;

  /// Always `false` on a freshly created provider (AC7) — flips to `true`
  /// only once VER-001's Verification gate approves it.
  final bool isDiscoverable;
  final String countryCode;
  final BusinessProfile? businessProfile;
  final FreelancerProfile? freelancerProfile;
}
