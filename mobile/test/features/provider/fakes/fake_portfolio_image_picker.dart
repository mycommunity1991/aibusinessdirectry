import 'dart:io';

import 'package:ai_marketplace_app/features/provider/presentation/widgets/portfolio_manager.dart';

/// A hermetic test double for [PortfolioImagePicker] — no real
/// `image_picker` platform channel is ever invoked. Mirrors
/// `fake_location_service.dart`'s pattern for faking a plugin-backed
/// dependency at its own abstraction boundary.
class FakePortfolioImagePicker implements PortfolioImagePicker {
  FakePortfolioImagePicker({this.fileToReturn});

  /// The file `pickImage` returns; `null` simulates the user cancelling
  /// the picker.
  final File? fileToReturn;

  int pickImageCallCount = 0;

  @override
  Future<File?> pickImage() async {
    pickImageCallCount++;
    return fileToReturn;
  }
}
