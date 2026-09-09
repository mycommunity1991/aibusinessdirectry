import 'package:ai_marketplace_app/features/claim/data/claim_repository.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_exception.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_review_reason.dart';
import 'package:ai_marketplace_app/features/claim/presentation/screens/claim_otp_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_claim_repository.dart';
import 'test_helpers.dart';

/// S-22 -- Claim OTP Verification (CLM-001, AC4/AC5/AC6).
void main() {
  const providerId = 'provider-1';
  const otpScreen = ClaimOtpScreen(providerId: providerId);

  Future<void> enterCode(WidgetTester tester, String code) async {
    await tester.enterText(
      find.widgetWithText(TextField, 'Verification code'),
      code,
    );
    await tester.pump();
  }

  testWidgets(
    'requests an OTP against the target listing on open, and shows no '
    'phone number anywhere on the screen (AC4)',
    (tester) async {
      final fakeRepository = FakeClaimRepository();

      await pumpClaimScreen(
        tester,
        child: otpScreen,
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(fakeRepository.requestOtpCallCount, 1);
      expect(fakeRepository.lastRequestOtpProviderId, providerId);
      expect(find.byType(TextField), findsOneWidget);
      // AC4's spirit -- never displays the actual phone number.
      expect(find.textContaining('+971'), findsNothing);
    },
  );

  testWidgets(
    '"This isn\'t working" is always visible on the code-entry screen, '
    'not gated behind any failed attempt (AC6)',
    (tester) async {
      final fakeRepository = FakeClaimRepository();

      await pumpClaimScreen(
        tester,
        child: otpScreen,
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('claim-otp-not-working-link')),
        findsOneWidget,
      );
    },
  );

  testWidgets('tapping "This isn\'t working" and choosing a reason calls '
      'requestAdminReview and shows the manual-review confirmation state '
      '(AC6)', (tester) async {
    final fakeRepository = FakeClaimRepository();

    await pumpClaimScreen(
      tester,
      child: otpScreen,
      overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text("This isn't working"));
    await tester.pumpAndSettle();

    expect(find.text("I didn't receive a code"), findsOneWidget);
    expect(find.text("This isn't my business's number"), findsOneWidget);

    await tester.tap(find.text("I didn't receive a code"));
    await tester.pumpAndSettle();

    expect(fakeRepository.requestAdminReviewCallCount, 1);
    expect(fakeRepository.lastAdminReviewArgs?.providerId, providerId);
    expect(
      fakeRepository.lastAdminReviewArgs?.reason,
      ClaimReviewReason.otpFailed,
    );
    expect(
      find.byKey(const ValueKey('claim-review-confirmed-title')),
      findsOneWidget,
    );
    expect(find.text("We've flagged this for manual review"), findsOneWidget);
  });

  testWidgets(
    'a successful verify-otp navigates to the claim-success state, with a '
    'CTA into Verification Upload (AC5)',
    (tester) async {
      final fakeRepository = FakeClaimRepository();

      await pumpClaimScreen(
        tester,
        child: otpScreen,
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      await enterCode(tester, '123456');
      await tester.tap(find.widgetWithText(FilledButton, 'Verify'));
      await tester.pumpAndSettle();

      expect(fakeRepository.verifyOtpCallCount, 1);
      expect(fakeRepository.lastVerifyOtpArgs?.providerId, providerId);
      expect(fakeRepository.lastVerifyOtpArgs?.code, '123456');
      expect(find.byKey(const ValueKey('claim-success-title')), findsOneWidget);

      await tester.tap(
        find.widgetWithText(FilledButton, 'Continue to Verification'),
      );
      await tester.pumpAndSettle();

      expect(find.text('verification-upload-stub'), findsOneWidget);
    },
  );

  testWidgets(
    'a wrong/expired code shows a plain-language error and stays on the '
    'code-entry screen, with "This isn\'t working" still visible',
    (tester) async {
      final fakeRepository = FakeClaimRepository(
        verifyOtpError: const ClaimException(type: ClaimErrorType.invalidCode),
      );

      await pumpClaimScreen(
        tester,
        child: otpScreen,
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      await enterCode(tester, '123456');
      await tester.tap(find.widgetWithText(FilledButton, 'Verify'));
      await tester.pumpAndSettle();

      expect(
        find.text("That code didn't work. Double-check it and try again."),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('claim-otp-not-working-link')),
        findsOneWidget,
      );
    },
  );

  testWidgets('a listing with no public phone number skips the code-entry UI '
      'entirely and auto-submits the admin-review fallback with '
      'reason=no_public_number (AC6, the no-public-number edge case)', (
    tester,
  ) async {
    final fakeRepository = FakeClaimRepository(
      requestOtpError: const ClaimException(
        type: ClaimErrorType.publicNumberUnavailable,
      ),
    );

    await pumpClaimScreen(
      tester,
      child: otpScreen,
      overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    // No OTP entry UI was ever shown for this listing.
    expect(find.byType(TextField), findsNothing);
    expect(find.text('Verify'), findsNothing);
    expect(
      find.byKey(const ValueKey('claim-otp-not-working-link')),
      findsNothing,
    );

    expect(fakeRepository.requestOtpCallCount, 1);
    expect(fakeRepository.requestAdminReviewCallCount, 1);
    expect(fakeRepository.lastAdminReviewArgs?.providerId, providerId);
    expect(
      fakeRepository.lastAdminReviewArgs?.reason,
      ClaimReviewReason.noPublicNumber,
    );
    expect(
      find.byKey(const ValueKey('claim-review-confirmed-title')),
      findsOneWidget,
    );
  });
}
