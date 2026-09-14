/// Arguments passed to the Write-a-Review screen (S-10, REV-002, AC6) via
/// GoRouter's `extra`, from `ProviderProfileScreen._onContactTap` only --
/// the sole call site this screen is ever reached from (Decision 7,
/// `Plan_S09_REV-002.md`). Mirrors `ProviderProfileArgs`'s record-typedef
/// pattern.
typedef WriteReviewArgs = ({
  String contactViewId,
  String providerId,
  String providerDisplayName,
  String? providerPhotoUrl,
});
