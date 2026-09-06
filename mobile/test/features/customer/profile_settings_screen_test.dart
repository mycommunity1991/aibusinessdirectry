import 'package:ai_marketplace_app/features/auth/state/language_controller.dart';
import 'package:ai_marketplace_app/features/customer/data/customer_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/customer_profile.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/customer_profile_exception.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/profile_settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_customer_repository.dart';

const _profileScreen = ProfileSettingsScreen();

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ProfileSettingsScreen (S-14) — rendering (AC5)', () {
    testWidgets('renders the caller\'s current display name, avatar, '
        'language, and notification channel', (tester) async {
      final fakeRepository = FakeCustomerRepository(
        profile: const CustomerProfile(
          id: 'profile-1',
          displayName: 'Fatima Al Mansoori',
          avatarUrl: 'https://example.com/avatar.png',
          language: 'en',
          notificationChannel: NotificationChannel.sms,
        ),
      );
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(fakeRepository.getMyProfileCallCount, 1);

      final displayNameField = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Display name'),
      );
      expect(displayNameField.controller!.text, 'Fatima Al Mansoori');

      final avatarField = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Avatar URL'),
      );
      expect(avatarField.controller!.text, 'https://example.com/avatar.png');

      final englishSegment = tester.widget<SegmentedButton<String>>(
        find.byType(SegmentedButton<String>),
      );
      expect(englishSegment.selected, {'en'});

      final radioGroup = tester.widget<RadioGroup<NotificationChannel>>(
        find.byType(RadioGroup<NotificationChannel>),
      );
      expect(radioGroup.groupValue, NotificationChannel.sms);
    });

    testWidgets('shows a retry-able error, never a raw status code, when '
        'the initial load fails', (tester) async {
      final fakeRepository = FakeCustomerRepository(
        getMyProfileError: const CustomerProfileException(
          type: CustomerProfileErrorType.network,
        ),
      );
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.text(
          "We couldn't connect. Check your internet connection and try again.",
        ),
        findsOneWidget,
      );
      expect(find.text('Try again'), findsOneWidget);
      expect(find.textContaining('Exception'), findsNothing);
    });
  });

  group('ProfileSettingsScreen (S-14) — editing display name/avatar', () {
    testWidgets('the display-name save action stays disabled until the '
        'field actually differs from the server value', (tester) async {
      final fakeRepository = FakeCustomerRepository();
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      final saveButtons = tester
          .widgetList<IconButton>(find.widgetWithIcon(IconButton, Icons.check))
          .toList();
      expect(saveButtons.first.onPressed, isNull);
    });

    testWidgets(
      'the display-name save action stays disabled while the field is blank',
      (tester) async {
        final fakeRepository = FakeCustomerRepository();
        await pumpScreen(
          tester,
          child: _profileScreen,
          overrides: [
            customerRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Display name'),
          '   ',
        );
        await tester.pump();

        final saveButtons = tester
            .widgetList<IconButton>(
              find.widgetWithIcon(IconButton, Icons.check),
            )
            .toList();
        expect(saveButtons.first.onPressed, isNull);
      },
    );

    testWidgets('saving a new display name calls the repository', (
      tester,
    ) async {
      final fakeRepository = FakeCustomerRepository();
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextField, 'Display name'),
        'Ahmed',
      );
      await tester.pump();

      final saveButtons = tester
          .widgetList<IconButton>(find.widgetWithIcon(IconButton, Icons.check))
          .toList();
      expect(saveButtons.first.onPressed, isNotNull);

      await tester.tap(find.widgetWithIcon(IconButton, Icons.check).first);
      await tester.pumpAndSettle();

      expect(fakeRepository.updateMyProfileCallCount, 1);
      expect(fakeRepository.lastUpdateArgs?['displayName'], 'Ahmed');

      final displayNameField = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Display name'),
      );
      expect(displayNameField.controller!.text, 'Ahmed');
    });

    testWidgets('clearing the avatar field and saving clears the stored avatar '
        '(Decision 6 — a plain URL field, not an upload picker)', (
      tester,
    ) async {
      final fakeRepository = FakeCustomerRepository(
        profile: const CustomerProfile(
          id: 'profile-1',
          displayName: 'New Customer',
          avatarUrl: 'https://example.com/avatar.png',
          language: 'en',
          notificationChannel: NotificationChannel.whatsapp,
        ),
      );
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.widgetWithText(TextField, 'Avatar URL'), '');
      await tester.pump();

      await tester.tap(find.widgetWithIcon(IconButton, Icons.check).last);
      await tester.pumpAndSettle();

      expect(fakeRepository.updateMyProfileCallCount, 1);
      expect(fakeRepository.lastUpdateArgs?['clearAvatarUrl'], isTrue);
      expect(fakeRepository.lastUpdateArgs?['avatarUrl'], isNull);
    });
  });

  group('ProfileSettingsScreen (S-14) — language toggle (AC6)', () {
    testWidgets('selecting Arabic updates the preference server-side and takes '
        'effect immediately in the running app, with no restart', (
      tester,
    ) async {
      final fakeRepository = FakeCustomerRepository();
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      final container = ProviderScope.containerOf(
        tester.element(find.byType(ProfileSettingsScreen)),
      );
      expect(container.read(languageControllerProvider).valueOrNull, isNull);

      await tester.tap(find.text('العربية'));
      await tester.pumpAndSettle();

      expect(fakeRepository.updateMyProfileCallCount, 1);
      expect(fakeRepository.lastUpdateArgs?['language'], 'ar');
      expect(
        container.read(languageControllerProvider).valueOrNull,
        const Locale('ar'),
      );
    });
  });

  group('ProfileSettingsScreen (S-14) — notification channel', () {
    testWidgets('selecting SMS calls the repository with the new channel', (
      tester,
    ) async {
      final fakeRepository = FakeCustomerRepository();
      await pumpScreen(
        tester,
        child: _profileScreen,
        overrides: [
          customerRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('SMS'));
      await tester.pumpAndSettle();

      expect(fakeRepository.updateMyProfileCallCount, 1);
      expect(
        fakeRepository.lastUpdateArgs?['notificationChannel'],
        NotificationChannel.sms,
      );
    });
  });

  group('ProfileSettingsScreen (S-14) — RTL (AC9)', () {
    testWidgets(
      'renders correctly in Arabic/RTL with no layout-overflow exception',
      (tester) async {
        final fakeRepository = FakeCustomerRepository();
        await pumpScreen(
          tester,
          child: _profileScreen,
          overrides: [
            customerRepositoryProvider.overrideWithValue(fakeRepository),
          ],
          locale: const Locale('ar'),
        );
        await tester.pumpAndSettle();

        final context = tester.element(find.byType(ProfileSettingsScreen));
        expect(Directionality.of(context), TextDirection.rtl);
        expect(tester.takeException(), isNull);
      },
    );
  });
}
