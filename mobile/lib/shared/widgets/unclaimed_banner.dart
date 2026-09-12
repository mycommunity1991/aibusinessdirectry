import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../l10n/generated/app_localizations.dart';

/// The locked, full-width "Unclaimed" banner (`16_UX_GUIDELINES.md` --
/// "Trust & Verification UX Patterns", CLM-001 Decision 8): solid Warning-
/// color (`AppColors.warning`, `#F59E0B`) with `AppColors.onWarning`
/// text/icon for contrast -- deliberately the *solid* warning pair, not
/// `DESIGN.md`'s softer `badge-unclaimed` component, since
/// `16_UX_GUIDELINES.md`'s own resolved pattern for this exact banner
/// explicitly specifies the full, solid Warning color. Occupies its
/// parent's full width by construction.
///
/// Extracted from `ProviderResultCard`'s own former private
/// `_UnclaimedBanner` (CON-001, Decision 9) -- `16_UX_GUIDELINES.md`'s
/// resolved pattern explicitly states this same banner applies to both the
/// provider card (S-08) and the Provider Profile screen (S-09), so this is
/// now a shared, public widget both render, byte-for-byte the same visual
/// implementation as before the extraction.
class UnclaimedBanner extends StatelessWidget {
  const UnclaimedBanner({super.key, this.onTap});

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
