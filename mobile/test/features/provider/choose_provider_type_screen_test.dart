import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider_type.dart';
import 'package:ai_marketplace_app/features/provider/state/provider_onboarding_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_provider_repository.dart';

void main() {
  group('ChooseProviderTypeScreen (S-16, PRO-001, AC9) — step indicator', () {
    testWidgets('renders the step indicator at step 1 of 3', (tester) async {
      await pumpApp(
        tester,
        overrides: [
          providerRepositoryProvider.overrideWithValue(
            FakeProviderRepository(),
          ),
        ],
        initialLocation: AppRoutes.chooseProviderType,
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel('Step 1 of 3'), findsOneWidget);
    });
  });

  group(
    'ChooseProviderTypeScreen (S-16, PRO-001, AC3/AC9) — selection gating',
    () {
      testWidgets('Continue stays disabled until a type card is selected', (
        tester,
      ) async {
        await pumpApp(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(
              FakeProviderRepository(),
            ),
          ],
          initialLocation: AppRoutes.chooseProviderType,
        );
        await tester.pumpAndSettle();

        var continueButton = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Continue'),
        );
        expect(continueButton.onPressed, isNull);

        await tester.tap(find.text('Business'));
        await tester.pumpAndSettle();

        continueButton = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Continue'),
        );
        expect(continueButton.onPressed, isNotNull);
      });

      testWidgets(
        'selecting Business and continuing sets the type and navigates to '
        'Basic Info (AC3 -- the only screen that ever sets provider_type)',
        (tester) async {
          await pumpApp(
            tester,
            overrides: [
              providerRepositoryProvider.overrideWithValue(
                FakeProviderRepository(),
              ),
            ],
            initialLocation: AppRoutes.chooseProviderType,
          );
          await tester.pumpAndSettle();

          await tester.tap(find.text('Business'));
          await tester.pumpAndSettle();
          await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
          await tester.pumpAndSettle();

          expect(find.text('Basic info'), findsOneWidget);

          final container = ProviderScope.containerOf(
            tester.element(find.byType(MaterialApp)),
          );
          expect(
            container.read(providerOnboardingControllerProvider).providerType,
            ProviderType.business,
          );
        },
      );

      testWidgets('selecting Freelancer sets the freelancer type', (
        tester,
      ) async {
        await pumpApp(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(
              FakeProviderRepository(),
            ),
          ],
          initialLocation: AppRoutes.chooseProviderType,
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Freelancer'));
        await tester.pumpAndSettle();
        await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
        await tester.pumpAndSettle();

        final container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp)),
        );
        expect(
          container.read(providerOnboardingControllerProvider).providerType,
          ProviderType.freelancer,
        );
      });
    },
  );
}
