import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Pumps a single [child] widget under a minimal GoRouter + ProviderScope +
/// localizations shell -- mirrors `features/verification/test_helpers.dart`
/// 's `pumpVerificationScreen` pattern, kept local to this feature's tests.
/// Every route a Claim screen might navigate to (S-21/S-22, plus S-19 the
/// post-claim next step) has a simple stub destination here, so
/// `context.push`/`context.go` calls resolve without needing the full app
/// router.
Future<void> pumpClaimScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  final router = GoRouter(
    initialLocation: '/under-test',
    routes: [
      GoRoute(path: '/under-test', builder: (context, state) => child),
      GoRoute(
        path: AppRoutes.claimSearch,
        builder: (context, state) =>
            const Scaffold(body: Text('claim-search-stub')),
      ),
      GoRoute(
        path: AppRoutes.claimOtp,
        builder: (context, state) {
          final providerId = state.extra as String? ?? 'unknown-provider';
          return Scaffold(body: Text('claim-otp-stub-$providerId'));
        },
      ),
      GoRoute(
        path: AppRoutes.verificationUpload,
        builder: (context, state) =>
            const Scaffold(body: Text('verification-upload-stub')),
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
