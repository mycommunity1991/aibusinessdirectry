import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'test_helpers.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('LanguageSelectionScreen (S-02)', () {
    testWidgets('Continue is disabled until a language is selected', (
      tester,
    ) async {
      await pumpApp(tester, initialLocation: AppRoutes.language);
      await tester.pumpAndSettle();

      final continueButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Continue'),
      );
      expect(continueButton.onPressed, isNull);
    });

    testWidgets(
      'selecting Arabic persists the choice and navigates to Phone Entry',
      (tester) async {
        await pumpApp(tester, initialLocation: AppRoutes.language);
        await tester.pumpAndSettle();

        await tester.tap(find.text('العربية'));
        await tester.pumpAndSettle();

        final continueButton = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Continue'),
        );
        expect(continueButton.onPressed, isNotNull);

        await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
        await tester.pumpAndSettle();

        expect(find.byType(PhoneEntryScreen), findsOneWidget);

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('app_language_code'), 'ar');
      },
    );

    testWidgets('selecting English persists "en"', (tester) async {
      await pumpApp(tester, initialLocation: AppRoutes.language);
      await tester.pumpAndSettle();

      await tester.tap(find.text('English'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
      await tester.pumpAndSettle();

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('app_language_code'), 'en');
    });
  });
}
