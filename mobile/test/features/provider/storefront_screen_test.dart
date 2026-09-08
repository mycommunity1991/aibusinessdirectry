import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/portfolio_photo.dart';
import 'package:ai_marketplace_app/features/provider/presentation/screens/storefront_screen.dart';
import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../verification/fakes/fake_verification_repository.dart';
import 'fakes/fake_provider_repository.dart';

Future<void> _pumpStorefront(
  WidgetTester tester,
  FakeProviderRepository repository,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        providerRepositoryProvider.overrideWithValue(repository),
        // The Storefront screen now renders a verification-status chip
        // (VER-001, Plan item 30) -- keep this test hermetic rather than
        // letting it hit the real Dio client.
        verificationRepositoryProvider.overrideWithValue(
          FakeVerificationRepository(),
        ),
      ],
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const StorefrontScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('StorefrontScreen (S-25, PRO-002, item 28) — loading', () {
    testWidgets('renders all four sections for an existing Business provider', (
      tester,
    ) async {
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingBusinessProvider,
      );
      await _pumpStorefront(tester, repository);

      expect(find.text('Basic info'), findsOneWidget);
      expect(find.text('Business details'), findsOneWidget);
      expect(find.text('Portfolio'), findsOneWidget);
      expect(find.text('Availability'), findsOneWidget);
      // Freelancer-only section never renders for a Business provider.
      expect(find.text('Freelancer details'), findsNothing);
    });

    testWidgets('renders the Freelancer details section for a Freelancer '
        'provider, never the Business one', (tester) async {
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingFreelancerProvider,
      );
      await _pumpStorefront(tester, repository);

      expect(find.text('Freelancer details'), findsOneWidget);
      expect(find.text('Business details'), findsNothing);
    });
  });

  group('StorefrontScreen — sections save independently (AC5)', () {
    testWidgets(
      'saving Basic Info calls updateProvider with only basic-info fields, '
      'and touches no other section',
      (tester) async {
        final repository = FakeProviderRepository(
          existingProvider: fakeExistingBusinessProvider,
        );
        await _pumpStorefront(tester, repository);

        await tester.enterText(
          find.widgetWithText(TextField, 'Display name'),
          'Updated Business Name',
        );
        await tester.pump();
        await tester.ensureVisible(
          find.byKey(const ValueKey('storefront-basic-info-save')),
        );
        await tester.tap(
          find.byKey(const ValueKey('storefront-basic-info-save')),
        );
        await tester.pumpAndSettle();

        expect(repository.updateProviderCallCount, 1);
        final request = repository.lastUpdateProviderRequest!;
        expect(request.displayName, 'Updated Business Name');
        expect(request.categoryLabels, isNotNull);
        expect(request.businessDetails, isNull);
        expect(request.freelancerDetails, isNull);

        // No other section's repository call was ever made.
        expect(repository.updateAvailabilityCallCount, 0);
        expect(repository.uploadPortfolioPhotoCallCount, 0);
        expect(repository.deletePortfolioPhotoCallCount, 0);
        expect(repository.reorderPortfolioCallCount, 0);

        expect(find.text('Changes saved.'), findsOneWidget);
      },
    );

    testWidgets('saving Business Details calls updateProvider with only '
        'businessDetails, and never basic-info fields', (tester) async {
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingBusinessProvider,
      );
      await _pumpStorefront(tester, repository);

      await tester.enterText(
        find.widgetWithText(TextField, 'Trade license number (optional)'),
        'TL-999',
      );
      await tester.pump();
      await tester.ensureVisible(
        find.byKey(const ValueKey('storefront-details-save')),
      );
      await tester.tap(find.byKey(const ValueKey('storefront-details-save')));
      await tester.pumpAndSettle();

      expect(repository.updateProviderCallCount, 1);
      final request = repository.lastUpdateProviderRequest!;
      expect(request.businessDetails, isNotNull);
      expect(request.businessDetails!.tradeLicenseNumber, 'TL-999');
      expect(request.displayName, isNull);
      expect(request.categoryLabels, isNull);
      expect(request.freelancerDetails, isNull);

      expect(repository.updateAvailabilityCallCount, 0);
      expect(repository.uploadPortfolioPhotoCallCount, 0);
      expect(repository.deletePortfolioPhotoCallCount, 0);
      expect(repository.reorderPortfolioCallCount, 0);
    });

    testWidgets('saving Freelancer Details calls updateProvider with only '
        'freelancerDetails, and never basic-info fields', (tester) async {
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingFreelancerProvider,
      );
      await _pumpStorefront(tester, repository);

      await tester.ensureVisible(find.widgetWithText(TextField, 'Add a skill'));
      await tester.enterText(
        find.widgetWithText(TextField, 'Add a skill'),
        'Electrical',
      );
      await tester.pump();
      final addSkillButton = find.byIcon(Icons.add_circle_outline).last;
      await tester.ensureVisible(addSkillButton);
      await tester.tap(addSkillButton);
      await tester.pump();

      await tester.ensureVisible(
        find.byKey(const ValueKey('storefront-details-save')),
      );
      await tester.tap(find.byKey(const ValueKey('storefront-details-save')));
      await tester.pumpAndSettle();

      expect(repository.updateProviderCallCount, 1);
      final request = repository.lastUpdateProviderRequest!;
      expect(request.freelancerDetails, isNotNull);
      expect(request.freelancerDetails!.skills, contains('Electrical'));
      expect(request.displayName, isNull);
      expect(request.categoryLabels, isNull);
      expect(request.businessDetails, isNull);

      expect(repository.updateAvailabilityCallCount, 0);
    });

    testWidgets('saving Availability calls updateAvailability only -- never '
        'updateProvider, portfolio, or basic-info fields', (tester) async {
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingFreelancerProvider,
      );
      await _pumpStorefront(tester, repository);

      final mondayRow = find.byKey(const ValueKey('weekly-hours-row-monday'));
      final mondaySwitch = find.descendant(
        of: mondayRow,
        matching: find.byType(Switch),
      );
      await tester.ensureVisible(mondaySwitch.first);
      await tester.tap(mondaySwitch.first);
      await tester.pump();

      await tester.ensureVisible(
        find.byKey(const ValueKey('storefront-availability-save')),
      );
      await tester.tap(
        find.byKey(const ValueKey('storefront-availability-save')),
      );
      await tester.pumpAndSettle();

      expect(repository.updateAvailabilityCallCount, 1);
      expect(repository.updateProviderCallCount, 0);
      expect(repository.uploadPortfolioPhotoCallCount, 0);
      expect(repository.reorderPortfolioCallCount, 0);

      final entries = repository.lastAvailabilityUpdate!;
      final monday = entries.firstWhere((entry) => entry.weekday == 'monday');
      expect(monday.isOpen, isTrue);
    });
  });

  group('StorefrontScreen — portfolio section', () {
    testWidgets('renders the portfolio manager with the loaded photos', (
      tester,
    ) async {
      const photo = PortfolioPhoto(
        id: 'photo-1',
        mediaUrl: '/media/portfolios/test/1.jpg',
        sortOrder: 0,
      );
      final repository = FakeProviderRepository(
        existingProvider: fakeExistingBusinessProvider,
        portfolio: const [photo],
      );
      await _pumpStorefront(tester, repository);

      expect(find.byTooltip('Remove photo'), findsOneWidget);
      expect(
        find.textContaining("haven't added any portfolio photos"),
        findsNothing,
      );
    });
  });
}
