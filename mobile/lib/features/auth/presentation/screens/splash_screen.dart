import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../state/auth_session_controller.dart';
import '../../state/language_controller.dart';

/// S-01 — Splash. A brand moment with no user action: checks the
/// persisted language choice and any in-memory session, then auto-routes
/// to Language Selection (S-02), Phone Entry (S-03), or the post-auth
/// placeholder.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _resolveDestination());
  }

  Future<void> _resolveDestination() async {
    Locale? locale;
    try {
      locale = await ref.read(languageControllerProvider.future);
    } catch (_) {
      // Fail safe: if the persisted language can't be read, treat it as
      // unset rather than getting stuck on the splash screen.
      locale = null;
    }
    if (!mounted) return;

    if (locale == null) {
      context.go(AppRoutes.language);
      return;
    }

    final session = ref.read(authSessionProvider);
    context.go(
      session != null ? AppRoutes.homePlaceholder : AppRoutes.phoneEntry,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: colorScheme.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.storefront_outlined,
              size: 64,
              color: colorScheme.onPrimary,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              l10n.appName,
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(color: colorScheme.onPrimary),
            ),
            const SizedBox(height: AppSpacing.xl),
            LoadingIndicator(
              label: l10n.loadingLabel,
              color: colorScheme.onPrimary,
            ),
          ],
        ),
      ),
    );
  }
}
