import 'dart:io';

import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/document_type.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/ocr_preview_result.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/submit_verification_request.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_exception.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_record.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [VerificationRepository] -- no real Dio/
/// network calls are ever made. Mirrors `fake_provider_repository.dart`'s
/// pattern: each method records its own call count and last-request
/// payload so a test can assert precisely what was sent without
/// inspecting raw JSON.
class FakeVerificationRepository extends VerificationRepository {
  FakeVerificationRepository({
    VerificationRecord? existingRecord,
    Map<String, List<int>>? documentBytesById,
    this.previewDocumentError,
    this.previewResult,
    this.submitError,
    this.getMyCurrentStatusError,
    this.getDocumentBytesError,
  }) : _record = existingRecord,
       _documentBytesById = documentBytesById ?? const {},
       super(Dio());

  VerificationRecord? _record;
  final Map<String, List<int>> _documentBytesById;

  /// The failure `previewDocument` throws, if any.
  final VerificationException? previewDocumentError;

  /// The result `previewDocument` returns, if [previewDocumentError] is
  /// `null` -- defaults to an all-empty result matching the real
  /// backend's `StubDocumentOcrService` (Decision 6, `Plan_S05_
  /// VER-001.md`) when not otherwise supplied.
  final OcrPreviewResult? previewResult;

  /// The failure `submit` throws, if any.
  final VerificationException? submitError;

  /// The failure `getMyCurrentStatus` throws, if any (never used for the
  /// plain "never submitted" case -- that's represented by `_record ==
  /// null` returning `null`, not an exception, mirroring
  /// `getMyProvider()`'s null-on-404 convention).
  final VerificationException? getMyCurrentStatusError;

  /// The failure `getDocumentBytes` throws, if any.
  final VerificationException? getDocumentBytesError;

  int previewDocumentCallCount = 0;
  int submitCallCount = 0;
  int getMyCurrentStatusCallCount = 0;
  int getDocumentBytesCallCount = 0;

  DocumentType? lastPreviewedDocumentType;
  File? lastPreviewedFile;

  /// The exact request passed to the most recent `submit` call -- lets a
  /// test assert precisely what was submitted, e.g. that it reflects the
  /// user's edits rather than the (empty) preview response (AC8).
  SubmitVerificationRequest? lastSubmitRequest;

  String? lastRequestedDocumentId;

  @override
  Future<OcrPreviewResult> previewDocument(
    File file,
    DocumentType documentType,
  ) async {
    previewDocumentCallCount++;
    lastPreviewedFile = file;
    lastPreviewedDocumentType = documentType;
    if (previewDocumentError != null) {
      throw previewDocumentError!;
    }
    return previewResult ??
        OcrPreviewResult(documentType: documentType, confidence: 0);
  }

  @override
  Future<VerificationRecord> submit(SubmitVerificationRequest request) async {
    submitCallCount++;
    lastSubmitRequest = request;
    if (submitError != null) {
      throw submitError!;
    }
    final created = VerificationRecord(
      id: 'verification-record-$submitCallCount',
      status: VerificationRecordStatus.pending,
      submittedAt: DateTime.utc(2026, 1, 1),
    );
    _record = created;
    return created;
  }

  @override
  Future<VerificationRecord?> getMyCurrentStatus() async {
    getMyCurrentStatusCallCount++;
    if (getMyCurrentStatusError != null) {
      throw getMyCurrentStatusError!;
    }
    return _record;
  }

  @override
  Future<List<int>> getDocumentBytes(String documentId) async {
    getDocumentBytesCallCount++;
    lastRequestedDocumentId = documentId;
    if (getDocumentBytesError != null) {
      throw getDocumentBytesError!;
    }
    return _documentBytesById[documentId] ?? const [];
  }
}

/// A representative pending record, for tests that need a
/// [FakeVerificationRepository] pre-seeded with an in-review cycle.
VerificationRecord fakePendingRecord({String id = 'record-pending'}) {
  return VerificationRecord(
    id: id,
    status: VerificationRecordStatus.pending,
    submittedAt: DateTime.utc(2026, 1, 1),
  );
}

/// A representative under_review record.
VerificationRecord fakeUnderReviewRecord({String id = 'record-under-review'}) {
  return VerificationRecord(
    id: id,
    status: VerificationRecordStatus.underReview,
    submittedAt: DateTime.utc(2026, 1, 1),
  );
}

/// A representative approved record.
VerificationRecord fakeApprovedRecord({String id = 'record-approved'}) {
  return VerificationRecord(
    id: id,
    status: VerificationRecordStatus.approved,
    submittedAt: DateTime.utc(2026, 1, 1),
    reviewedAt: DateTime.utc(2026, 1, 2),
  );
}

/// A representative rejected record, with a plain-language reason.
VerificationRecord fakeRejectedRecord({
  String id = 'record-rejected',
  String? rejectionReason,
}) {
  return VerificationRecord(
    id: id,
    status: VerificationRecordStatus.rejected,
    submittedAt: DateTime.utc(2026, 1, 1),
    reviewedAt: DateTime.utc(2026, 1, 2),
    rejectionReason: rejectionReason ?? 'The document was too blurry to read.',
  );
}
