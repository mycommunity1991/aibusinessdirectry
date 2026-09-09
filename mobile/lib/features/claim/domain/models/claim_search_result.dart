/// Mirrors the backend's `ClaimSearchResultResponse`
/// (`backend/app/modules/provider/schemas.py`, CLM-001, AC3) -- one row of
/// `GET /claims/search`.
class ClaimSearchResult {
  const ClaimSearchResult({
    required this.id,
    required this.displayName,
    this.addressLine,
    this.city,
    this.phoneNumberMasked,
  });

  factory ClaimSearchResult.fromJson(Map<String, dynamic> json) {
    return ClaimSearchResult(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      addressLine: json['address_line'] as String?,
      city: json['city'] as String?,
      // Never the raw phone number -- only a pre-masked string (e.g.
      // "+971 5*****67") so a searcher can sanity-check "is this my
      // number" without it being exposed to anyone who merely searched
      // (backend `_mask_phone_number`). `null` if the listing has no
      // public number on record at all.
      phoneNumberMasked: json['phone_number_masked'] as String?,
    );
  }

  final String id;
  final String displayName;
  final String? addressLine;
  final String? city;
  final String? phoneNumberMasked;
}
