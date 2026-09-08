import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/primary_button.dart';

/// S-15 — List Your Business intro (PRO-001). Pure value-prop copy plus a
/// single "Get Started" CTA into S-16 (Choose Provider Type) — no
/// repository calls, no wizard-state writes. Reached only from
/// `ProfileSettingsScreen`'s "List Your Business" tile, after confirming
/// via `getMyProvider()` that the caller has no listing yet (Decision 9,
/// `Plan_S04_PRO-001.md`).
class ProviderIntroScreen extends StatelessWidget {
  const ProviderIntroScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.providerIntroTitle)),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Icon(
                      Icons.storefront_outlined,
                      size: 64,
                      color: colorScheme.primary,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      l10n.providerIntroHeadline,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      l10n.providerIntroBody,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              PrimaryButton(
                label: l10n.getStartedLabel,
                onPressed: () => context.push(AppRoutes.chooseProviderType),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
