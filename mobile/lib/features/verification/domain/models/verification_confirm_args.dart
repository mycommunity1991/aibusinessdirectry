import 'dart:io';

import 'document_type.dart';
import 'ocr_preview_result.dart';

/// `extra` payload required to reach `VerificationConfirmScreen` --
/// mirrors `OtpEntryArgs`/`AddressFormArgs`'s pattern (a screen that
/// cannot render meaningfully without its predecessor's result).
class VerificationConfirmArgs {
  const VerificationConfirmArgs({
    required this.documentType,
    required this.file,
    required this.preview,
  });

  final DocumentType documentType;

  /// The device's own picked-file reference -- the confirm screen renders
  /// its thumbnail locally from this, never from a fetched server URL
  /// (the pending-slot file is private, Decision 7).
  final File file;
  final OcrPreviewResult preview;
}
