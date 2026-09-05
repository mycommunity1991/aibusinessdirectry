import 'package:ai_marketplace_app/features/auth/presentation/screens/language_selection_screen.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'test_helpers.dart';

/// Session-restore behavior ("routes to the post-auth placeholder when a
/// persisted session silently refreshes" and its failure/no-session
/// counterparts) moved to `session_persistence_test.dart` (AUTH-003) — this
/// file keeps only the language-gating behavior that predates that story.
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
  });
}
