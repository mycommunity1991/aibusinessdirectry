import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/otp_entry_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes/fake_auth_repository.dart';
import 'test_helpers.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('PhoneEntryScreen (S-03)', () {
    testWidgets('Continue is disabled while the phone number is invalid', (
      tester,
    ) async {
      await pumpApp(tester, initialLocation: AppRoutes.phoneEntry);
      await tester.pumpAndSettle();

      final continueButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Continue with Mobile Number'),
      );
      expect(continueButton.onPressed, isNull);
    });

    testWidgets(
      'shows inline validation once a short number has been entered',
      (tester) async {
        await pumpApp(tester, initialLocation: AppRoutes.phoneEntry);
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Mobile number'),
          '12',
        );
        await tester.pumpAndSettle();

        expect(find.text('Enter a valid mobile number.'), findsOneWidget);
      },
    );

    testWidgets('Google and Apple options render disabled ("coming soon")', (
      tester,
    ) async {
      await pumpApp(tester, initialLocation: AppRoutes.phoneEntry);
      await tester.pumpAndSettle();

      final google = tester.widget<OutlinedButton>(
        find.ancestor(
          of: find.text('Continue with Google'),
          matching: find.byType(OutlinedButton),
        ),
      );
      final apple = tester.widget<OutlinedButton>(
        find.ancestor(
          of: find.text('Continue with Apple'),
          matching: find.byType(OutlinedButton),
        ),
      );

      expect(google.onPressed, isNull);
      expect(apple.onPressed, isNull);
    });

    testWidgets(
      'submitting a valid number requests an OTP and navigates to OTP Entry with the entered number',
      (tester) async {
        final fakeRepository = FakeAuthRepository();
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Mobile number'),
          '501234567',
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.widgetWithText(FilledButton, 'Continue with Mobile Number'),
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.requestOtpCallCount, 1);
        expect(find.byType(OtpEntryScreen), findsOneWidget);

        final otpScreen = tester.widget<OtpEntryScreen>(
          find.byType(OtpEntryScreen),
        );
        expect(otpScreen.countryCode, '+971');
        expect(otpScreen.phoneNumber, '501234567');
      },
    );

    testWidgets(
      'a failed OTP request shows a plain-language error, never a raw status code',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          requestOtpError: const AuthException(type: AuthErrorType.unknown),
        );
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Mobile number'),
          '501234567',
        );
        await tester.pumpAndSettle();
        await tester.tap(
          find.widgetWithText(FilledButton, 'Continue with Mobile Number'),
        );
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text('Something went wrong. Please try again.'),
          findsOneWidget,
        );
        expect(find.textContaining('400'), findsNothing);
        expect(find.textContaining('429'), findsNothing);
        expect(find.textContaining('Exception'), findsNothing);
        expect(find.byType(OtpEntryScreen), findsNothing);
      },
    );
  });
}
