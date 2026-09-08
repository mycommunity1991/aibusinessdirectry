import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http_parser/http_parser.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/document_type.dart';
import '../domain/models/ocr_preview_result.dart';
import '../domain/models/submit_verification_request.dart';
import '../domain/models/verification_exception.dart';
import '../domain/models/verification_record.dart';

/// Wraps `/providers/me/verification` and its sub-resources
/// (`backend/app/modules/verification/api.py`, VER-001).
///
/// Every failure is mapped to a plain-language [VerificationException] --
/// callers (`VerificationUploadController`/`VerificationStatusController`/
/// the screens) never see a [DioException], an HTTP status code, or a
/// backend error identifier, following the same convention as
/// `provider_repository.dart`.
class VerificationRepository {
  VerificationRepository(this._dio);

  final Dio _dio;

  static const _basePath = '/providers/me/verification';

  // The backend's `VerificationDocumentTooLargeError`/
  // `VerificationDocumentInvalidTypeError` (`backend/app/core/exceptions/
  // exceptions.py`) are two genuinely distinct 422s (Decision 8,
  // `Plan_S05_VER-001.md`) but `ErrorResponse` carries no separate
  // machine-readable error code -- only `message`. Both exceptions are
  // always raised with their fixed default message (never overridden
  // anywhere in `document_validation.py`), so matching that exact text is
  // the only way to tell them apart today. Flagged for a future backend
  // improvement (an explicit error code field) rather than guessed at.
  static const _tooLargeMessage =
      'This file is too large. The maximum size is 10 MB.';
  static const _invalidTypeMessage =
      'Unsupported file type. Please upload a JPG, PNG, WEBP, or PDF file.';

  /// Validates and stashes [file] at the caller's private, deterministic
  /// pending slot, and runs the (stubbed, Decision 6) OCR pass -- writes
  /// **no** database row. The returned fields are always empty today;
  /// present them as editable, provisional data, never as fact (AC4).
  Future<OcrPreviewResult> previewDocument(
    File file,
    DocumentType documentType,
  ) async {
    try {
      final fileName = file.uri.pathSegments.isNotEmpty
          ? file.uri.pathSegments.last
          : 'document';
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          file.path,
          filename: fileName,
          contentType: _contentTypeFor(fileName),
        ),
        'document_type': documentType.wireValue,
      });
      final response = await _dio.post<Map<String, dynamic>>(
        '$_basePath/documents/preview',
        data: formData,
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const VerificationException(type: VerificationErrorType.unknown);
      }
      return OcrPreviewResult.fromJson(data);
    } on DioException catch (error) {
      throw _mapPreviewError(error);
    }
  }

  /// Submits a new verification cycle (AC5) -- always **creates** a new
  /// `verification_records` row, never updates an existing one, so
  /// resubmission after a rejection preserves history by construction
  /// (AC7). `request`'s fields are exactly what the user confirmed/edited
  /// on the confirm screen, never the OCR stub's raw preview output (AC8).
  Future<VerificationRecord> submit(SubmitVerificationRequest request) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        _basePath,
        data: request.toJson(),
      );
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const VerificationException(type: VerificationErrorType.unknown);
      }
      return VerificationRecord.fromJson(data);
    } on DioException catch (error) {
      throw _mapSubmitError(error);
    }
  }

  /// Returns the caller's own latest verification cycle, or `null` if
  /// they've never submitted (backend 404) -- mirrors
  /// `ProviderRepository.getMyProvider()`'s null-on-404 convention:
  /// "not yet submitted" is a normal state here, not a failure.
  Future<VerificationRecord?> getMyCurrentStatus() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(_basePath);
      final data = response.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const VerificationException(type: VerificationErrorType.unknown);
      }
      return VerificationRecord.fromJson(data);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      throw _mapNetworkOnlyError(error);
    }
  }

  /// Streams one of the caller's own verification document's raw bytes,
  /// for an in-app "view what I submitted" preview on the status screen.
  /// **Never** construct a raw `Image.network`/direct-URL call against a
  /// verification document -- the document is private and only servable
  /// through this authenticated endpoint (Decision 7); render the
  /// returned bytes with `Image.memory`.
  Future<List<int>> getDocumentBytes(String documentId) async {
    try {
      final response = await _dio.get<List<int>>(
        '$_basePath/documents/$documentId/file',
        options: Options(responseType: ResponseType.bytes),
      );
      final data = response.data;
      if (data == null) {
        throw const VerificationException(type: VerificationErrorType.unknown);
      }
      return data;
    } on DioException catch (error) {
      throw _mapNetworkOnlyError(error);
    }
  }

  VerificationException _mapPreviewError(DioException error) {
    if (error.response == null) {
      return const VerificationException(type: VerificationErrorType.network);
    }
    final statusCode = error.response!.statusCode;
    if (statusCode == 404) {
      return const VerificationException(
        type: VerificationErrorType.providerNotFound,
      );
    }
    if (statusCode == 422) {
      final message = _messageOf(error);
      if (message == _tooLargeMessage) {
        return const VerificationException(
          type: VerificationErrorType.documentTooLarge,
        );
      }
      if (message == _invalidTypeMessage) {
        return const VerificationException(
          type: VerificationErrorType.documentInvalidType,
        );
      }
    }
    return const VerificationException(type: VerificationErrorType.unknown);
  }

  VerificationException _mapSubmitError(DioException error) {
    if (error.response == null) {
      return const VerificationException(type: VerificationErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const VerificationException(
        type: VerificationErrorType.providerNotFound,
      ),
      409 => const VerificationException(
        type: VerificationErrorType.submissionNotAllowed,
      ),
      // `submit`'s service layer only ever raises one 422
      // (`VerificationDocumentRequiredError`) -- unlike preview's two, no
      // message-matching is needed here.
      422 => const VerificationException(
        type: VerificationErrorType.documentRequired,
      ),
      _ => const VerificationException(type: VerificationErrorType.unknown),
    };
  }

  VerificationException _mapNetworkOnlyError(DioException error) {
    if (error.response == null) {
      return const VerificationException(type: VerificationErrorType.network);
    }
    return const VerificationException(type: VerificationErrorType.unknown);
  }

  String? _messageOf(DioException error) {
    final data = error.response?.data;
    return data is Map<String, dynamic> ? data['message'] as String? : null;
  }

  MediaType? _contentTypeFor(String fileName) {
    final lower = fileName.toLowerCase();
    if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
      return MediaType('image', 'jpeg');
    }
    if (lower.endsWith('.png')) return MediaType('image', 'png');
    if (lower.endsWith('.webp')) return MediaType('image', 'webp');
    if (lower.endsWith('.pdf')) return MediaType('application', 'pdf');
    return null;
  }
}

final verificationRepositoryProvider = Provider<VerificationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VerificationRepository(apiClient.dio);
});
