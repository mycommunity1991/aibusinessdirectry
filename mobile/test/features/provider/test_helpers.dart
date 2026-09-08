import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_pick_result.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';

/// A representative reverse-geocoded fix, reused by every provider-wizard
/// test that needs to simulate "Use current location" via
/// `FakeLocationService` (mirrors `address_form_screen_test.dart`'s
/// `_fakeFix`).
const providerFakeLocationFix = LocationPickResult(
  latitude: 25.2048,
  longitude: 55.2708,
  addressLine: 'Al Wasl Road',
  city: 'Dubai',
  region: 'Dubai',
  countryCode: 'AE',
);

/// Pumps the real app router starting at Choose Provider Type (S-16),
/// selects [type] ("Business" or "Freelancer"), and taps Continue —
/// landing on Provider Basic Info (S-17) with the wizard's type already
/// set, exactly as it's reached in the real app.
Future<void> pumpToProviderBasicInfo(
  WidgetTester tester, {
  required List<Override> overrides,
  required String typeLabel,
}) async {
  await pumpApp(
    tester,
    overrides: overrides,
    initialLocation: AppRoutes.chooseProviderType,
  );
  await tester.pumpAndSettle();

  await tester.tap(find.text(typeLabel));
  await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
  await tester.pumpAndSettle();
}

/// Continues from Provider Basic Info (S-17, assumed already on-screen)
/// having filled in the minimal required fields, landing on S-18a/S-18b.
Future<void> fillMinimalBasicInfoAndContinue(WidgetTester tester) async {
  await tester.enterText(
    find.widgetWithText(TextField, 'Display name'),
    'Test Provider',
  );
  await tester.enterText(
    find.widgetWithText(TextField, 'Mobile number'),
    '501234567',
  );
  await tester.enterText(
    find.widgetWithText(TextField, 'Category'),
    'Plumbing',
  );
  await tester.pump();

  await tester.ensureVisible(find.widgetWithText(FilledButton, 'Continue'));
  await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
  await tester.pumpAndSettle();
}
