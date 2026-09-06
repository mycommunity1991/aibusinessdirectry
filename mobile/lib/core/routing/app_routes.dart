/// Centralized route path constants — screens must navigate via these
/// constants rather than hardcoding path strings.
class AppRoutes {
  const AppRoutes._();

  static const String splash = '/splash';
  static const String language = '/language';
  static const String phoneEntry = '/phone-entry';
  static const String otpEntry = '/otp-entry';

  /// Minimal stub landed on after a successful `verify-otp`. Full Home
  /// (S-06) is a separate future Customer Core Loop story.
  static const String homePlaceholder = '/home-placeholder';

  /// Profile & Settings (S-14, CUS-001). Reached directly from a temporary
  /// entry point on [homePlaceholder] — not a bottom-nav tab, since the
  /// full Home/Activity/Profile shell needs real Home/Activity screens
  /// that don't exist yet (`Plan_S03_CUS-001.md` Decision 7).
  static const String profileSettings = '/profile-settings';
}
