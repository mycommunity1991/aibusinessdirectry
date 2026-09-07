/// The result of a successful pick from [LocationPickerScreen] — plain
/// coordinates plus a best-effort reverse-geocoded address, deliberately
/// generic (no Customer-domain field names or types) so a future
/// Provider-domain business/freelancer location screen (S-18a/b, not this
/// story) can reuse [LocationPickerScreen] without adaptation
/// (`Plan_S03_CUS-002.md` Decision 7).
class LocationPickResult {
  const LocationPickResult({
    required this.latitude,
    required this.longitude,
    this.addressLine,
    this.city,
    this.region,
    this.countryCode,
  });

  final double latitude;
  final double longitude;

  /// A best-effort street-level address line, if reverse geocoding found
  /// one — always further user-editable by the caller, never authoritative.
  final String? addressLine;
  final String? city;
  final String? region;

  /// ISO 3166-1 alpha-2, if reverse geocoding found one.
  final String? countryCode;
}
