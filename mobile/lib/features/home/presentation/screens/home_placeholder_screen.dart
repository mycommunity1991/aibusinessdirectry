import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../auth/state/auth_session_controller.dart';

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
