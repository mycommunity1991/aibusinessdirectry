import 'package:ai_marketplace_app/features/claim/data/claim_repository.dart';
import 'package:ai_marketplace_app/features/claim/domain/models/claim_search_result.dart';
import 'package:ai_marketplace_app/features/claim/presentation/screens/claim_search_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_claim_repository.dart';
import 'test_helpers.dart';

/// S-21 -- Claim Search (CLM-001, AC3).
void main() {
  const result = ClaimSearchResult(
    id: 'provider-1',
    displayName: 'Al Noor Plumbing Services LLC',
    addressLine: 'Al Wasl Road',
    city: 'Dubai',
    phoneNumberMasked: '+971 5*****67',
  );

  testWidgets(
    'renders results from the repository after searching, and "Select '
    'listing" navigates to the Claim OTP screen with the chosen providerId '
    '(AC3)',
    (tester) async {
      final fakeRepository = FakeClaimRepository(searchResults: [result]);

      await pumpClaimScreen(
        tester,
        child: const ClaimSearchScreen(),
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Al Noor');
      await tester.pump();
      await tester.tap(find.widgetWithText(FilledButton, 'Search'));
      await tester.pumpAndSettle();

      expect(fakeRepository.searchUnclaimedCallCount, 1);
      expect(fakeRepository.lastSearchQuery, 'Al Noor');
      expect(find.text('Al Noor Plumbing Services LLC'), findsOneWidget);
      expect(find.textContaining('Al Wasl Road'), findsOneWidget);
      expect(find.text('+971 5*****67'), findsOneWidget);

      await tester.tap(find.widgetWithText(OutlinedButton, 'Select listing'));
      await tester.pumpAndSettle();

      expect(find.text('claim-otp-stub-provider-1'), findsOneWidget);
    },
  );

  testWidgets(
    'shows the pre-search idle message before any search, distinct from '
    'the zero-results message, and never calls the repository',
    (tester) async {
      final fakeRepository = FakeClaimRepository();

      await pumpClaimScreen(
        tester,
        child: const ClaimSearchScreen(),
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(
        find.text(
          "Search by your business's name or address to find your listing.",
        ),
        findsOneWidget,
      );
      expect(fakeRepository.searchUnclaimedCallCount, 0);
    },
  );

  testWidgets(
    'a search returning zero results shows the post-search "no results" '
    'copy',
    (tester) async {
      final fakeRepository = FakeClaimRepository(searchResults: const []);

      await pumpClaimScreen(
        tester,
        child: const ClaimSearchScreen(),
        overrides: [claimRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'nonexistent');
      await tester.pump();
      await tester.tap(find.widgetWithText(FilledButton, 'Search'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('No unclaimed listings match this search'),
        findsOneWidget,
      );
    },
  );
}
