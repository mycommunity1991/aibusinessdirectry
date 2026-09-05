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
