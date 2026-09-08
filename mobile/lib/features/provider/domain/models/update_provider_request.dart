import 'provider.dart';

/// Partial update of a Business Provider's subtype details for `PATCH
/// /providers/me` (PRO-002) -- mirrors the backend's
/// `UpdateBusinessDetailsRequest`. Same fields as `CreateBusinessDetails`,
/// all optional; deliberately excludes `country_code`, which is not
/// editable via this story's surface.
class UpdateBusinessDetails {
  const UpdateBusinessDetails({
    this.addressLine,
    this.city,
    this.region,
    this.latitude,
    this.longitude,
    this.operatingHours,
    this.deliveryRadiusMeters,
    this.tradeLicenseNumber,
  });

  final String? addressLine;
  final String? city;
  final String? region;
  final double? latitude;
  final double? longitude;

  /// Keyed by lowercase weekday name (e.g. "monday"); `null` for a closed
  /// day. When present, always the full 7-day map, matching the create-time
  /// convention.
  final Map<String, OperatingHoursEntry?>? operatingHours;
  final int? deliveryRadiusMeters;
  final String? tradeLicenseNumber;

  Map<String, dynamic> toJson() {
    return {
      if (addressLine != null) 'address_line': addressLine,
      if (city != null) 'city': city,
      if (region != null) 'region': region,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (operatingHours != null)
        'operating_hours': operatingHours!.map(
          (day, entry) => MapEntry(day, entry?.toJson()),
        ),
      if (deliveryRadiusMeters != null)
        'delivery_radius_meters': deliveryRadiusMeters,
      if (tradeLicenseNumber != null)
        'trade_license_number': tradeLicenseNumber,
    };
  }
}

/// Partial update of a Freelancer Provider's subtype details for `PATCH
/// /providers/me` (PRO-002) -- mirrors the backend's
/// `UpdateFreelancerDetailsRequest`. Same fields as
/// `CreateFreelancerDetails`, all optional; deliberately excludes
/// `country_code`.
class UpdateFreelancerDetails {
  const UpdateFreelancerDetails({
    this.baseLatitude,
    this.baseLongitude,
    this.serviceRadiusMeters,
    this.skills,
    this.yearsExperience,
  });

  final double? baseLatitude;
  final double? baseLongitude;
  final int? serviceRadiusMeters;
  final List<String>? skills;
  final int? yearsExperience;

  Map<String, dynamic> toJson() {
    return {
      if (baseLatitude != null) 'base_latitude': baseLatitude,
      if (baseLongitude != null) 'base_longitude': baseLongitude,
      if (serviceRadiusMeters != null)
        'service_radius_meters': serviceRadiusMeters,
      if (skills != null) 'skills': skills,
      if (yearsExperience != null) 'years_experience': yearsExperience,
    };
  }
}

/// Request payload for `PATCH /providers/me` (PRO-002, AC5) -- mirrors the
/// backend's `UpdateProviderRequest` exactly. Every field is optional and
/// only fields actually set here are sent (`toJson` omits unset fields) --
/// this is what makes each Storefront section independently saveable: a
/// section's Save action constructs a request containing only its own
/// fields, never another section's. `provider_type` is deliberately not a
/// field here at all -- it remains immutable (PRO-001, Decision 3).
class UpdateProviderRequest {
  const UpdateProviderRequest({
    this.displayName,
    this.phoneCountryCode,
    this.phoneNumber,
    this.whatsappNumber,
    this.description,
    this.categoryLabels,
    this.businessDetails,
    this.freelancerDetails,
  });

  final String? displayName;
  final String? phoneCountryCode;
  final String? phoneNumber;
  final String? whatsappNumber;
  final String? description;

  /// When present, replaces the provider's entire label set (Decision 1,
  /// `Plan_S04_PRO-002.md`) -- capped at 5, exactly one must be primary.
  final List<CategoryLabel>? categoryLabels;

  /// Rejected (400) by the backend if the provider's actual `provider_type`
  /// is not `business`.
  final UpdateBusinessDetails? businessDetails;

  /// Rejected (400) by the backend if the provider's actual `provider_type`
  /// is not `freelancer`.
  final UpdateFreelancerDetails? freelancerDetails;

  Map<String, dynamic> toJson() {
    return {
      if (displayName != null) 'display_name': displayName,
      if (phoneCountryCode != null) 'phone_country_code': phoneCountryCode,
      if (phoneNumber != null) 'phone_number': phoneNumber,
      if (whatsappNumber != null) 'whatsapp_number': whatsappNumber,
      if (description != null) 'description': description,
      if (categoryLabels != null)
        'category_labels': categoryLabels!
            .map((label) => label.toJson())
            .toList(),
      if (businessDetails != null)
        'business_details': businessDetails!.toJson(),
      if (freelancerDetails != null)
        'freelancer_details': freelancerDetails!.toJson(),
    };
  }
}
