import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider_exception.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_upload_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../shared/widgets/location_picker/fakes/fake_location_service.dart';
import 'fakes/fake_provider_repository.dart';
import 'test_helpers.dart';

Future<void> _reachBusinessDetails(
  WidgetTester tester, {
  required List<Override> overrides,
}) async {
  await pumpToProviderBasicInfo(
    tester,
    overrides: overrides,
    typeLabel: 'Business',
  );
  await fillMinimalBasicInfoAndContinue(tester);
}

void main() {
  group('BusinessDetailsScreen (S-18a, PRO-001, AC9) — step indicator', () {
    testWidgets('renders the step indicator at step 3 of 3', (tester) async {
      await _reachBusinessDetails(
        tester,
        overrides: [
          providerRepositoryProvider.overrideWithValue(
            FakeProviderRepository(),
          ),
        ],
      );

      expect(find.bySemanticsLabel('Step 3 of 3'), findsOneWidget);
    });
  });

  group(
    'BusinessDetailsScreen (S-18a, PRO-001, AC5/AC9) — required-field gating',
    () {
      testWidgets(
        'Submit stays disabled until the address line and a location are set',
        (tester) async {
          final fakeLocationService = FakeLocationService(
            reverseGeocodeResult: providerFakeLocationFix,
          );
          await _reachBusinessDetails(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
              locationServiceProvider.overrideWithValue(fakeLocationService),
            ],
          );

          var submitButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Submit'),
          );
          expect(submitButton.onPressed, isNull);

          await tester.tap(find.text('Use current location'));
          await tester.pumpAndSettle();

          submitButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Submit'),
          );
          expect(submitButton.onPressed, isNotNull);
        },
      );

      testWidgets(
        'optional operating hours, delivery radius, and trade license never '
        'block Submit',
        (tester) async {
          final fakeLocationService = FakeLocationService(
            reverseGeocodeResult: providerFakeLocationFix,
          );
          await _reachBusinessDetails(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
              locationServiceProvider.overrideWithValue(fakeLocationService),
            ],
          );

          await tester.tap(find.text('Use current location'));
          await tester.pumpAndSettle();

          // Every optional field (operating hours, delivery radius, trade
          // license) is left untouched.
          final submitButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Submit'),
          );
          expect(submitButton.onPressed, isNotNull);
        },
      );
    },
  );

  group('BusinessDetailsScreen (S-18a, PRO-001, Decision 2) — submission', () {
    testWidgets(
      'submitting calls createProvider exactly once with basic info and '
      'business details merged',
      (tester) async {
        final fakeRepository = FakeProviderRepository();
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: providerFakeLocationFix,
        );
        await _reachBusinessDetails(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();

        await tester.enterText(
          find.widgetWithText(TextField, 'Trade license number (optional)'),
          'TL-12345',
        );
        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createProviderCallCount, 1);
        final request = fakeRepository.lastCreateRequest!;
        expect(request.providerType, ProviderType.business);
        expect(request.displayName, 'Test Provider');
        expect(request.phoneCountryCode, '+971');
        expect(request.phoneNumber, '501234567');
        expect(request.categoryLabel, 'Plumbing');
        expect(request.businessDetails, isNotNull);
        expect(request.businessDetails!.addressLine, 'Al Wasl Road');
        expect(request.businessDetails!.countryCode, 'AE');
        expect(request.businessDetails!.latitude, 25.2048);
        expect(request.businessDetails!.longitude, 55.2708);
        expect(request.businessDetails!.tradeLicenseNumber, 'TL-12345');
        expect(request.freelancerDetails, isNull);

        // Wizard-ending navigation lands on Verification Upload (S-19,
        // VER-001, Plan item 30), not Home.
        expect(find.byType(VerificationUploadScreen), findsOneWidget);
      },
    );

    testWidgets(
      'a failed submission (409 already-exists) shows a plain-language '
      'error, never a raw exception, and stays on the details screen',
      (tester) async {
        final fakeRepository = FakeProviderRepository(
          createProviderError: const ProviderException(
            type: ProviderErrorType.alreadyExists,
          ),
        );
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: providerFakeLocationFix,
        );
        await _reachBusinessDetails(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
        );

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createProviderCallCount, 1);
        expect(find.byType(AppErrorMessage), findsOneWidget);
        expect(
          find.text('You already have a business listing.'),
          findsOneWidget,
        );
        expect(find.text('Business details'), findsOneWidget);
        expect(find.textContaining('ProviderException'), findsNothing);
      },
    );
  });
}
