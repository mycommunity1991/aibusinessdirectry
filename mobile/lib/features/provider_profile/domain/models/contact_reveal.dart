/// Mirrors the backend's `ContactViewRevealResponse`
/// (`backend/app/modules/contact/schemas.py`, CON-001, AC2) --
/// `POST /contact-views`'s success payload: the Contact Reveal sheet's
/// data, shown immediately with no quote/approval/messaging step in
/// between.
class ContactReveal {
  const ContactReveal({
    required this.id,
    required this.providerId,
    required this.providerDisplayName,
    this.phoneCountryCode,
    this.phoneNumber,
    this.whatsappNumber,
  });

  factory ContactReveal.fromJson(Map<String, dynamic> json) {
    return ContactReveal(
      id: json['id'] as String,
      providerId: json['provider_id'] as String,
      providerDisplayName: json['provider_display_name'] as String,
      phoneCountryCode: json['phone_country_code'] as String?,
      phoneNumber: json['phone_number'] as String?,
      whatsappNumber: json['whatsapp_number'] as String?,
    );
  }

  final String id;
  final String providerId;
  final String providerDisplayName;

  /// e.g. `"+971"`.
  final String? phoneCountryCode;
  final String? phoneNumber;

  /// `null` when the provider has no WhatsApp number on record -- the
  /// Contact Reveal sheet's WhatsApp button is only shown when this is
  /// non-null (AC2).
  final String? whatsappNumber;

  /// The country code and local number concatenated for display and the
  /// `tel:` Call button, e.g. `"+971 501234567"` -- `null` only if either
  /// half is missing (should be unreachable in practice: a Provider row
  /// with no phone number could never have been a valid Contact target).
  String? get fullPhoneNumber {
    final code = phoneCountryCode;
    final number = phoneNumber;
    if (code == null || number == null) return null;
    return '$code $number';
  }
}
