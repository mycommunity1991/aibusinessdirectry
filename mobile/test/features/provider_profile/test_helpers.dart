import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/write_review_args.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Pumps a single [child] widget under a minimal GoRouter + ProviderScope +
/// localizations shell -- mirrors `features/claim/test_helpers.dart`'s
/// `pumpClaimScreen` pattern, kept local to this feature's tests. The Claim
/// OTP screen (the Provider Profile screen's own unclaimed-banner
/// destination) and the Write-a-Review screen (REV-002, AC6) each have a
/// simple stub here so `context.push` calls resolve without needing the
/// full app router.
Future<void> pumpProviderProfileScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  final router = GoRouter(
    initialLocation: '/under-test',
    routes: [
      GoRoute(path: '/under-test', builder: (context, state) => child),
      GoRoute(
        path: AppRoutes.claimOtp,
        builder: (context, state) {
          final providerId = state.extra as String? ?? 'unknown-provider';
          return Scaffold(body: Text('claim-otp-stub-$providerId'));
        },
      ),
      GoRoute(
        path: AppRoutes.writeReview,
        builder: (context, state) {
          final args = state.extra as WriteReviewArgs?;
          return Scaffold(
            body: Text(
              args == null
                  ? 'write-review-stub-no-args'
                  : 'write-review-stub-${args.contactViewId}-'
                        '${args.providerId}-${args.providerDisplayName}',
            ),
          );
        },
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
