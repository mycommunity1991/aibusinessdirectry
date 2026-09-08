import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/step_indicator.dart';
import '../../domain/models/provider_type.dart';
import '../../state/provider_onboarding_controller.dart';

/// S-16 — Choose Provider Type (PRO-001, AC3). Two selectable cards
/// (Business / Freelancer); selecting one and continuing sets
/// `ProviderOnboardingController`'s type — this is the **only** screen in
/// the feature that ever does so.
class ChooseProviderTypeScreen extends ConsumerStatefulWidget {
  const ChooseProviderTypeScreen({super.key});

  @override
  ConsumerState<ChooseProviderTypeScreen> createState() =>
      _ChooseProviderTypeScreenState();
}

class _ChooseProviderTypeScreenState
    extends ConsumerState<ChooseProviderTypeScreen> {
  ProviderType? _selected;

  void _onContinue() {
    final selected = _selected;
    if (selected == null) return;
    ref
        .read(providerOnboardingControllerProvider.notifier)
        .setProviderType(selected);
    context.push(AppRoutes.providerBasicInfo);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    // Keeps `providerOnboardingControllerProvider` (`autoDispose`) alive for
    // as long as this screen stays on the navigation stack -- it's pushed,
    // never popped, until the wizard completes, so this is what makes the
    // draft survive across every subsequent step (Decision 8,
    // `Plan_S04_PRO-001.md`). `_onContinue` only ever needs `ref.read`, but
    // this `watch` is what prevents the provider from being disposed the
    // instant that one-off read finishes.
    ref.watch(providerOnboardingControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.chooseProviderTypeTitle)),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const StepIndicator(
                currentStep: 1,
                totalSteps: providerWizardTotalSteps,
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                l10n.chooseProviderTypePrompt,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: AppSpacing.md),
              _ProviderTypeCard(
                icon: Icons.storefront_outlined,
                title: l10n.providerTypeBusinessTitle,
                subtitle: l10n.providerTypeBusinessSubtitle,
                selected: _selected == ProviderType.business,
                onTap: () => setState(() => _selected = ProviderType.business),
              ),
              const SizedBox(height: AppSpacing.md),
              _ProviderTypeCard(
                icon: Icons.person_outline,
                title: l10n.providerTypeFreelancerTitle,
                subtitle: l10n.providerTypeFreelancerSubtitle,
                selected: _selected == ProviderType.freelancer,
                onTap: () =>
                    setState(() => _selected = ProviderType.freelancer),
              ),
              const Spacer(),
              PrimaryButton(
                label: l10n.continueLabel,
                onPressed: _selected == null ? null : _onContinue,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// One selectable provider-type option — a `card-standard`-style card
/// (`docs/AI/DESIGN.md`) that highlights via the theme's primary color when
/// selected, with a trailing check icon.
class _ProviderTypeCard extends StatelessWidget {
  const _ProviderTypeCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: EdgeInsets.zero,
      color: selected
          ? colorScheme.primaryContainer
          : colorScheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.largeCard),
        side: BorderSide(
          color: selected ? colorScheme.primary : Colors.transparent,
          width: 2,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.largeCard),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              Icon(
                icon,
                size: 32,
                color: selected
                    ? colorScheme.primary
                    : colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected)
                Icon(Icons.check_circle, color: colorScheme.primary),
            ],
          ),
        ),
      ),
    );
  }
}
