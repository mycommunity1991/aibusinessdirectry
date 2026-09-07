/// A thin client-side model matching the backend's `SavedAddressResponse`
/// (`backend/app/modules/customer/schemas.py`, CUS-002) — one row of
/// `GET`/`POST /customers/me/addresses` or `PATCH .../{address_id}`.
class SavedAddress {
  const SavedAddress({
    required this.id,
    this.label,
    required this.addressLine,
    this.city,
    this.region,
    required this.countryCode,
    required this.latitude,
    required this.longitude,
    required this.isDefault,
  });

  factory SavedAddress.fromJson(Map<String, dynamic> json) {
    return SavedAddress(
      id: json['id'] as String,
      label: json['label'] as String?,
      addressLine: json['address_line'] as String,
      city: json['city'] as String?,
      region: json['region'] as String?,
      countryCode: json['country_code'] as String,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      isDefault: json['is_default'] as bool,
    );
  }

  final String id;

  /// A short label, e.g. "Home", "Work" — optional.
  final String? label;
  final String addressLine;
  final String? city;
  final String? region;

  /// ISO 3166-1 alpha-2, e.g. "AE" — deliberately generic, not UAE-specific
  /// (`docs/AI/04_DATABASE.md`, `Plan_S03_CUS-002.md` Decision 5).
  final String countryCode;
  final double latitude;
  final double longitude;
  final bool isDefault;

  SavedAddress copyWith({bool? isDefault}) {
    return SavedAddress(
      id: id,
      label: label,
      addressLine: addressLine,
      city: city,
      region: region,
      countryCode: countryCode,
      latitude: latitude,
      longitude: longitude,
      isDefault: isDefault ?? this.isDefault,
    );
  }
}
