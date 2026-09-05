import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:ai_marketplace_app/features/auth/state/auth_session_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../auth/fakes/fake_auth_repository.dart';
import '../auth/test_helpers.dart';

/// AUTH-003 — the bare "Log out" action added to the existing
/// `HomePlaceholderScreen` stub (Plan Decision 11 — no new "Manage
/// Sessions" screen this story).
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'app_language_code': 'en'});
  });

  testWidgets(
    'tapping Log out revokes the session, clears local session state, and routes to Phone Entry',
    (tester) async {
      final fakeRepository = FakeAuthRepository();
      const token = AuthToken(
        accessToken: 'current-access-token',
        refreshToken: 'current-refresh-token',
        tokenType: 'bearer',
        user: AuthUser(
          id: 'user-1',
          phoneCountryCode: '+971',
          phoneNumber: '501234567',
          status: 'active',
          preferredLanguage: 'en',
          roles: ['customer'],
        ),
      );

      await pumpApp(
        tester,
        initialLocation: AppRoutes.homePlaceholder,
        overrides: [
          authRepositoryProvider.overrideWithValue(fakeRepository),
          authSessionProvider.overrideWith((ref) => token),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Log out'));
      await tester.pumpAndSettle();

      expect(fakeRepository.logoutCallCount, 1);
      expect(fakeRepository.lastLogoutAccessToken, 'current-access-token');
      expect(find.byType(PhoneEntryScreen), findsOneWidget);

      final container = ProviderScope.containerOf(
        tester.element(find.byType(PhoneEntryScreen)),
      );
      expect(container.read(authSessionProvider), isNull);
    },
  );
}
