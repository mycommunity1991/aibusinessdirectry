import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/customer/data/saved_address_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address_exception.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/address_form_screen.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_pick_result.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../shared/widgets/location_picker/fakes/fake_location_service.dart';
import '../auth/test_helpers.dart';
import 'fakes/fake_saved_address_repository.dart';

/// Pumps [child] (an [AddressFormScreen] in non-skippable mode) pushed on
/// top of a stub "list" screen — so a successful save's `context.pop(true)`
/// has somewhere real to pop back to, mirroring how it's actually reached
/// from `SavedAddressesScreen`/the Home "Find a Service" stub.
Future<void> _pumpPushed(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  final router = GoRouter(
    initialLocation: '/list',
    routes: [
      GoRoute(
        path: '/list',
        builder: (context, state) => Scaffold(
          body: Builder(
            builder: (innerContext) => ElevatedButton(
              onPressed: () => innerContext.push('/form'),
              child: const Text('open-form'),
            ),
          ),
        ),
      ),
      GoRoute(path: '/form', builder: (context, state) => child),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp.router(
        theme: AppTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        routerConfig: router,
      ),
    ),
  );
  await tester.tap(find.text('open-form'));
  await tester.pumpAndSettle();
}

const _fakeFix = LocationPickResult(
  latitude: 25.2048,
  longitude: 55.2708,
  addressLine: 'Al Wasl Road',
  city: 'Dubai',
  region: 'Dubai',
  countryCode: 'AE',
);

void main() {
  group('AddressFormScreen (CUS-002, AC3) — manual entry', () {
    testWidgets('renders every manual-entry field', (tester) async {
      await pumpScreen(
        tester,
        child: const AddressFormScreen(mode: AddressFormMode.add),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.widgetWithText(TextField, 'Label (optional)'),
        findsOneWidget,
      );
      expect(find.widgetWithText(TextField, 'Address'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'City'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'State / Region'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'Country code'), findsOneWidget);
      expect(find.text('Pick on map'), findsOneWidget);
      expect(find.text('Use current location'), findsOneWidget);
    });

    testWidgets('the country code field is uppercased as the user types', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        child: const AddressFormScreen(mode: AddressFormMode.add),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextField, 'Country code'),
        'ae',
      );
      await tester.pump();

      final field = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Country code'),
      );
      expect(field.controller!.text, 'AE');
    });
  });

  group('AddressFormScreen (CUS-002, AC3) — Save gated on a picked location', () {
    testWidgets(
      'Save stays disabled until a location has been set via "Use current location"',
      (tester) async {
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: _fakeFix,
        );
        await pumpScreen(
          tester,
          child: const AddressFormScreen(mode: AddressFormMode.add),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(
              FakeSavedAddressRepository(),
            ),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );
        await tester.pumpAndSettle();

        // Even with the address/country fields filled in, Save must stay
        // disabled until a location has actually been picked (AC3).
        await tester.enterText(
          find.widgetWithText(TextField, 'Address'),
          'Villa 12, Al Wasl Road',
        );
        await tester.enterText(
          find.widgetWithText(TextField, 'Country code'),
          'AE',
        );
        await tester.pump();

        var saveButton = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Save'),
        );
        expect(saveButton.onPressed, isNull);
        expect(find.text('No location set yet'), findsOneWidget);

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        expect(fakeLocationService.getCurrentLocationCallCount, 1);
        saveButton = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Save'),
        );
        expect(saveButton.onPressed, isNotNull);
        expect(find.textContaining('Location set:'), findsOneWidget);
      },
    );
  });

  group('AddressFormScreen (CUS-002, AC4) — skippable mode', () {
    testWidgets('the Skip link is shown only when skippable is true', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        child: const AddressFormScreen(mode: AddressFormMode.add),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();
      expect(find.text('Skip'), findsNothing);

      await pumpScreen(
        tester,
        child: const AddressFormScreen(
          mode: AddressFormMode.add,
          skippable: true,
        ),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();
      expect(find.text('Skip'), findsOneWidget);
    });

    testWidgets(
      'tapping Skip navigates to Home and never calls the repository (AC4)',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository();
        await pumpScreen(
          tester,
          child: const AddressFormScreen(
            mode: AddressFormMode.add,
            skippable: true,
          ),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Skip'));
        await tester.pumpAndSettle();

        expect(find.text('home-placeholder-stub'), findsOneWidget);
        expect(fakeRepository.createCallCount, 0);
      },
    );

    testWidgets(
      'a successful save in skippable mode creates the address and navigates to Home',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository();
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: _fakeFix,
        );
        await pumpScreen(
          tester,
          child: const AddressFormScreen(
            mode: AddressFormMode.add,
            skippable: true,
          ),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Address'),
          'Villa 12, Al Wasl Road',
        );
        await tester.enterText(
          find.widgetWithText(TextField, 'Country code'),
          'AE',
        );
        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Save'));
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createCallCount, 1);
        expect(find.text('home-placeholder-stub'), findsOneWidget);
      },
    );
  });

  group('AddressFormScreen (CUS-002, AC6) — non-skippable add/edit', () {
    testWidgets(
      'a successful save in non-skippable mode pops back to the caller',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository();
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: _fakeFix,
        );
        await _pumpPushed(
          tester,
          child: const AddressFormScreen(mode: AddressFormMode.add),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );

        await tester.enterText(
          find.widgetWithText(TextField, 'Address'),
          'Villa 12, Al Wasl Road',
        );
        await tester.enterText(
          find.widgetWithText(TextField, 'Country code'),
          'AE',
        );
        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Save'));
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createCallCount, 1);
        // Popped back to the stub "list" screen underneath.
        expect(find.text('open-form'), findsOneWidget);
        expect(find.byType(AddressFormScreen), findsNothing);
      },
    );

    testWidgets('edit mode prefills every field and Save starts enabled', (
      tester,
    ) async {
      const existing = SavedAddress(
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
      await pumpScreen(
        tester,
        child: const AddressFormScreen(
          mode: AddressFormMode.edit,
          existingAddress: existing,
        ),
        overrides: [
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        tester
            .widget<TextField>(
              find.widgetWithText(TextField, 'Label (optional)'),
            )
            .controller!
            .text,
        'Home',
      );
      expect(
        tester
            .widget<TextField>(find.widgetWithText(TextField, 'Address'))
            .controller!
            .text,
        'Villa 12, Al Wasl Road',
      );

      final saveButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Save'),
      );
      expect(saveButton.onPressed, isNotNull);
    });

    testWidgets(
      'a failed save shows a plain-language error, never a raw exception',
      (tester) async {
        final fakeRepository = FakeSavedAddressRepository(
          createError: const SavedAddressException(
            type: SavedAddressErrorType.unknown,
          ),
        );
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: _fakeFix,
        );
        await pumpScreen(
          tester,
          child: const AddressFormScreen(mode: AddressFormMode.add),
          overrides: [
            savedAddressRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Address'),
          'Villa 12, Al Wasl Road',
        );
        await tester.enterText(
          find.widgetWithText(TextField, 'Country code'),
          'AE',
        );
        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Save'));
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text('Something went wrong. Please try again.'),
          findsOneWidget,
        );
        expect(find.textContaining('SavedAddressException'), findsNothing);
      },
    );
  });
}
