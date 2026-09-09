import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../auth/state/auth_session_controller.dart';
import '../../../customer/data/saved_address_repository.dart';
import '../../../customer/domain/models/address_form_mode.dart';
import '../../../customer/domain/models/saved_address_exception.dart';

/// Minimal placeholder landed on after a successful `verify-otp`.
///
/// Full Home (S-06) belongs to a future Customer Core Loop story — this
/// stub exists only so AUTH-001 has somewhere authenticated to land. Its
/// only added behavior (AUTH-003) is a bare "Log out" action — no dedicated
/// "Manage Sessions" screen is built this story (Plan Decision 11).
///
/// The app-bar person icon is a temporary entry point to Profile & Settings
/// (S-14, CUS-001) — not a bottom-nav tab, since the real 3-tab
/// Home/Activity/Profile shell needs real Home/Activity screens that don't
/// exist yet (`Plan_S03_CUS-001.md` Decision 7).
///
/// The "Find a Service" button still enforces CUS-002's address-required
/// gate (AC5, unchanged) — but as of DIR-001 (`Plan_S06_DIR-001.md`
/// Decision 6), once a saved address exists it opens the real, structured
/// Search Filters screen instead of showing a "coming soon" snackbar. The
/// full AI Conversation entry point (S-06/S-07) remains a future story;
/// this button is still not that, only a step closer to it.
class HomePlaceholderScreen extends ConsumerWidget {
  const HomePlaceholderScreen({super.key});

  Future<void> _onLogOut(WidgetRef ref, BuildContext context) async {
    final accessToken = ref.read(authSessionProvider)?.accessToken;
    await ref.read(authRepositoryProvider).logout(accessToken);
    await ref.read(authSessionControllerProvider).clear();
    if (context.mounted) {
      context.go(AppRoutes.phoneEntry);
    }
  }

  Future<void> _onFindService(WidgetRef ref, BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    try {
      final addresses = await ref.read(savedAddressRepositoryProvider).list();
      if (!context.mounted) return;
      if (addresses.isEmpty) {
        // AC5: re-prompt for an address (non-skippable this time) instead
        // of proceeding -- unchanged from CUS-002.
        await context.push<bool>(
          AppRoutes.addressForm,
          extra: (
            mode: AddressFormMode.add,
            existingAddress: null,
            subtitle: l10n.addressRequiredForSearchSubtitle,
          ),
        );
      } else {
        // DIR-001, Decision 6: the real Search Filters screen replaces the
        // prior "coming soon" snackbar now that it exists.
        context.push(AppRoutes.searchFilters);
      }
    } on SavedAddressException {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.genericErrorMessage)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: l10n.profileSettingsTooltip,
            onPressed: () => context.push(AppRoutes.profileSettings),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 64,
                color: colorScheme.primary,
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                l10n.homePlaceholderTitle,
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                l10n.homePlaceholderMessage,
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xl),
              OutlinedButton(
                onPressed: () => _onFindService(ref, context),
                child: Text(l10n.findServiceButtonLabel),
              ),
              const SizedBox(height: AppSpacing.md),
              TextButton(
                onPressed: () => _onLogOut(ref, context),
                child: Text(l10n.logOutLabel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
