import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/state/auth_session_controller.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/add_first_address_screen.dart';
import 'package:ai_marketplace_app/features/home/presentation/screens/home_placeholder_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes/fake_auth_repository.dart';
import 'test_helpers.dart';

/// AUTH-002 — Google/Apple sign-in on the Sign In / Sign Up screen (S-03).
///
/// Exercises [OAuthSignInController] end-to-end through the real
/// `PhoneEntryScreen`, using [FakeAuthRepository] as the hermetic boundary
/// (no real Dio/network calls, no real Google/Apple plugin calls — the
/// plugin invocation lives inside `AuthRepository`, which the fake fully
/// overrides, mirroring `Plan_S02_AUTH-002.md`'s "fakes/mocks at the
/// repository layer" test strategy).
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('PhoneEntryScreen (S-03) — Google/Apple buttons (AC1)', () {
    testWidgets('Google and Apple buttons render enabled, not "coming soon"', (
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

      expect(google.onPressed, isNotNull);
      expect(apple.onPressed, isNotNull);
      expect(find.text('Coming soon'), findsNothing);
    });
  });

  group('OAuthSignInController — successful sign-in', () {
    testWidgets(
      'a successful Google sign-in navigates to the first-address prompt (CUS-002, AC4) and populates authSessionProvider',
      (tester) async {
        final fakeRepository = FakeAuthRepository();
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Google'));
        await tester.pumpAndSettle();

        expect(fakeRepository.signInWithGoogleCallCount, 1);
        expect(find.byType(AddFirstAddressScreen), findsOneWidget);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(AddFirstAddressScreen)),
        );
        expect(container.read(authSessionProvider), isNotNull);
        expect(
          container.read(authSessionProvider)!.accessToken,
          'test-access-token',
        );
      },
    );

    testWidgets(
      'a successful Apple sign-in navigates to the first-address prompt (CUS-002, AC4) and populates authSessionProvider',
      (tester) async {
        final fakeRepository = FakeAuthRepository();
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Apple'));
        await tester.pumpAndSettle();

        expect(fakeRepository.signInWithAppleCallCount, 1);
        expect(find.byType(AddFirstAddressScreen), findsOneWidget);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(AddFirstAddressScreen)),
        );
        expect(container.read(authSessionProvider), isNotNull);
      },
    );
  });

  group('OAuthSignInController — cancellation (AC7)', () {
    testWidgets(
      'cancelling Google sign-in resets to idle with no error shown and no navigation',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          signInWithGoogleError: const OAuthCancelledException(),
        );
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Google'));
        await tester.pumpAndSettle();

        // Benign, non-error outcome (AC7): no crash, no stuck spinner, no
        // error message, and the user stays on Sign In / Sign Up.
        expect(find.byType(AppErrorMessage), findsNothing);
        expect(find.text('Continue with Google'), findsOneWidget);
        final google = tester.widget<OutlinedButton>(
          find.ancestor(
            of: find.text('Continue with Google'),
            matching: find.byType(OutlinedButton),
          ),
        );
        expect(google.onPressed, isNotNull);
        expect(find.byType(HomePlaceholderScreen), findsNothing);
      },
    );

    testWidgets(
      'cancelling Apple sign-in resets to idle with no error shown and no navigation',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          signInWithAppleError: const OAuthCancelledException(),
        );
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Apple'));
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsNothing);
        expect(find.byType(HomePlaceholderScreen), findsNothing);
      },
    );
  });

  group('OAuthSignInController — generic failure (AC6)', () {
    testWidgets(
      'a generic Google failure shows the localized identity-verification error, never a raw backend message',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          signInWithGoogleError: const AuthException(
            type: AuthErrorType.identityVerificationFailed,
          ),
        );
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Google'));
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text("We couldn't verify your sign-in. Please try again."),
          findsOneWidget,
        );
        expect(find.textContaining('401'), findsNothing);
        expect(find.textContaining('InvalidIdentityTokenError'), findsNothing);
        expect(find.textContaining('Exception'), findsNothing);
        expect(find.byType(HomePlaceholderScreen), findsNothing);
      },
    );

    testWidgets(
      'a generic Apple failure shows the localized identity-verification error, never a raw backend message',
      (tester) async {
        final fakeRepository = FakeAuthRepository(
          signInWithAppleError: const AuthException(
            type: AuthErrorType.identityVerificationFailed,
          ),
        );
        await pumpApp(
          tester,
          initialLocation: AppRoutes.phoneEntry,
          overrides: [authRepositoryProvider.overrideWithValue(fakeRepository)],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Continue with Apple'));
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text("We couldn't verify your sign-in. Please try again."),
          findsOneWidget,
        );
        expect(find.byType(HomePlaceholderScreen), findsNothing);
      },
    );
  });
}
