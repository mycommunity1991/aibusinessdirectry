import 'package:ai_marketplace_app/features/customer/data/saved_address_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/saved_addresses_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_saved_address_repository.dart';

const _home = SavedAddress(
  id: 'address-1',
  label: 'Home',
  addressLine: 'Villa 12, Al Wasl Road',
  city: 'Dubai',
  region: 'Dubai',
  countryCode: 'AE',
  latitude: 25.2048,
  longitude: 55.2708,
  isDefault: true,
);

const _work = SavedAddress(
  id: 'address-2',
  label: 'Work',
  addressLine: 'Office Tower, Sheikh Zayed Road',
  city: 'Dubai',
  region: 'Dubai',
  countryCode: 'AE',
  latitude: 25.1,
  longitude: 55.2,
  isDefault: false,
);

void main() {
  group('SavedAddressesScreen (S-12, AC6) — rendering', () {
    testWidgets('lists every address and badges the default', (tester) async {
      final fakeRepository = FakeSavedAddressRepository(
        initialAddresses: [_home, _work],
      );
      await pumpScreen(
        tester,
        child: const SavedAddressesScreen(),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Work'), findsOneWidget);
      expect(find.text('Default'), findsOneWidget);
      expect(find.text('No default address set'), findsNothing);
    });

    testWidgets('shows the empty state when there are no addresses', (
      tester,
    ) async {
      final fakeRepository = FakeSavedAddressRepository();
      await pumpScreen(
        tester,
        child: const SavedAddressesScreen(),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.text('No saved addresses yet. Add one to get started.'),
        findsOneWidget,
      );
    });

    testWidgets(
      'shows a "no default" indicator when addresses exist but none is default',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          initialAddresses: [_work],
        );
        await pumpScreen(
          tester,
          child: const SavedAddressesScreen(),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(find.text('No default address set'), findsOneWidget);
      },
    );
  });

  group('SavedAddressesScreen (S-12, AC7) — delete with Undo', () {
    testWidgets(
      'deleting shows an Undo snackbar and does not call the repository until it expires',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          initialAddresses: [_home, _work],
        );
        await pumpScreen(
          tester,
          child: const SavedAddressesScreen(),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.widgetWithIcon(IconButton, Icons.delete_outline).last,
        );
        await tester.pump();

        expect(find.text('Address deleted'), findsOneWidget);
        expect(find.text('Work'), findsNothing);
        expect(fakeRepository.deleteCallCount, 0);

        await tester.pump(const Duration(seconds: 5));
        await tester.pumpAndSettle();

        expect(fakeRepository.deleteCallCount, 1);
        expect(fakeRepository.lastDeletedId, 'address-2');
      },
    );

    testWidgets('tapping Undo restores the address and never calls delete', (
      tester,
    ) async {
      final fakeRepository = FakeSavedAddressRepository(
        initialAddresses: [_home, _work],
      );
      await pumpScreen(
        tester,
        child: const SavedAddressesScreen(),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.widgetWithIcon(IconButton, Icons.delete_outline).last,
      );
      await tester.pump();
      expect(find.text('Work'), findsNothing);

      // Invoked directly (rather than a simulated tap) since the snackbar's
      // on-screen position relative to the default test viewport is an
      // unrelated geometry detail, not what this test is verifying.
      tester
          .widget<SnackBarAction>(find.widgetWithText(SnackBarAction, 'Undo'))
          .onPressed();
      await tester.pump();

      expect(find.text('Work'), findsOneWidget);

      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();

      expect(fakeRepository.deleteCallCount, 0);
    });

    testWidgets('tapping Undo right at the old (pre-fix) finalize delay still '
        'restores the address instead of silently no-oping (regression for '
        'the Undo/finalize timing race `tester` found)', (tester) async {
      final fakeRepository = FakeSavedAddressRepository(
        initialAddresses: [_home, _work],
      );
      await pumpScreen(
        tester,
        child: const SavedAddressesScreen(),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.widgetWithIcon(IconButton, Icons.delete_outline).last,
      );
      await tester.pump();

      // Advance to exactly the *old*, pre-fix finalize delay (the
      // snackbar's own `duration`, with no safety margin beyond it).
      // Before the fix, the real delete would already have been
      // finalized by this instant, even though the real on-screen
      // snackbar's Undo action can remain visibly tappable for a
      // further ~250-500ms while it animates out.
      await tester.pump(const Duration(seconds: 4));

      expect(
        fakeRepository.deleteCallCount,
        0,
        reason:
            'the safety margin must keep the real delete from '
            'finalizing until after the snackbar has actually gone away',
      );

      tester
          .widget<SnackBarAction>(find.widgetWithText(SnackBarAction, 'Undo'))
          .onPressed();
      await tester.pump();

      expect(find.text('Work'), findsOneWidget);

      // Let the (now-cancelled) finalize's scheduled time pass entirely.
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(fakeRepository.deleteCallCount, 0);
    });

    testWidgets(
      'deleting the default with others remaining offers a "choose a new default" bottom sheet',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          initialAddresses: [_home, _work],
        );
        await pumpScreen(
          tester,
          child: const SavedAddressesScreen(),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.widgetWithIcon(IconButton, Icons.delete_outline).first,
        );
        await tester.pump(const Duration(seconds: 5));
        await tester.pumpAndSettle();

        expect(fakeRepository.deleteCallCount, 1);
        expect(fakeRepository.lastDeletedId, 'address-1');
        expect(find.text('Choose a new default address'), findsOneWidget);
        expect(find.text('Not now'), findsOneWidget);

        await tester.tap(find.text('Work').last);
        await tester.pumpAndSettle();

        expect(fakeRepository.updateCallCount, 1);
        expect(find.text('Default'), findsOneWidget);
      },
    );

    testWidgets(
      'deleting the only (default) address shows no bottom sheet, just the empty state',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          initialAddresses: [_home],
        );
        await pumpScreen(
          tester,
          child: const SavedAddressesScreen(),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.widgetWithIcon(IconButton, Icons.delete_outline));
        await tester.pump(const Duration(seconds: 5));
        await tester.pumpAndSettle();

        expect(fakeRepository.deleteCallCount, 1);
        expect(find.text('Choose a new default address'), findsNothing);
        expect(
          find.text('No saved addresses yet. Add one to get started.'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      '"Not now" leaves no default address set, with addresses still shown',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          initialAddresses: [_home, _work],
        );
        await pumpScreen(
          tester,
          child: const SavedAddressesScreen(),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.widgetWithIcon(IconButton, Icons.delete_outline).first,
        );
        await tester.pump(const Duration(seconds: 5));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Not now'));
        await tester.pumpAndSettle();

        expect(fakeRepository.updateCallCount, 0);
        expect(find.text('No default address set'), findsOneWidget);
        expect(find.text('Default'), findsNothing);
      },
    );
  });
}
