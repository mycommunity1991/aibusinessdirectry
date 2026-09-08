import 'provider.dart';
import 'provider_type.dart';

/// Business-subtype details for `POST /providers/me` — mirrors the
/// backend's `CreateBusinessDetailsRequest`
/// (`backend/app/modules/provider/schemas.py`, AC5).
class CreateBusinessDetails {
  const CreateBusinessDetails({
    required this.addressLine,
    this.city,
    this.region,
    required this.countryCode,
    required this.latitude,
    required this.longitude,
    this.operatingHours,
    this.deliveryRadiusMeters,
    this.tradeLicenseNumber,
  });

  final String addressLine;
  final String? city;
  final String? region;

  /// ISO 3166-1 alpha-2, e.g. "AE" — reverse-geocoded client-side via
  /// `LocationPickerScreen` (Decision 6, `Plan_S04_PRO-001.md`).
  final String countryCode;
  final double latitude;
  final double longitude;

  /// Keyed by lowercase weekday name (e.g. "monday"); `null` for a closed
  /// day. `null` (the whole map) if the user never set any hours.
  final Map<String, OperatingHoursEntry?>? operatingHours;
  final int? deliveryRadiusMeters;
  final String? tradeLicenseNumber;

  Map<String, dynamic> toJson() {
    return {
      'address_line': addressLine,
      'city': ?city,
      'region': ?region,
      'country_code': countryCode,
      'latitude': latitude,
      'longitude': longitude,
      if (operatingHours != null)
        'operating_hours': operatingHours!.map(
          (day, entry) => MapEntry(day, entry?.toJson()),
        ),
      'delivery_radius_meters': ?deliveryRadiusMeters,
      'trade_license_number': ?tradeLicenseNumber,
    };
  }
}

/// Freelancer-subtype details for `POST /providers/me` — mirrors the
/// backend's `CreateFreelancerDetailsRequest`
/// (`backend/app/modules/provider/schemas.py`, AC6).
class CreateFreelancerDetails {
  const CreateFreelancerDetails({
    required this.baseLatitude,
    required this.baseLongitude,
    required this.countryCode,
    required this.serviceRadiusMeters,
    this.skills,
    this.yearsExperience,
  });

  final double baseLatitude;
  final double baseLongitude;

  /// ISO 3166-1 alpha-2 -- flows to `providers.country_code` only, not
  /// persisted on `freelancer_profiles` (Decision 6, `Plan_S04_PRO-001.md`).
  final String countryCode;
  final int serviceRadiusMeters;
  final List<String>? skills;
  final int? yearsExperience;

  Map<String, dynamic> toJson() {
    return {
      'base_latitude': baseLatitude,
      'base_longitude': baseLongitude,
      'country_code': countryCode,
      'service_radius_meters': serviceRadiusMeters,
      'skills': ?skills,
      'years_experience': ?yearsExperience,
    };
  }
}

/// Request payload for `POST /providers/me` — mirrors the backend's
/// `CreateProviderRequest` exactly. Submitted exactly once, at the end of
/// the mobile onboarding wizard (Decision 2, `Plan_S04_PRO-001.md`).
class CreateProviderRequest {
  CreateProviderRequest({
    required this.providerType,
    required this.displayName,
    required this.phoneCountryCode,
    required this.phoneNumber,
    this.whatsappNumber,
    required this.categoryLabel,
    this.description,
    this.businessDetails,
    this.freelancerDetails,
  }) : assert(
         (providerType == ProviderType.business) == (businessDetails != null),
         'businessDetails must be set if and only if providerType is business',
       ),
       assert(
         (providerType == ProviderType.freelancer) ==
             (freelancerDetails != null),
         'freelancerDetails must be set if and only if providerType is '
         'freelancer',
       );

  final ProviderType providerType;
  final String displayName;
  final String phoneCountryCode;
  final String phoneNumber;
  final String? whatsappNumber;

  /// Free-text category, e.g. "Plumbing" (Decision 4, `Plan_S04_PRO-001.md`
  /// -- a temporary stand-in for the not-yet-built Category domain).
  final String categoryLabel;
  final String? description;
  final CreateBusinessDetails? businessDetails;
  final CreateFreelancerDetails? freelancerDetails;

  Map<String, dynamic> toJson() {
    return {
      'provider_type': providerType.wireValue,
      'display_name': displayName,
      'phone_country_code': phoneCountryCode,
      'phone_number': phoneNumber,
      'whatsapp_number': ?whatsappNumber,
      'category_label': categoryLabel,
      'description': ?description,
      if (businessDetails != null)
        'business_details': businessDetails!.toJson(),
      if (freelancerDetails != null)
        'freelancer_details': freelancerDetails!.toJson(),
    };
  }
}
