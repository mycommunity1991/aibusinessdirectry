import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_args.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Pumps a single [child] widget under a minimal GoRouter + ProviderScope +
/// localizations shell -- mirrors `features/claim/test_helpers.dart`'s
/// `pumpClaimScreen` pattern, kept local to this feature's tests. A
/// `GoRouter` (rather than a bare `MaterialApp`) is needed since CON-001
/// wired a real `context.push` to the Provider Profile screen from a
/// matched-result card tap -- a stub destination for it is registered here
/// so that navigation resolves without needing the full app router.
Future<void> pumpConversationScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
  Locale locale = const Locale('en'),
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
        path: AppRoutes.providerProfile,
        builder: (context, state) {
          final args = state.extra as ProviderProfileArgs?;
          return Scaffold(
            body: Text(
              'provider-profile-stub-${args?.providerId ?? 'unknown'}-'
              '${args?.searchRequestId ?? 'no-search-request'}',
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
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router,
      ),
    ),
  );
}

/// Fails if any [Text] widget currently in the tree contains something
/// that looks like a raw confidence/score value (e.g. `0.75`) -- AC6's
/// "never shows a raw confidence score to the user," asserted at the
/// widget-tree level, not just by this screen's models having no such
/// field to render in the first place.
void expectNoConfidenceValueRendered(WidgetTester tester) {
  final texts = tester.widgetList<Text>(find.byType(Text));
  final pattern = RegExp(r'\b[01]\.\d{1,3}\b');
  for (final text in texts) {
    final data = text.data ?? '';
    expect(
      pattern.hasMatch(data),
      isFalse,
      reason: 'Found what looks like a raw confidence value in "$data"',
    );
  }
}

/// Fails if any [Text] widget currently in the tree contains "manual",
/// "fallback", or "admin" (case-insensitive) -- AI-002 AC3/AC7's forbidden-
/// word discipline, asserted at the widget-tree level for a live
/// `pending_manual_match`/`routed_to_admin` render, mirrored from the
/// backend's own `test_no_forbidden_customer_copy.py`.
void expectNoForbiddenWordsRendered(WidgetTester tester) {
  final texts = tester.widgetList<Text>(find.byType(Text));
  final forbidden = RegExp(r'manual|fallback|admin', caseSensitive: false);
  for (final text in texts) {
    final data = text.data ?? '';
    expect(
      forbidden.hasMatch(data),
      isFalse,
      reason: 'Found a forbidden internal-routing term in "$data"',
    );
  }
}
