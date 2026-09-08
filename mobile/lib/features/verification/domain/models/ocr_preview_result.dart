import 'document_type.dart';

/// The (stubbed, Decision 6 `Plan_S05_VER-001.md`) OCR pass's candidate
/// fields -- mirrors the backend's `VerificationPreviewResponse`.
///
/// Every field is always `null`/`0.0` today -- the OCR pipeline never
/// actually reads the document. The confirm screen must present these as
/// editable, provisional inputs the user fills in themselves ("we
/// couldn't read this automatically yet"), never as an already-completed
/// read (AC4) -- see `verification_confirm_screen.dart`.
class OcrPreviewResult {
  const OcrPreviewResult({
    required this.documentType,
    this.fullName,
    this.idNumber,
    this.expiryDate,
    required this.confidence,
  });

  factory OcrPreviewResult.fromJson(Map<String, dynamic> json) {
    return OcrPreviewResult(
      documentType: DocumentType.fromWire(json['document_type'] as String),
      fullName: json['full_name'] as String?,
      idNumber: json['id_number'] as String?,
      expiryDate: json['expiry_date'] as String?,
      confidence: (json['confidence'] as num).toDouble(),
    );
  }

  final DocumentType documentType;
  final String? fullName;
  final String? idNumber;

  /// ISO `YYYY-MM-DD`, kept as a raw string -- the confirm screen edits it
  /// as free text; there is no round trip to a real `DateTime` needed for
  /// an always-empty stub value (Decision 6).
  final String? expiryDate;

  /// Always `0.0` today -- `StubDocumentOcrService` never guesses.
  final double confidence;
}
