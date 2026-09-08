import 'document_type.dart';

/// The user's final, possibly-edited values for `POST
/// /providers/me/verification` -- mirrors the backend's
/// `SubmitVerificationRequest`/`ConfirmedFieldsInput`
/// (`backend/app/modules/verification/schemas.py`).
///
/// Deliberately has **no** `status`, `reviewed_at`, `reviewed_by`, or
/// `rejection_reason` field -- there is no field on this request through
/// which a caller could even attempt to set them (AC6).
class SubmitVerificationRequest {
  const SubmitVerificationRequest({
    this.documentType,
    this.fullName,
    this.idNumber,
    this.expiryDate,
  });

  /// `null` for a Business submission with no document (AC2/Decision 3);
  /// always set for a Freelancer submission (always `emiratesId`).
  final DocumentType? documentType;

  /// The user's **submitted, edited** values -- not necessarily equal to
  /// whatever the (always-empty) preview response returned (AC8).
  final String? fullName;
  final String? idNumber;
  final String? expiryDate;

  Map<String, dynamic> toJson() {
    return {
      'document_type': ?documentType?.wireValue,
      'confirmed_fields': {
        'full_name': ?fullName,
        'id_number': ?idNumber,
        'expiry_date': ?expiryDate,
      },
    };
  }
}
