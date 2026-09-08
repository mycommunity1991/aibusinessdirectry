import 'verification_document.dart';

/// Mirrors the backend's four-value `verification_status` Postgres enum
/// (reused, not duplicated, from the Provider domain -- Decision 1,
/// `Plan_S05_VER-001.md`). `pending`/`underReview` both render as "we're
/// reviewing your documents" per `docs/AI/16_UX_GUIDELINES.md`'s
/// internal-to-user-facing copy mapping table.
enum VerificationRecordStatus {
  pending,
  underReview,
  approved,
  rejected;

  static VerificationRecordStatus fromWire(String value) {
    return switch (value) {
      'pending' => VerificationRecordStatus.pending,
      'under_review' => VerificationRecordStatus.underReview,
      'approved' => VerificationRecordStatus.approved,
      'rejected' => VerificationRecordStatus.rejected,
      _ => throw ArgumentError('Unknown verification status: $value'),
    };
  }
}

/// The caller's own latest verification cycle -- mirrors the backend's
/// `VerificationRecordResponse` (`GET /providers/me/verification`,
/// VER-001, AC6). The backend scopes every lookup to the caller's own
/// provider, so this is never another account's data.
class VerificationRecord {
  const VerificationRecord({
    required this.id,
    required this.status,
    required this.submittedAt,
    this.reviewedAt,
    this.rejectionReason,
    this.documents = const [],
  });

  factory VerificationRecord.fromJson(Map<String, dynamic> json) {
    final documentsJson = json['documents'] as List<dynamic>?;
    return VerificationRecord(
      id: json['id'] as String,
      status: VerificationRecordStatus.fromWire(json['status'] as String),
      submittedAt: DateTime.parse(json['submitted_at'] as String),
      reviewedAt: json['reviewed_at'] == null
          ? null
          : DateTime.parse(json['reviewed_at'] as String),
      rejectionReason: json['rejection_reason'] as String?,
      documents:
          documentsJson
              ?.map(
                (item) =>
                    VerificationDocument.fromJson(item as Map<String, dynamic>),
              )
              .toList() ??
          const [],
    );
  }

  final String id;
  final VerificationRecordStatus status;
  final DateTime submittedAt;
  final DateTime? reviewedAt;

  /// Plain-language rejection reason, set by a future VER-002 admin
  /// review -- out of this story's scope to write, only to display.
  final String? rejectionReason;
  final List<VerificationDocument> documents;
}
