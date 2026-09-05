import 'package:ai_marketplace_app/core/storage/secure_token_storage.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:ai_marketplace_app/features/auth/state/auth_session_controller.dart';
import 'package:ai_marketplace_app/features/home/presentation/screens/home_placeholder_screen.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes/fake_auth_repository.dart';
import 'fakes/fake_secure_token_storage.dart';
import 'test_helpers.dart';

/// AUTH-003 — "stay signed in across app restarts". Exercises Splash's
/// (S-01) session-restore step: a persisted session is read from secure
/// storage, silently refreshed against the backend, and only then trusted
/// — never a bare "a token exists" check (Plan "Mobile — Proposed
/// Changes", `splash_screen.dart`).
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'app_language_code': 'en'});
  });

  final persistedToken = AuthToken(
    accessToken: 'stale-access-token',
    refreshToken: 'persisted-refresh-token',
    tokenType: 'bearer',
    user: const AuthUser(
      id: 'user-1',
      phoneCountryCode: '+971',
      phoneNumber: '501234567',
      status: 'active',
      preferredLanguage: 'en',
      roles: ['customer'],
    ),
  );

  group('Splash session restore', () {
    testWidgets(
      'a persisted session silently refreshes and routes to the home placeholder',
      (tester) async {
        final fakeStorage = FakeSecureTokenStorage(
          initialToken: persistedToken,
        );
        final fakeRepository = FakeAuthRepository();

        await pumpApp(
          tester,
          overrides: [
            secureTokenStorageProvider.overrideWithValue(fakeStorage),
            authRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.refreshCallCount, 1);
        expect(fakeRepository.lastRefreshToken, 'persisted-refresh-token');
        expect(find.byType(HomePlaceholderScreen), findsOneWidget);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(HomePlaceholderScreen)),
        );
        expect(container.read(authSessionProvider), isNotNull);
        // The refreshed pair replaces the stale persisted one.
        expect(fakeStorage.writeCallCount, 1);
      },
    );

    testWidgets(
      'no persisted session routes straight to Phone Entry, never calling refresh',
      (tester) async {
        final fakeStorage = FakeSecureTokenStorage();
        final fakeRepository = FakeAuthRepository();

        await pumpApp(
          tester,
          overrides: [
            secureTokenStorageProvider.overrideWithValue(fakeStorage),
            authRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.refreshCallCount, 0);
        expect(find.byType(PhoneEntryScreen), findsOneWidget);
      },
    );

    testWidgets(
      'a persisted-but-rejected session is cleared and routes to Phone Entry',
      (tester) async {
        final fakeStorage = FakeSecureTokenStorage(
          initialToken: persistedToken,
        );
        final fakeRepository = FakeAuthRepository(
          refreshError: const AuthException(
            type: AuthErrorType.identityVerificationFailed,
          ),
        );

        await pumpApp(
          tester,
          overrides: [
            secureTokenStorageProvider.overrideWithValue(fakeStorage),
            authRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.refreshCallCount, 1);
        expect(find.byType(PhoneEntryScreen), findsOneWidget);
        expect(fakeStorage.clearCallCount, 1);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(PhoneEntryScreen)),
        );
        expect(container.read(authSessionProvider), isNull);
      },
    );
  });
}
