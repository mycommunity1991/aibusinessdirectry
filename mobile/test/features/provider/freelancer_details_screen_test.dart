import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_upload_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../shared/widgets/location_picker/fakes/fake_location_service.dart';
import 'fakes/fake_provider_repository.dart';
import 'test_helpers.dart';

Future<void> _reachFreelancerDetails(
  WidgetTester tester, {
  required List<Override> overrides,
}) async {
  await pumpToProviderBasicInfo(
    tester,
    overrides: overrides,
    typeLabel: 'Freelancer',
  );
  await fillMinimalBasicInfoAndContinue(tester);
}

void main() {
  group('FreelancerDetailsScreen (S-18b, PRO-001, AC9) — step indicator', () {
    testWidgets('renders the step indicator at step 3 of 3', (tester) async {
      await _reachFreelancerDetails(
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

  group('FreelancerDetailsScreen (S-18b, PRO-001, AC6/AC9) — required-field '
      'gating', () {
    testWidgets('Submit stays disabled until a base location is set', (
      tester,
    ) async {
      final fakeLocationService = FakeLocationService(
        reverseGeocodeResult: providerFakeLocationFix,
      );
      await _reachFreelancerDetails(
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
    });

    testWidgets('the service-radius default, and optional skills/years-of-'
        'experience, never block Submit', (tester) async {
      final fakeLocationService = FakeLocationService(
        reverseGeocodeResult: providerFakeLocationFix,
      );
      await _reachFreelancerDetails(
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

      // No skill added, no years of experience entered, radius left at
      // its default -- Submit must still be enabled once location is
      // set.
      final submitButton = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Submit'),
      );
      expect(submitButton.onPressed, isNotNull);
    });
  });

  group('FreelancerDetailsScreen (S-18b, PRO-001) — skill tags', () {
    testWidgets('adding a skill shows it as a removable chip', (tester) async {
      await _reachFreelancerDetails(
        tester,
        overrides: [
          providerRepositoryProvider.overrideWithValue(
            FakeProviderRepository(),
          ),
        ],
      );

      await tester.enterText(
        find.widgetWithText(TextField, 'Add a skill'),
        'Electrical wiring',
      );
      await tester.pump();
      await tester.tap(find.byIcon(Icons.add_circle_outline));
      await tester.pump();

      expect(find.widgetWithText(Chip, 'Electrical wiring'), findsOneWidget);
      // The input clears after adding.
      final skillField = tester.widget<TextField>(
        find.widgetWithText(TextField, 'Add a skill'),
      );
      expect(skillField.controller!.text, isEmpty);
    });
  });

  group(
    'FreelancerDetailsScreen (S-18b, PRO-001, Decision 2) — submission',
    () {
      testWidgets(
        'submitting calls createProvider exactly once with basic info and '
        'freelancer details merged',
        (tester) async {
          final fakeRepository = FakeProviderRepository();
          final fakeLocationService = FakeLocationService(
            reverseGeocodeResult: providerFakeLocationFix,
          );
          await _reachFreelancerDetails(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(fakeRepository),
              locationServiceProvider.overrideWithValue(fakeLocationService),
            ],
          );

          await tester.tap(find.text('Use current location'));
          await tester.pumpAndSettle();

          await tester.enterText(
            find.widgetWithText(TextField, 'Add a skill'),
            'Electrical wiring',
          );
          await tester.pump();
          await tester.tap(find.byIcon(Icons.add_circle_outline));
          await tester.pump();

          await tester.enterText(
            find.widgetWithText(TextField, 'Years of experience (optional)'),
            '5',
          );
          await tester.pump();

          await tester.ensureVisible(
            find.widgetWithText(FilledButton, 'Submit'),
          );
          await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
          await tester.pumpAndSettle();

          expect(fakeRepository.createProviderCallCount, 1);
          final request = fakeRepository.lastCreateRequest!;
          expect(request.providerType, ProviderType.freelancer);
          expect(request.displayName, 'Test Provider');
          expect(request.categoryLabel, 'Plumbing');
          expect(request.freelancerDetails, isNotNull);
          expect(request.freelancerDetails!.baseLatitude, 25.2048);
          expect(request.freelancerDetails!.baseLongitude, 55.2708);
          expect(request.freelancerDetails!.countryCode, 'AE');
          expect(
            request.freelancerDetails!.serviceRadiusMeters,
            greaterThan(0),
          );
          expect(request.freelancerDetails!.skills, ['Electrical wiring']);
          expect(request.freelancerDetails!.yearsExperience, 5);
          expect(request.businessDetails, isNull);

          // Wizard-ending navigation lands on Verification Upload (S-19,
          // VER-001, Plan item 30), not Home.
          expect(find.byType(VerificationUploadScreen), findsOneWidget);
        },
      );
    },
  );
}
