import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_confirm_args.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_confirm_screen.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Pumps a single [child] widget under a minimal GoRouter + ProviderScope
/// + localizations shell -- mirrors `features/auth/test_helpers.dart`'s
/// `pumpScreen` pattern, kept local to this feature's tests since
/// Verification's screens navigate to routes that helper doesn't stub.
/// Every route a Verification screen might navigate to (S-19/S-20) has a
/// simple stub destination here, so `context.go`/`context.push` calls
/// resolve without needing the full app router.
Future<void> pumpVerificationScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  final router = GoRouter(
    initialLocation: '/under-test',
    routes: [
      GoRoute(path: '/under-test', builder: (context, state) => child),
      GoRoute(
        path: AppRoutes.verificationUpload,
        builder: (context, state) =>
            const Scaffold(body: Text('verification-upload-stub')),
      ),
      GoRoute(
        path: AppRoutes.verificationConfirm,
        // Mirrors the real app router's own `extra`-required wiring, so
        // tests that continue from Upload into Confirm exercise the exact
        // same args-passing behavior as production.
        builder: (context, state) {
          final args = state.extra as VerificationConfirmArgs;
          return VerificationConfirmScreen(args: args);
        },
      ),
      GoRoute(
        path: AppRoutes.verificationStatus,
        builder: (context, state) =>
            const Scaffold(body: Text('verification-status-stub')),
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp.router(
        theme: AppTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router,
      ),
    ),
  );
}
