/// Configuration for the Google Maps SDK (CUS-002, AC3).
///
/// Mirrors `oauth_config.dart`'s `String.fromEnvironment` pattern: blank by
/// default, real value supplied at build/run time via `--dart-define`,
/// since a real Google Cloud Console project + billing account is an
/// external prerequisite not available at implementation time
/// (`Plan_S03_CUS-002.md`, "Decisions Needing Explicit User Sign-Off").
///
/// Unlike `OAuthConfig`'s values (read directly by `AuthRepository` at
/// runtime), the Google Maps API key is consumed natively — Android's
/// `AndroidManifest.xml` `com.google.android.geo.API_KEY` meta-data and
/// iOS's `AppDelegate.swift` `GMSServices.provideAPIKey(...)` call, both of
/// which currently carry placeholder/blank values (see those files' own
/// comments). [googleMapsApiKey] exists here for documentation/consistency
/// with [OAuthConfig] and so a future story wiring real native config has a
/// single, obvious place to read the key from if it ever needs to be
/// threaded through Dart (e.g. a build script) — no current call site
/// depends on it.
class MapsConfig {
  const MapsConfig._();

  /// Set via `--dart-define=GOOGLE_MAPS_API_KEY=...`.
  static const String googleMapsApiKey = String.fromEnvironment(
    'GOOGLE_MAPS_API_KEY',
  );
}
