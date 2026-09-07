import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_pick_result.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_picker_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import 'fakes/fake_location_service.dart';

/// Stands in for the real `GoogleMap` — never a real platform view in
/// tests (`Plan_S03_CUS-002.md`: "no real GoogleMap ... platform channel
/// calls in tests").
Widget _fakeMapViewBuilder(
  BuildContext context, {
  required LatLng center,
  required ValueChanged<LatLng> onCenterChanged,
  required ValueChanged<GoogleMapController> onMapCreated,
}) {
  return const ColoredBox(key: Key('fake-map'), color: Colors.transparent);
}

/// Pushes [LocationPickerScreen] from a plain button and renders whatever
/// it pops with as text, so tests can assert on the returned
/// [LocationPickResult] without any GoRouter dependency (this widget never
/// uses GoRouter — plain `Navigator.pop`).
class _Harness extends StatefulWidget {
  const _Harness();

  @override
  State<_Harness> createState() => _HarnessState();
}

class _HarnessState extends State<_Harness> {
  LocationPickResult? _result;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: _result == null
            ? ElevatedButton(
                onPressed: () async {
                  final result = await Navigator.of(context)
                      .push<LocationPickResult>(
                        MaterialPageRoute(
                          builder: (_) => const LocationPickerScreen(
                            mapViewBuilder: _fakeMapViewBuilder,
                          ),
                        ),
                      );
                  setState(() => _result = result);
                },
                child: const Text('open'),
              )
            : Text(
                'lat:${_result!.latitude},lng:${_result!.longitude},'
                'addr:${_result!.addressLine}',
              ),
      ),
    );
  }
}

Future<void> _pump(
  WidgetTester tester, {
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const _Harness(),
      ),
    ),
  );
}

void main() {
  group('LocationPickerScreen (CUS-002, AC3)', () {
    testWidgets(
      'renders the map, "Use current location", and "Confirm this location"',
      (tester) async {
        await _pump(
          tester,
          overrides: [
            locationServiceProvider.overrideWithValue(FakeLocationService()),
          ],
        );
        await tester.tap(find.text('open'));
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('fake-map')), findsOneWidget);
        expect(find.text('Use current location'), findsOneWidget);
        expect(find.text('Confirm this location'), findsOneWidget);
      },
    );

    testWidgets(
      'confirming pops with the reverse-geocoded result for the current center',
      (tester) async {
        final fakeService = FakeLocationService(
          reverseGeocodeResult: const LocationPickResult(
            latitude: 25.2048,
            longitude: 55.2708,
            addressLine: 'Al Wasl Road',
            city: 'Dubai',
            region: 'Dubai',
            countryCode: 'AE',
          ),
        );
        await _pump(
          tester,
          overrides: [locationServiceProvider.overrideWithValue(fakeService)],
        );
        await tester.tap(find.text('open'));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Confirm this location'));
        await tester.pumpAndSettle();

        expect(fakeService.reverseGeocodeCallCount, 1);
        expect(
          find.text('lat:25.2048,lng:55.2708,addr:Al Wasl Road'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      '"Use current location" recenters on the device fix before confirming',
      (tester) async {
        final fakeService = FakeLocationService(
          currentLocation: const LocationFix(
            latitude: 24.4539,
            longitude: 54.3773,
          ),
          reverseGeocodeResult: const LocationPickResult(
            latitude: 24.4539,
            longitude: 54.3773,
            addressLine: 'Corniche Road',
          ),
        );
        await _pump(
          tester,
          overrides: [locationServiceProvider.overrideWithValue(fakeService)],
        );
        await tester.tap(find.text('open'));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();
        expect(fakeService.getCurrentLocationCallCount, 1);

        await tester.tap(find.text('Confirm this location'));
        await tester.pumpAndSettle();

        expect(
          find.text('lat:24.4539,lng:54.3773,addr:Corniche Road'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'a permission-denied failure shows a localized message, never a raw exception',
      (tester) async {
        final fakeService = FakeLocationService(
          getCurrentLocationError: const LocationServiceException(
            type: LocationServiceErrorType.permissionDenied,
          ),
        );
        await _pump(
          tester,
          overrides: [locationServiceProvider.overrideWithValue(fakeService)],
        );
        await tester.tap(find.text('open'));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        expect(
          find.text(
            'Location permission is needed to use your current location.',
          ),
          findsOneWidget,
        );
        expect(find.textContaining('LocationServiceException'), findsNothing);
      },
    );
  });
}
