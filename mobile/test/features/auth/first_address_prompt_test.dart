import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/customer/data/saved_address_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/add_first_address_screen.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/address_form_screen.dart';
import 'package:ai_marketplace_app/features/home/presentation/screens/home_placeholder_screen.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_auth_repository.dart';
import 'test_helpers.dart';
import '../customer/fakes/fake_saved_address_repository.dart';

/// CUS-002 — AC4 ("skippable, never blocks registration completion"), AC5
/// ("does not re-prompt until a search is actually attempted"), and AC9's
/// "skip-then-required-later flow", proven end-to-end through the real
/// registration → Home → "Find a Service" navigation, exactly as a customer
/// would experience it (`Plan_S03_CUS-002.md` item 28).
void main() {
  testWidgets(
    'skip at registration reaches Home with a live session and zero addresses, '
    'then "Find a Service" routes to a non-skippable re-prompt (AC4/AC5/AC9)',
    (tester) async {
      final fakeAuthRepository = FakeAuthRepository();
      final fakeSavedAddressRepository = FakeSavedAddressRepository();

      await pumpApp(
        tester,
        initialLocation: AppRoutes.phoneEntry,
        overrides: [
          authRepositoryProvider.overrideWithValue(fakeAuthRepository),
          savedAddressRepositoryProvider.overrideWithValue(
            fakeSavedAddressRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      // 1. Registration (via Google OAuth, AUTH-002) completes — session is
      // already live by the time the first-address prompt renders (AC4).
      await tester.tap(find.text('Continue with Google'));
      await tester.pumpAndSettle();

      expect(find.byType(AddFirstAddressScreen), findsOneWidget);
      expect(find.text('Add your first address'), findsOneWidget);
      expect(find.text('Skip'), findsOneWidget);

      // 2. Skip -- never calls the repository, and reaches Home directly.
      await tester.tap(find.text('Skip'));
      await tester.pumpAndSettle();

      expect(find.byType(HomePlaceholderScreen), findsOneWidget);
      expect(fakeSavedAddressRepository.createCallCount, 0);

      // 3. No re-prompt happens on its own -- only once "Find a Service"
      // (the temporary AC5 trigger stub) is tapped.
      expect(find.byType(AddressFormScreen), findsNothing);

      // 4. Tapping it, with zero saved addresses, routes to the (real,
      // non-skippable) re-prompt -- proving AC5's gate fires exactly then.
      await tester.tap(find.text('Find a Service'));
      await tester.pumpAndSettle();

      expect(fakeSavedAddressRepository.listCallCount, greaterThanOrEqualTo(1));
      expect(find.byType(AddressFormScreen), findsOneWidget);
      expect(
        find.text('Add an address to search for services near you.'),
        findsOneWidget,
      );
      // Non-skippable this time -- no Skip link on the re-prompt.
      expect(find.text('Skip'), findsNothing);
    },
  );

  testWidgets(
    '"Find a Service" with at least one saved address shows "Search coming soon" instead of re-prompting',
    (tester) async {
      final fakeAuthRepository = FakeAuthRepository();
      final fakeSavedAddressRepository = FakeSavedAddressRepository(
        initialAddresses: const [
          SavedAddress(
            id: 'address-1',
            label: 'Home',
            addressLine: 'Villa 12, Al Wasl Road',
            city: 'Dubai',
            region: 'Dubai',
            countryCode: 'AE',
            latitude: 25.2048,
            longitude: 55.2708,
            isDefault: true,
          ),
        ],
      );

      await pumpApp(
        tester,
        initialLocation: AppRoutes.phoneEntry,
        overrides: [
          authRepositoryProvider.overrideWithValue(fakeAuthRepository),
          savedAddressRepositoryProvider.overrideWithValue(
            fakeSavedAddressRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Continue with Google'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Skip'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Find a Service'));
      await tester.pumpAndSettle();

      expect(find.text('Search coming soon.'), findsOneWidget);
      expect(find.byType(AddressFormScreen), findsNothing);
    },
  );
}
