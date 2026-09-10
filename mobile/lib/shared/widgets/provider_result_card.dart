import 'package:flutter/material.dart';

import '../../core/network/api_config.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../l10n/generated/app_localizations.dart';
import '../models/ranked_provider_result.dart';

/// The reusable, single result-card widget for any ranked-provider list
/// (`shared/widgets/ranked_provider_results_list.dart`, `Plan_S07_AI-002.md`
/// Mobile item 25) -- photo, name, category labels, rating+count, and
/// distance. Originally `features/search`'s `ProviderSearchCard` (DIR-001);
/// moved here so both `features/search` (S-08) and `features/conversation`
/// (S-07's ranked-results state, AI-002) render provider results through the
/// same widget, rather than one feature importing the other's widget file
/// directly (`13_OPEN_DECISIONS.md` item 12).
///
/// Deliberately generic over how the underlying list was ordered/produced:
/// it renders exactly [RankedProviderResult]'s fields and nothing else --
/// no ranking-specific UI (e.g. a "match score") exists here, since no
/// merit-ranking algorithm exists yet (DIR-001 AC5, AI-002 Decision 5).
///
/// CLM-001, Decision 8: when [RankedProviderResult.isClaimed] is `false`,
/// renders a full-width Warning-color banner above the card's normal
/// content (the exact locked copy/color from `16_UX_GUIDELINES.md`'s
/// "Trust & Verification UX Patterns") -- server-driven off that one
/// boolean, never inferred client-side. Tapping the banner calls
/// [onClaimTap]; tapping anywhere else on the card still calls [onTap]
/// unchanged.
class ProviderResultCard extends StatelessWidget {
  const ProviderResultCard({
    super.key,
    required this.provider,
    this.onTap,
    this.onClaimTap,
  });

  final RankedProviderResult provider;
  final VoidCallback? onTap;

  /// Called when the unclaimed banner's inline CTA is tapped. Only ever
  /// rendered/reachable when `provider.isClaimed == false`.
  final VoidCallback? onClaimTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!provider.isClaimed) _UnclaimedBanner(onTap: onClaimTap),
          InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _CardPhoto(photoUrl: provider.primaryPhotoUrl),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          provider.displayName,
                          style: textTheme.titleMedium,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (provider.categoryLabels.isNotEmpty) ...[
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            provider.categoryLabels.join(' • '),
                            style: textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          _ratingLabel(l10n, provider),
                          style: textTheme.bodySmall,
                        ),
                        // AI-002, Decision 2c: `distanceMeters` is `null`
                        // only when no origin/provider location could be
                        // resolved -- the row is simply omitted rather than
                        // rendering a guessed or zeroed distance.
                        if (provider.distanceMeters != null) ...[
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            _distanceLabel(l10n, provider.distanceMeters!),
                            style: textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// `averageRating == null` always renders "No reviews yet" -- never a
  /// synthesized `"0.0 (0 reviews)"`.
  static String _ratingLabel(
    AppLocalizations l10n,
    RankedProviderResult provider,
  ) {
    final rating = provider.averageRating;
    if (rating == null) return l10n.noReviewsYetLabel;
    return l10n.ratingWithReviewCountLabel(
      rating.toStringAsFixed(1),
      provider.reviewCount,
    );
  }

  static String _distanceLabel(AppLocalizations l10n, double meters) {
    if (meters < 1000) {
      return l10n.distanceInMetersLabel(meters.round());
    }
    return l10n.distanceInKmLabel((meters / 1000).toStringAsFixed(1));
  }
}

class _CardPhoto extends StatelessWidget {
  const _CardPhoto({required this.photoUrl});

  final String? photoUrl;

  static const double _size = 72;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final photoUrl = this.photoUrl;

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.standard),
      child: photoUrl == null
          ? _Placeholder(colorScheme: colorScheme)
          : Image.network(
              '${ApiConfig.mediaOrigin}$photoUrl',
              width: _size,
              height: _size,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) =>
                  _Placeholder(colorScheme: colorScheme),
            ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.colorScheme});

  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: _CardPhoto._size,
      height: _CardPhoto._size,
      color: colorScheme.surfaceContainerHighest,
      child: Icon(
        Icons.storefront_outlined,
        color: colorScheme.onSurfaceVariant,
      ),
    );
  }
}

/// The locked, full-width "Unclaimed" banner (`16_UX_GUIDELINES.md` --
/// "Trust & Verification UX Patterns", Decision 8): solid Warning-color
/// (`AppColors.warning`, `#F59E0B`) with `AppColors.onWarning` text/icon for
/// contrast -- deliberately the *solid* warning pair, not `DESIGN.md`'s
/// softer `badge-unclaimed` component, since `16_UX_GUIDELINES.md`'s own
/// resolved pattern for this exact banner explicitly specifies the full,
/// solid Warning color. Occupies the card's full width by construction.
class _UnclaimedBanner extends StatelessWidget {
  const _UnclaimedBanner({required this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;

    return Material(
      color: AppColors.warning,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          child: Row(
            children: [
              const Icon(
                Icons.info_outline,
                color: AppColors.onWarning,
                size: 18,
              ),
              const SizedBox(width: AppSpacing.xs),
              Expanded(
                child: Text(
                  l10n.unclaimedBannerLabel,
                  style: textTheme.labelLarge?.copyWith(
                    color: AppColors.onWarning,
                  ),
                ),
              ),
              const Icon(
                Icons.chevron_right,
                color: AppColors.onWarning,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
