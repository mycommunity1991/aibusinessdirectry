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

  /// S-05 — the skippable first-address prompt shown right after
  /// registration (CUS-002, AC4). Replaces [homePlaceholder] as the
  /// `verify-otp`/OAuth success destination.
  static const String addFirstAddress = '/add-first-address';

  /// S-12 — Saved Addresses list (CUS-002, AC6/AC7). Reached from
  /// [profileSettings].
  static const String savedAddresses = '/saved-addresses';

  /// The shared Add/Edit Address form (CUS-002, `AddressFormScreen`),
  /// covering S-12's add/edit and the AC5 re-prompt from
  /// [homePlaceholder]'s "Find a Service" stub. Requires an
  /// `AddressFormArgs` via `extra`. [addFirstAddress] is a separate,
  /// dedicated route and never uses this one.
  static const String addressForm = '/address-form';
}
