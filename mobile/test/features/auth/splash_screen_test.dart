import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/language_selection_screen.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:ai_marketplace_app/features/auth/state/auth_session_controller.dart';
import 'package:ai_marketplace_app/features/home/presentation/screens/home_placeholder_screen.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'test_helpers.dart';

void main() {
  group('SplashScreen auto-routing (S-01)', () {
    testWidgets('routes to Language Selection when no language is persisted', (
      tester,
    ) async {
      SharedPreferences.setMockInitialValues({});

      await pumpApp(tester);
      await tester.pumpAndSettle();

      expect(find.byType(LanguageSelectionScreen), findsOneWidget);
    });

    testWidgets(
      'routes to Phone Entry when a language is persisted and no session exists',
      (tester) async {
        SharedPreferences.setMockInitialValues({'app_language_code': 'en'});

        await pumpApp(tester);
        await tester.pumpAndSettle();

        expect(find.byType(PhoneEntryScreen), findsOneWidget);
      },
    );

    testWidgets(
      'routes to the post-auth placeholder when a language is persisted and a session exists',
      (tester) async {
        SharedPreferences.setMockInitialValues({'app_language_code': 'en'});
        final token = AuthToken(
          accessToken: 'test-token',
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

        await pumpApp(
          tester,
          overrides: [authSessionProvider.overrideWith((ref) => token)],
        );
        await tester.pumpAndSettle();

        expect(find.byType(HomePlaceholderScreen), findsOneWidget);
      },
    );
  });
}
