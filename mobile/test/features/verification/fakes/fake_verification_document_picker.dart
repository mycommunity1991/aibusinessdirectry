import 'dart:io';

import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_upload_screen.dart';

/// A hermetic test double for [VerificationDocumentPicker] -- no real
/// `image_picker`/`file_picker` platform channel is ever invoked. Mirrors
/// `fake_portfolio_image_picker.dart`'s pattern.
class FakeVerificationDocumentPicker implements VerificationDocumentPicker {
  FakeVerificationDocumentPicker({this.cameraFile, this.filesFile});

  /// The file `pickFromCamera` returns; `null` simulates cancelling.
  final File? cameraFile;

  /// The file `pickFromFiles` returns; `null` simulates cancelling.
  final File? filesFile;

  int pickFromCameraCallCount = 0;
  int pickFromFilesCallCount = 0;

  @override
  Future<File?> pickFromCamera() async {
    pickFromCameraCallCount++;
    return cameraFile;
  }

  @override
  Future<File?> pickFromFiles() async {
    pickFromFilesCallCount++;
    return filesFile;
  }
}
