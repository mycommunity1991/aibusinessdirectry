import 'package:ai_marketplace_app/core/routing/app_router.dart';
import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Pumps the full app router (Splash/Language/Phone Entry/OTP Entry/Home
/// placeholder), starting at [initialLocation], with the given provider
/// [overrides]. Used by tests that exercise real GoRouter navigation
/// between two or more of this story's screens.
Future<void> pumpApp(
  WidgetTester tester, {
  List<Override> overrides = const [],
  String initialLocation = AppRoutes.splash,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp.router(
        theme: AppTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: buildAppRouter(initialLocation: initialLocation),
      ),
    ),
  );
}

/// Pumps a single [child] widget under a minimal GoRouter + ProviderScope
/// + localizations shell — for screens (like OTP Entry) that are normally
/// reached via `extra` data rather than a bare path, and whose
/// `context.pop()`/`context.go()` calls just need *some* router ancestor
/// to resolve against.
Future<void> pumpScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  final router = GoRouter(
    initialLocation: '/under-test',
    routes: [
      GoRoute(path: '/under-test', builder: (context, state) => child),
      GoRoute(
        path: AppRoutes.phoneEntry,
        builder: (context, state) =>
            const Scaffold(body: Text('phone-entry-stub')),
      ),
      GoRoute(
        path: AppRoutes.homePlaceholder,
        builder: (context, state) =>
            const Scaffold(body: Text('home-placeholder-stub')),
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
