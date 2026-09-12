import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../l10n/generated/app_localizations.dart';

/// `DESIGN.md`'s `badge-verified` component -- a paired checkmark icon and
/// "Verified" text label (never an icon alone, per `16_UX_GUIDELINES.md`'s
/// "pair every status badge with a text label" rule).
///
/// Shown on the Provider Profile screen (S-09, CON-001, AC5, Decision 8)
/// only when `is_claimed == true && verification_status == approved` --
/// mutually exclusive with the shared [UnclaimedBanner]
/// (`shared/widgets/unclaimed_banner.dart`): Decision 8's precedence
/// (`is_claimed` checked first) means at most one of the two ever renders
/// for a given provider, never both.
class VerifiedBadge extends StatelessWidget {
  const VerifiedBadge({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;

    return Container(
      key: const ValueKey('verified-badge'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppColors.successContainer,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.verified,
            color: AppColors.onSuccessContainer,
            size: 18,
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            l10n.verifiedBadgeLabel,
            style: textTheme.labelLarge?.copyWith(
              color: AppColors.onSuccessContainer,
            ),
          ),
        ],
      ),
    );
  }
}
