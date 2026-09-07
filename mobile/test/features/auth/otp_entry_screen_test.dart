import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/otp_entry_screen.dart';
import 'package:ai_marketplace_app/features/auth/state/otp_entry_controller.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_auth_repository.dart';
import 'test_helpers.dart';

const _otpScreen = OtpEntryScreen(
  countryCode: '+971',
  phoneNumber: '501234567',
);

Future<void> _enterCode(WidgetTester tester, String code) async {
  await tester.enterText(
    find.widgetWithText(TextField, 'Verification code'),
    code,
  );
  await tester.pump();
}

void main() {
  group('OtpEntryScreen (S-04) — countdown (AC9)', () {
    testWidgets('shows a visible countdown matching the configured expiry', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        child: _otpScreen,
        overrides: [
          otpCountdownDurationProvider.overrideWithValue(
            const Duration(seconds: 5),
          ),
        ],
      );
      await tester.pump();

      expect(find.text('Resend code in 0:05'), findsOneWidget);
      expect(find.text('Resend code'), findsNothing);
    });

    testWidgets('resend becomes enabled once the countdown reaches zero', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        child: _otpScreen,
        overrides: [
          otpCountdownDurationProvider.overrideWithValue(
            const Duration(seconds: 2),
          ),
        ],
      );
      await tester.pump();
      expect(find.text('Resend code'), findsNothing);

      await tester.pump(const Duration(seconds: 2));

      expect(find.text('Resend code'), findsOneWidget);
      expect(find.textContaining('Resend code in'), findsNothing);
    });

    testWidgets(
      'resending restarts the countdown, resized from the fresh response',
      (tester) async {
        // Sized from the fresh resend's own `expires_in_seconds` (FU-2) —
        // not the same value the initial 2-second countdown started from.
        final fakeRepository = FakeAuthRepository(
          requestOtpExpiresInSeconds: 3,
        );
        await pumpScreen(
          tester,
          child: _otpScreen,
          overrides: [
            otpCountdownDurationProvider.overrideWithValue(
              const Duration(seconds: 2),
            ),
            authRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(seconds: 2));

        await tester.tap(find.widgetWithText(TextButton, 'Resend code'));
        await tester.pumpAndSettle();

        expect(fakeRepository.requestOtpCallCount, 1);
        expect(find.text('Resend code in 0:03'), findsOneWidget);
      },
    );

    testWidgets(
      'the initial countdown is sized from OtpEntryArgs.expiresInSeconds, not the fallback default',
      (tester) async {
        await pumpScreen(
          tester,
          child: const OtpEntryScreen(
            countryCode: '+971',
            phoneNumber: '501234567',
            expiresInSeconds: 7,
          ),
          overrides: [
            // The fallback default is deliberately different from 7, so
            // this only passes if the countdown is sized from the args
            // value, not the fallback provider.
            otpCountdownDurationProvider.overrideWithValue(
              const Duration(minutes: 5),
            ),
          ],
        );
        await tester.pump();

        expect(find.text('Resend code in 0:07'), findsOneWidget);
      },
    );
  });

  group('OtpEntryScreen (S-04) — 6-digit live validation', () {
    testWidgets('Verify is disabled until 6 digits are entered', (
      tester,
    ) async {
      await pumpScreen(tester, child: _otpScreen);
      await tester.pump();

      await _enterCode(tester, '123');

      final verifyButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Verify'),
      );
      expect(verifyButton.onPressed, isNull);
      expect(find.text('Enter all 6 digits.'), findsOneWidget);

      await _enterCode(tester, '123456');

      final verifyButtonComplete = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Verify'),
      );
      expect(verifyButtonComplete.onPressed, isNotNull);
      expect(find.text('Enter all 6 digits.'), findsNothing);
    });

    testWidgets('non-digit characters are rejected by the input formatter', (
      tester,
    ) async {
      await pumpScreen(tester, child: _otpScreen);
      await tester.pump();

      await _enterCode(tester, 'ab12cd');

      final field = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Verification code'),
      );
      expect(field.controller!.text, '12');
    });
  });

  group('OtpEntryScreen (S-04) — verification outcomes', () {
    testWidgets(
      'a failed verification shows a localized plain-language message, never a raw code or the backend string',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          verifyOtpError: const AuthException(type: AuthErrorType.invalidCode),
        );
        await pumpScreen(
          tester,
          child: _otpScreen,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pump();

        await _enterCode(tester, '123456');
        await tester.tap(find.widgetWithText(FilledButton, 'Verify'));
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text("That code didn't work. Check the digits and try again."),
          findsOneWidget,
        );
        expect(find.textContaining('400'), findsNothing);
        expect(find.textContaining('429'), findsNothing);
        expect(find.textContaining('AuthException'), findsNothing);
      },
    );

    testWidgets(
      'a locked-out attempt shows a localized lockout message, never a raw code or the backend string',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          verifyOtpError: const AuthException(
            type: AuthErrorType.tooManyAttempts,
          ),
        );
        await pumpScreen(
          tester,
          child: _otpScreen,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pump();

        await _enterCode(tester, '123456');
        await tester.tap(find.widgetWithText(FilledButton, 'Verify'));
        await tester.pumpAndSettle();

        expect(
          find.text(
            'Too many attempts. Please wait a moment before trying again.',
          ),
          findsOneWidget,
        );
        expect(find.textContaining('429'), findsNothing);
      },
    );

    testWidgets(
      'a successful verification navigates to the first-address prompt (CUS-002, AC4), not straight to Home',
      (tester) async {
        final fakeRepository = FakeAuthRepository();
        await pumpScreen(
          tester,
          child: _otpScreen,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pump();

        await _enterCode(tester, '123456');
        await tester.tap(find.widgetWithText(FilledButton, 'Verify'));
        await tester.pumpAndSettle();

        expect(fakeRepository.verifyOtpCallCount, 1);
        expect(find.text('add-first-address-stub'), findsOneWidget);
      },
    );
  });
}
