import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:ai_marketplace_app/features/auth/presentation/screens/phone_entry_screen.dart';
import 'package:ai_marketplace_app/features/auth/state/auth_session_controller.dart';
import 'package:ai_marketplace_app/features/customer/data/customer_repository.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/profile_settings_screen.dart';
import 'package:ai_marketplace_app/features/notifications/data/notification_repository.dart';
import 'package:ai_marketplace_app/features/notifications/presentation/screens/notifications_inbox_screen.dart';
import 'package:ai_marketplace_app/shared/data/unread_notification_count_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../shared/fakes/fake_unread_notification_count_repository.dart';
import '../auth/fakes/fake_auth_repository.dart';
import '../auth/test_helpers.dart';
import '../customer/fakes/fake_customer_repository.dart';
import '../notifications/fakes/fake_notification_repository.dart';

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

  testWidgets(
    'tapping the profile icon opens Profile & Settings (S-14, CUS-001, '
    'Plan Decision 7 — a temporary entry point, not a bottom-nav tab)',
    (tester) async {
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
          authSessionProvider.overrideWith((ref) => token),
          customerRepositoryProvider.overrideWithValue(
            FakeCustomerRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.person_outline));
      await tester.pumpAndSettle();

      expect(find.byType(ProfileSettingsScreen), findsOneWidget);
    },
  );

  group('HomePlaceholderScreen -- "Notifications" entry point '
      '(ENG-001, Plan Frontend item 2)', () {
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

    testWidgets('renders the "Notifications" entry point tile with a live '
        'unread-count badge from a fixture', (tester) async {
      await pumpApp(
        tester,
        initialLocation: AppRoutes.homePlaceholder,
        overrides: [
          authSessionProvider.overrideWith((ref) => token),
          customerRepositoryProvider.overrideWithValue(
            FakeCustomerRepository(),
          ),
          unreadNotificationCountRepositoryProvider.overrideWithValue(
            FakeUnreadNotificationCountRepository(count: 4),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('home-notifications-entry-point')),
        findsOneWidget,
      );
      expect(find.text('Notifications'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('home-notifications-unread-badge')),
        findsOneWidget,
      );
      expect(find.text('4'), findsOneWidget);
    });

    testWidgets('renders no badge at all when the unread count is zero', (
      tester,
    ) async {
      await pumpApp(
        tester,
        initialLocation: AppRoutes.homePlaceholder,
        overrides: [
          authSessionProvider.overrideWith((ref) => token),
          customerRepositoryProvider.overrideWithValue(
            FakeCustomerRepository(),
          ),
          unreadNotificationCountRepositoryProvider.overrideWithValue(
            FakeUnreadNotificationCountRepository(count: 0),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('home-notifications-unread-badge')),
        findsNothing,
      );
    });

    testWidgets('tapping the "Notifications" tile navigates to '
        'AppRoutes.notificationsInbox', (tester) async {
      await pumpApp(
        tester,
        initialLocation: AppRoutes.homePlaceholder,
        overrides: [
          authSessionProvider.overrideWith((ref) => token),
          customerRepositoryProvider.overrideWithValue(
            FakeCustomerRepository(),
          ),
          unreadNotificationCountRepositoryProvider.overrideWithValue(
            FakeUnreadNotificationCountRepository(count: 1),
          ),
          // Keeps the destination screen's own first load hermetic --
          // this test only asserts navigation occurred, not the
          // Inbox's own load behavior (covered by
          // `notifications_inbox_screen_test.dart`).
          notificationRepositoryProvider.overrideWithValue(
            FakeNotificationRepository(pages: const [[]]),
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey('home-notifications-entry-point')),
      );
      await tester.pumpAndSettle();

      expect(find.byType(NotificationsInboxScreen), findsOneWidget);
    });
  });
}
