import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:ai_marketplace_app/features/provider/state/provider_onboarding_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_repository.dart';
import 'test_helpers.dart';

void main() {
  group('ProviderBasicInfoScreen (S-17, PRO-001, AC9) — step indicator', () {
    testWidgets('renders the step indicator at step 2 of 3', (tester) async {
      await pumpToProviderBasicInfo(
        tester,
        overrides: [
          providerRepositoryProvider.overrideWithValue(
            FakeProviderRepository(),
          ),
        ],
        typeLabel: 'Business',
      );

      expect(find.bySemanticsLabel('Step 2 of 3'), findsOneWidget);
    });
  });

  group(
    'ProviderBasicInfoScreen (S-17, PRO-001, AC4/AC9) — required-field gating',
    () {
      testWidgets(
        'Continue stays disabled until display name, phone number, and '
        'category are all filled',
        (tester) async {
          await pumpToProviderBasicInfo(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
            ],
            typeLabel: 'Business',
          );

          var continueButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Continue'),
          );
          expect(continueButton.onPressed, isNull);

          await tester.enterText(
            find.widgetWithText(TextField, 'Display name'),
            'Test Provider',
          );
          await tester.pump();
          continueButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Continue'),
          );
          expect(continueButton.onPressed, isNull);

          await tester.enterText(
            find.widgetWithText(TextField, 'Mobile number'),
            '501234567',
          );
          await tester.pump();
          continueButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Continue'),
          );
          expect(continueButton.onPressed, isNull);

          await tester.enterText(
            find.widgetWithText(TextField, 'Category'),
            'Plumbing',
          );
          await tester.pump();
          continueButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Continue'),
          );
          expect(continueButton.onPressed, isNotNull);
        },
      );

      testWidgets(
        'optional WhatsApp number and description never block Continue',
        (tester) async {
          await pumpToProviderBasicInfo(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
            ],
            typeLabel: 'Business',
          );

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

          // Left blank -- WhatsApp number and description are optional.
          final continueButton = tester.widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Continue'),
          );
          expect(continueButton.onPressed, isNotNull);
        },
      );

      testWidgets(
        'the "same as phone number" toggle copies the phone into WhatsApp',
        (tester) async {
          await pumpToProviderBasicInfo(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
            ],
            typeLabel: 'Business',
          );

          await tester.enterText(
            find.widgetWithText(TextField, 'Mobile number'),
            '501234567',
          );
          await tester.pump();

          await tester.tap(find.text('Same as phone number'));
          await tester.pump();

          final whatsappField = tester.widget<TextField>(
            find.widgetWithText(TextField, 'WhatsApp number (optional)'),
          );
          expect(whatsappField.controller!.text, '+971501234567');
          expect(whatsappField.enabled, isFalse);
        },
      );
    },
  );

  group(
    'ProviderBasicInfoScreen (S-17, PRO-001, AC4) — routes by stored type',
    () {
      testWidgets('continuing on the Business path opens Business Details', (
        tester,
      ) async {
        await pumpToProviderBasicInfo(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(
              FakeProviderRepository(),
            ),
          ],
          typeLabel: 'Business',
        );
        await fillMinimalBasicInfoAndContinue(tester);

        expect(find.text('Business details'), findsOneWidget);
      });

      testWidgets(
        'continuing on the Freelancer path opens Freelancer Details',
        (tester) async {
          await pumpToProviderBasicInfo(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
            ],
            typeLabel: 'Freelancer',
          );
          await fillMinimalBasicInfoAndContinue(tester);

          expect(find.text('Freelancer details'), findsOneWidget);
        },
      );
    },
  );

  testWidgets(
    'basic info is recorded into the onboarding controller on Continue',
    (tester) async {
      await pumpToProviderBasicInfo(
        tester,
        overrides: [
          providerRepositoryProvider.overrideWithValue(
            FakeProviderRepository(),
          ),
        ],
        typeLabel: 'Business',
      );
      await fillMinimalBasicInfoAndContinue(tester);

      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp)),
      );
      final state = container.read(providerOnboardingControllerProvider);
      expect(state.providerType, ProviderType.business);
      expect(state.displayName, 'Test Provider');
      expect(state.phoneCountryCode, '+971');
      expect(state.phoneNumber, '501234567');
      expect(state.categoryLabel, 'Plumbing');
      expect(state.whatsappNumber, isNull);
      expect(state.description, isNull);
    },
  );
}
