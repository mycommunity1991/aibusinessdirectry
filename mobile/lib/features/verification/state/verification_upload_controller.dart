import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/data/current_provider_type_repository.dart';
import '../../../shared/models/provider_type.dart';
import '../data/verification_repository.dart';
import '../domain/models/document_type.dart';
import '../domain/models/ocr_preview_result.dart';
import '../domain/models/submit_verification_request.dart';
import '../domain/models/verification_exception.dart';

/// S-19's draft state: the caller's own `provider_type` (read-only, to
/// gate document-type choice -- Freelancer must submit an Emirates ID,
/// no choice; Business may choose, or skip per AC2/Decision 3), the
/// in-progress document pick, and the preview/submit-without-document
/// in-flight state.
class VerificationUploadState {
  const VerificationUploadState({
    this.providerType,
    this.isLoadingProviderType = true,
    this.documentType = DocumentType.emiratesId,
    this.pickedFile,
    this.skipDocument = false,
    this.isBusy = false,
    this.error,
  });

  final ProviderType? providerType;
  final bool isLoadingProviderType;
  final DocumentType documentType;
  final File? pickedFile;

  /// Business-only (AC2/Decision 3) -- submits with no document at all.
  final bool skipDocument;

  final bool isBusy;
  final VerificationException? error;

  bool get isFreelancer => providerType == ProviderType.freelancer;

  VerificationUploadState copyWith({
    ProviderType? providerType,
    bool? isLoadingProviderType,
    DocumentType? documentType,
    File? pickedFile,
    bool? skipDocument,
    bool? isBusy,
    VerificationException? error,
    bool clearError = false,
  }) {
    return VerificationUploadState(
      providerType: providerType ?? this.providerType,
      isLoadingProviderType:
          isLoadingProviderType ?? this.isLoadingProviderType,
      documentType: documentType ?? this.documentType,
      pickedFile: pickedFile ?? this.pickedFile,
      skipDocument: skipDocument ?? this.skipDocument,
      isBusy: isBusy ?? this.isBusy,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages S-19 (Verification Upload)'s document-type gating and
/// preview/submit-without-document actions (`Plan_S05_VER-001.md` items
/// 27/31).
///
/// Reads the caller's own `provider_type` via the shared
/// [CurrentProviderTypeRepository] (`shared/data/`, not `features/
/// provider/`) -- keeping this feature module free of any direct
/// dependency on `features/provider/` (`docs/AI/02_ARCHITECTURE.md`:
/// "Features must not depend directly on each other. Shared
/// functionality belongs in shared modules.").
class VerificationUploadController
    extends StateNotifier<VerificationUploadState> {
  VerificationUploadController(
    this._verificationRepository,
    this._currentProviderTypeRepository,
  ) : super(const VerificationUploadState()) {
    _loadProviderType();
  }

  final VerificationRepository _verificationRepository;
  final CurrentProviderTypeRepository _currentProviderTypeRepository;

  Future<void> _loadProviderType() async {
    // `getMyProviderType()` never throws (it resolves to `null` on any
    // 404/parse failure, defensive only -- unreachable via the real UI,
    // since this screen is only ever reached once a provider listing
    // already exists, either right after PRO-001's onboarding wizard or
    // from the Storefront's verification-status link), so no try/catch
    // is needed here.
    final providerType = await _currentProviderTypeRepository
        .getMyProviderType();
    state = state.copyWith(
      providerType: providerType,
      isLoadingProviderType: false,
      documentType: providerType == ProviderType.freelancer
          ? DocumentType.emiratesId
          : state.documentType,
    );
  }

  /// Freelancer's document type is fixed (`emiratesId`, AC2) -- a no-op
  /// while [VerificationUploadState.isFreelancer] is true.
  void setDocumentType(DocumentType type) {
    if (state.isFreelancer) return;
    state = state.copyWith(documentType: type, skipDocument: false);
  }

  void setPickedFile(File file) {
    state = state.copyWith(
      pickedFile: file,
      skipDocument: false,
      clearError: true,
    );
  }

  /// Business-only (AC2/Decision 3) -- a Freelancer can never skip.
  void setSkipDocument(bool skip) {
    if (state.isFreelancer) return;
    state = state.copyWith(skipDocument: skip, clearError: true);
  }

  /// Validates + stashes the picked file and runs the OCR stub (Decision
  /// 6). Returns the (always empty) preview result on success, or `null`
  /// on failure (in which case [VerificationUploadState.error] carries
  /// the plain-language cause).
  Future<OcrPreviewResult?> previewPickedFile() async {
    final file = state.pickedFile;
    if (file == null) return null;

    state = state.copyWith(isBusy: true, clearError: true);
    try {
      final result = await _verificationRepository.previewDocument(
        file,
        state.documentType,
      );
      state = state.copyWith(isBusy: false);
      return result;
    } on VerificationException catch (error) {
      state = state.copyWith(isBusy: false, error: error);
      return null;
    }
  }

  /// Business-only path (AC2/Decision 3): submits directly with no
  /// document, skipping the confirm step entirely since there is nothing
  /// to confirm. Returns `true` on success.
  Future<bool> submitWithoutDocument() async {
    state = state.copyWith(isBusy: true, clearError: true);
    try {
      await _verificationRepository.submit(const SubmitVerificationRequest());
      state = state.copyWith(isBusy: false);
      return true;
    } on VerificationException catch (error) {
      state = state.copyWith(isBusy: false, error: error);
      return false;
    }
  }
}

final verificationUploadControllerProvider =
    StateNotifierProvider.autoDispose<
      VerificationUploadController,
      VerificationUploadState
    >(
      (ref) => VerificationUploadController(
        ref.watch(verificationRepositoryProvider),
        ref.watch(currentProviderTypeRepositoryProvider),
      ),
    );
