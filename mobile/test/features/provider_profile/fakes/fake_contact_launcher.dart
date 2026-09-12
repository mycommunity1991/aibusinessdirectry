import 'package:ai_marketplace_app/features/provider_profile/presentation/utils/contact_launcher.dart';

/// A hermetic test double for [ContactLauncher] -- never invokes the real
/// `url_launcher` platform channel. Mirrors `FakePortfolioImagePicker`/
/// `FakeLocationService`'s pattern.
class FakeContactLauncher implements ContactLauncher {
  String? lastCallPhoneNumber;
  String? lastWhatsAppNumber;

  @override
  Future<bool> launchCall(String phoneNumber) async {
    lastCallPhoneNumber = phoneNumber;
    return true;
  }

  @override
  Future<bool> launchWhatsApp(String whatsappNumber) async {
    lastWhatsAppNumber = whatsappNumber;
    return true;
  }
}
