/// Mirrors the backend's `DocumentType` enum
/// (`backend/app/modules/verification/models.py`, VER-001).
enum DocumentType {
  emiratesId,
  tradeLicense,
  other;

  /// The exact wire value the backend expects/returns.
  String get wireValue => switch (this) {
    DocumentType.emiratesId => 'emirates_id',
    DocumentType.tradeLicense => 'trade_license',
    DocumentType.other => 'other',
  };

  static DocumentType fromWire(String value) {
    return switch (value) {
      'emirates_id' => DocumentType.emiratesId,
      'trade_license' => DocumentType.tradeLicense,
      'other' => DocumentType.other,
      _ => throw ArgumentError('Unknown document_type: $value'),
    };
  }
}
