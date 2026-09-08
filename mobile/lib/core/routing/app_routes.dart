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

  /// S-15 — List Your Business intro (PRO-001). Reached from
  /// [profileSettings]'s "List Your Business" entry point, only once
  /// `getMyProvider()` has confirmed the caller has no listing yet
  /// (Decision 9, `Plan_S04_PRO-001.md`).
  static const String providerIntro = '/provider-intro';

  /// S-16 — Choose Provider Type (PRO-001, AC3). The only screen that ever
  /// writes `provider_type` into `ProviderOnboardingController`.
  static const String chooseProviderType = '/choose-provider-type';

  /// S-17 — Provider Basic Info (PRO-001, AC4). Routes to [businessDetails]
  /// or [freelancerDetails] based on the onboarding controller's stored
  /// type.
  static const String providerBasicInfo = '/provider-basic-info';

  /// S-18a — Business Details, the Business path's final wizard step
  /// (PRO-001, AC5).
  static const String businessDetails = '/business-details';

  /// S-18b — Freelancer Details, the Freelancer path's final wizard step
  /// (PRO-001, AC6).
  static const String freelancerDetails = '/freelancer-details';

  /// S-25 — Manage My Storefront (PRO-002). Reached from
  /// [profileSettings]'s "List Your Business" entry point once
  /// `getMyProvider()` confirms the caller already has a listing (the
  /// branch that previously only showed a snackbar, PRO-001 Decision 9).
  static const String storefront = '/storefront';

  /// S-19 — Verification Upload (VER-001). Reached immediately after a
  /// successful `POST /providers/me` at the end of the onboarding wizard
  /// (replacing [homePlaceholder] as that destination, `Plan_S05_
  /// VER-001.md` item 30), or from [storefront]'s verification-status
  /// link / [verificationStatus]'s "Resubmit" action.
  static const String verificationUpload = '/verification-upload';

  /// The "OCR confirm" step (VER-001, AC4) — always reached via
  /// `push(..., extra: VerificationConfirmArgs(...))` from
  /// [verificationUpload], never a bare deep link (mirrors [otpEntry]/
  /// [addressForm]'s `extra`-required pattern).
  static const String verificationConfirm = '/verification-confirm';

  /// S-20 — Verification Status (VER-001). Reached from [storefront]'s
  /// verification status chip, and landed on after a successful
  /// submission from [verificationUpload]/[verificationConfirm].
  static const String verificationStatus = '/verification-status';
}
