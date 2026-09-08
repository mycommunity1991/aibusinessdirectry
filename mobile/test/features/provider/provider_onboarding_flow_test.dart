import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/customer/data/customer_repository.dart';
import 'package:ai_marketplace_app/features/customer/presentation/screens/profile_settings_screen.dart';
import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider_type.dart';
import 'package:ai_marketplace_app/features/provider/presentation/screens/choose_provider_type_screen.dart';
import 'package:ai_marketplace_app/features/provider/presentation/screens/storefront_screen.dart';
import 'package:ai_marketplace_app/features/provider/state/provider_onboarding_controller.dart';
import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../shared/widgets/location_picker/fakes/fake_location_service.dart';
import '../auth/test_helpers.dart';
import '../customer/fakes/fake_customer_repository.dart';
import '../verification/fakes/fake_verification_repository.dart';
import 'fakes/fake_provider_repository.dart';
import 'test_helpers.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Provider onboarding wizard (PRO-001) — type immutability (AC3)', () {
    testWidgets(
      'the Business type set at S-16 persists unchanged through Basic '
      'Info and Business Details, with no screen ever re-asking',
      (tester) async {
        final fakeRepository = FakeProviderRepository();
        await pumpToProviderBasicInfo(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
          ],
          typeLabel: 'Business',
        );

        var container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp)),
        );
        expect(
          container.read(providerOnboardingControllerProvider).providerType,
          ProviderType.business,
        );
        // Choose Provider Type is never shown again on this path.
        expect(find.byType(ChooseProviderTypeScreen), findsNothing);

        await fillMinimalBasicInfoAndContinue(tester);

        container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp)),
        );
        expect(
          container.read(providerOnboardingControllerProvider).providerType,
          ProviderType.business,
        );
        expect(find.byType(ChooseProviderTypeScreen), findsNothing);
        expect(find.text('Business details'), findsOneWidget);
      },
    );

    testWidgets(
      'the Freelancer type set at S-16 persists unchanged through Basic '
      'Info and Freelancer Details',
      (tester) async {
        final fakeRepository = FakeProviderRepository();
        await pumpToProviderBasicInfo(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
          ],
          typeLabel: 'Freelancer',
        );
        await fillMinimalBasicInfoAndContinue(tester);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp)),
        );
        expect(
          container.read(providerOnboardingControllerProvider).providerType,
          ProviderType.freelancer,
        );
        expect(find.text('Freelancer details'), findsOneWidget);
      },
    );
  });

  group('Provider onboarding wizard (PRO-001, Decision 2) — single end-of-'
      'wizard submission', () {
    testWidgets(
      'completing the Business path submits exactly one createProvider '
      'call with basic info and business details merged',
      (tester) async {
        final fakeRepository = FakeProviderRepository();
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: providerFakeLocationFix,
        );
        await pumpToProviderBasicInfo(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
          typeLabel: 'Business',
        );
        await fillMinimalBasicInfoAndContinue(tester);

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createProviderCallCount, 1);
        final request = fakeRepository.lastCreateRequest!;
        expect(request.providerType, ProviderType.business);
        expect(request.displayName, 'Test Provider');
        expect(request.categoryLabel, 'Plumbing');
        expect(request.businessDetails, isNotNull);
        expect(request.businessDetails!.addressLine, 'Al Wasl Road');
        expect(request.freelancerDetails, isNull);
      },
    );

    testWidgets(
      'completing the Freelancer path submits exactly one createProvider '
      'call with basic info and freelancer details merged',
      (tester) async {
        final fakeRepository = FakeProviderRepository();
        final fakeLocationService = FakeLocationService(
          reverseGeocodeResult: providerFakeLocationFix,
        );
        await pumpToProviderBasicInfo(
          tester,
          overrides: [
            providerRepositoryProvider.overrideWithValue(fakeRepository),
            locationServiceProvider.overrideWithValue(fakeLocationService),
          ],
          typeLabel: 'Freelancer',
        );
        await fillMinimalBasicInfoAndContinue(tester);

        await tester.tap(find.text('Use current location'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(fakeRepository.createProviderCallCount, 1);
        final request = fakeRepository.lastCreateRequest!;
        expect(request.providerType, ProviderType.freelancer);
        expect(request.displayName, 'Test Provider');
        expect(request.categoryLabel, 'Plumbing');
        expect(request.freelancerDetails, isNotNull);
        expect(request.freelancerDetails!.baseLatitude, 25.2048);
        expect(request.businessDetails, isNull);
      },
    );
  });

  group('Provider onboarding wizard (PRO-001 Decision 9 / PRO-002 item 30) — '
      'already-have-a-listing short-circuit (mobile mirror of AC8)', () {
    testWidgets(
      'tapping "List Your Business" when getMyProvider() already returns '
      'a provider navigates to the Storefront screen (S-25), never S-16',
      (tester) async {
        final fakeProviderRepository = FakeProviderRepository(
          existingProvider: fakeExistingBusinessProvider,
        );
        await pumpApp(
          tester,
          overrides: [
            customerRepositoryProvider.overrideWithValue(
              FakeCustomerRepository(),
            ),
            providerRepositoryProvider.overrideWithValue(
              fakeProviderRepository,
            ),
            // The Storefront screen now renders a verification-status
            // chip (VER-001, Plan item 30) -- keep this test hermetic
            // rather than letting it hit the real Dio client.
            verificationRepositoryProvider.overrideWithValue(
              FakeVerificationRepository(),
            ),
          ],
          initialLocation: AppRoutes.profileSettings,
        );
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.text('List Your Business'));
        await tester.tap(find.text('List Your Business'));
        await tester.pumpAndSettle();

        // Called at least once for the pre-navigation check; the
        // Storefront screen's own load also calls it again.
        expect(
          fakeProviderRepository.getMyProviderCallCount,
          greaterThanOrEqualTo(1),
        );
        expect(find.byType(StorefrontScreen), findsOneWidget);
        expect(find.byType(ProfileSettingsScreen), findsNothing);
        expect(find.byType(ChooseProviderTypeScreen), findsNothing);
      },
    );

    testWidgets(
      'tapping "List Your Business" when getMyProvider() returns null '
      'navigates into the wizard intro (S-15)',
      (tester) async {
        final fakeProviderRepository = FakeProviderRepository();
        await pumpApp(
          tester,
          overrides: [
            customerRepositoryProvider.overrideWithValue(
              FakeCustomerRepository(),
            ),
            providerRepositoryProvider.overrideWithValue(
              fakeProviderRepository,
            ),
          ],
          initialLocation: AppRoutes.profileSettings,
        );
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.text('List Your Business'));
        await tester.tap(find.text('List Your Business'));
        await tester.pumpAndSettle();

        expect(fakeProviderRepository.getMyProviderCallCount, 1);
        expect(find.text('List Your Business'), findsWidgets);
        expect(find.text('Get Started'), findsOneWidget);
      },
    );
  });
}
