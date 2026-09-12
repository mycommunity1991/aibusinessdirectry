import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart' as url_launcher;

/// Abstracts launching an external `tel:`/`https://wa.me/...` URL behind
/// one interface, so [ContactRevealSheet] and any widget test can depend on
/// it without ever invoking the real `url_launcher` platform channel --
/// mirrors `PortfolioImagePicker`/`LocationService`'s exact pattern
/// (PRO-002/CUS-002).
abstract class ContactLauncher {
  /// Launches the device's dialer for [phoneNumber] (the provider's
  /// country code and local number, concatenated -- e.g. `"+971501234567"`,
  /// no spaces). Returns `true` if a handler accepted the URL.
  Future<bool> launchCall(String phoneNumber);

  /// Launches WhatsApp (or a browser fallback) for [whatsappNumber]
  /// (digits only, no `+`/spaces/dashes). Returns `true` if a handler
  /// accepted the URL.
  Future<bool> launchWhatsApp(String whatsappNumber);
}

/// The real, device-backed [ContactLauncher] -- wraps `url_launcher`
/// directly. Used everywhere except widget tests.
class DeviceContactLauncher implements ContactLauncher {
  const DeviceContactLauncher();

  @override
  Future<bool> launchCall(String phoneNumber) {
    return url_launcher.launchUrl(Uri(scheme: 'tel', path: phoneNumber));
  }

  @override
  Future<bool> launchWhatsApp(String whatsappNumber) {
    return url_launcher.launchUrl(
      Uri.parse('https://wa.me/$whatsappNumber'),
      mode: url_launcher.LaunchMode.externalApplication,
    );
  }
}

final contactLauncherProvider = Provider<ContactLauncher>(
  (ref) => const DeviceContactLauncher(),
);
