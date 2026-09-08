import 'document_type.dart';

/// One document attached to a verification cycle -- mirrors the backend's
/// `VerificationDocumentResponse`
/// (`backend/app/modules/verification/schemas.py`, VER-001).
///
/// Deliberately does **not** keep the backend's `file_download_url` field
/// as a directly-usable URL -- the document is private (Decision 7,
/// `Plan_S05_VER-001.md`) and only ever fetched through
/// `VerificationRepository.getDocumentBytes(id)`, which attaches the
/// caller's bearer token via the app's existing Dio client. No screen in
/// this feature ever constructs a raw `Image.network`/direct-URL call
/// against a verification document.
class VerificationDocument {
  const VerificationDocument({
    required this.id,
    required this.documentType,
    this.ocrExtractedData,
  });

  factory VerificationDocument.fromJson(Map<String, dynamic> json) {
    final rawData = json['ocr_extracted_data'] as Map<String, dynamic>?;
    return VerificationDocument(
      id: json['id'] as String,
      documentType: DocumentType.fromWire(json['document_type'] as String),
      ocrExtractedData: rawData?.map(
        (key, value) => MapEntry(key, value as String?),
      ),
    );
  }

  final String id;
  final DocumentType documentType;

  /// The caller's own **submitted, confirmed** `full_name`/`id_number`/
  /// `expiry_date` fields (AC8) -- never the OCR stub's raw preview
  /// output, which is always empty (Decision 6).
  final Map<String, String?>? ocrExtractedData;
}
