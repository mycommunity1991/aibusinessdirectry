import '../../l10n/generated/app_localizations.dart';

/// Formats a provider's rating for display -- "No reviews yet" when
/// [averageRating] is `null` (DIR-001, Decision 2; never a synthesized
/// `"0.0 (0 reviews)"`), otherwise "{rating} ({count} reviews)". Rating and
/// review count are always rendered together, never rating alone
/// (`DESIGN.md`, CON-001 AC5) -- extracted here so `ProviderResultCard`
/// (S-08) and the Provider Profile screen (S-09, CON-001) share one
/// implementation rather than each computing this string independently.
String ratingWithReviewCountLabel(
  AppLocalizations l10n, {
  required double? averageRating,
  required int reviewCount,
}) {
  if (averageRating == null) return l10n.noReviewsYetLabel;
  return l10n.ratingWithReviewCountLabel(
    averageRating.toStringAsFixed(1),
    reviewCount,
  );
}
