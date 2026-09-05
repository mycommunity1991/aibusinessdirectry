/// Configuration for the Google/Apple native sign-in plugins (AUTH-002).
///
/// Mirrors `ApiConfig`'s `String.fromEnvironment` pattern — every value is
/// blank by default and must be supplied at build/run time via
/// `--dart-define`, since the real Google Cloud Console / Apple Developer
/// Portal credentials are external configuration not available at
/// implementation time (`Plan_S02_AUTH-002.md`, Decisions 9 & 10, "Mobile —
/// Proposed Changes → Platform configuration"). Blank values are handled
/// gracefully by `AuthRepository` (Google's `serverClientId` becomes `null`
/// and Apple's Android/web fallback is skipped), so automated tests never
/// depend on real values — only real-device sign-in does.
class OAuthConfig {
  const OAuthConfig._();

  /// Google's single, shared Web/server OAuth Client ID, used to scope the
  /// ID token's audience regardless of platform (Plan Decision 9). Set via
  /// `--dart-define=GOOGLE_OAUTH_SERVER_CLIENT_ID=...`.
  static const String googleServerClientId = String.fromEnvironment(
    'GOOGLE_OAUTH_SERVER_CLIENT_ID',
  );

  /// Apple's Services ID, required only for the Android/web fallback sign-in
  /// flow (native iOS/macOS uses the app's Bundle ID instead and needs no
  /// configuration here) (Plan Decision 10). Set via
  /// `--dart-define=APPLE_OAUTH_SERVICE_ID=...`.
  static const String appleServiceId = String.fromEnvironment(
    'APPLE_OAUTH_SERVICE_ID',
  );

  /// The redirect URI registered against [appleServiceId] for the
  /// Android/web fallback flow. Set via
  /// `--dart-define=APPLE_OAUTH_REDIRECT_URI=...`.
  static const String appleRedirectUri = String.fromEnvironment(
    'APPLE_OAUTH_REDIRECT_URI',
  );
}
