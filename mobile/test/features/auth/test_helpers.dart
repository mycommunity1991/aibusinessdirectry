import 'package:ai_marketplace_app/core/routing/app_router.dart';
import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/core/storage/secure_token_storage.dart';
import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_args.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'fakes/fake_secure_token_storage.dart';

/// A hermetic, empty [FakeSecureTokenStorage] default — every widget test
/// gets an in-memory session-storage double unless it supplies its own
/// `secureTokenStorageProvider` override (which, placed after this one in
/// [Override] list order, wins). Without this, any screen that persists a
/// session (AUTH-003) would hit the real `flutter_secure_storage` platform
/// channel in tests and throw a `MissingPluginException`.
List<Override> _withDefaultStorage(List<Override> overrides) {
  return [
    secureTokenStorageProvider.overrideWithValue(FakeSecureTokenStorage()),
    ...overrides,
  ];
}

/// Pumps the full app router (Splash/Language/Phone Entry/OTP Entry/Home
/// placeholder/Profile & Settings), starting at [initialLocation], with the
/// given provider [overrides]. Used by tests that exercise real GoRouter
/// navigation between two or more of this story's screens.
///
/// [locale] is optional and defaults to `null` (device-locale resolution,
/// matching every pre-CUS-001 call site unchanged) — pass
/// `const Locale('ar')` to pump a screen under test in Arabic/RTL (AC9,
/// `Plan_S03_CUS-001.md` Decision 8), the first RTL-specific automated
/// check in this codebase.
Future<void> pumpApp(
  WidgetTester tester, {
  List<Override> overrides = const [],
  String initialLocation = AppRoutes.splash,
  Locale? locale,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: _withDefaultStorage(overrides),
      child: MaterialApp.router(
        theme: AppTheme.light(),
        locale: locale,
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
///
/// [locale] is optional and defaults to `null` — see [pumpApp]'s doc for
/// the AC9/RTL use case this exists for.
Future<void> pumpScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
  Locale? locale,
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
      GoRoute(
        path: AppRoutes.addFirstAddress,
        builder: (context, state) =>
            const Scaffold(body: Text('add-first-address-stub')),
      ),
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
      overrides: _withDefaultStorage(overrides),
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
