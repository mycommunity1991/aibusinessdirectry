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
}
