import 'package:ai_marketplace_app/features/search/domain/models/search_result_provider.dart';
import 'package:ai_marketplace_app/features/search/presentation/widgets/provider_search_card.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// `ProviderSearchCard` (S-08, CLM-001 Decision 8, Mobile item 32) -- the
/// unclaimed banner's exact locked copy/visibility.
void main() {
  const unclaimedBannerText = 'Unclaimed — Is this your business? Claim it';

  const unclaimedProvider = SearchResultProvider(
    id: 'provider-unclaimed',
    displayName: 'Al Noor Plumbing Services LLC',
    slug: 'al-noor-plumbing',
    providerType: ProviderType.business,
    reviewCount: 0,
    distanceMeters: 500,
    isClaimed: false,
  );

  const claimedProvider = SearchResultProvider(
    id: 'provider-claimed',
    displayName: 'Speedy Plumbing',
    slug: 'speedy-plumbing',
    providerType: ProviderType.business,
    reviewCount: 2,
    distanceMeters: 500,
    isClaimed: true,
  );

  Future<void> pumpCard(
    WidgetTester tester, {
    required SearchResultProvider provider,
    VoidCallback? onTap,
    VoidCallback? onClaimTap,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: ProviderSearchCard(
            provider: provider,
            onTap: onTap,
            onClaimTap: onClaimTap,
          ),
        ),
      ),
    );
  }

  testWidgets(
    'renders the full-width Unclaimed banner with the exact locked copy '
    'when isClaimed is false (AC2, Decision 8)',
    (tester) async {
      await pumpCard(tester, provider: unclaimedProvider);

      expect(find.text(unclaimedBannerText), findsOneWidget);
    },
  );

  testWidgets('never renders the Unclaimed banner when isClaimed is true', (
    tester,
  ) async {
    await pumpCard(tester, provider: claimedProvider);

    expect(find.text(unclaimedBannerText), findsNothing);
  });

  testWidgets('tapping the Unclaimed banner calls onClaimTap, never onTap', (
    tester,
  ) async {
    var claimTapCount = 0;
    var cardTapCount = 0;
    await pumpCard(
      tester,
      provider: unclaimedProvider,
      onTap: () => cardTapCount++,
      onClaimTap: () => claimTapCount++,
    );

    await tester.tap(find.text(unclaimedBannerText));
    await tester.pump();

    expect(claimTapCount, 1);
    expect(cardTapCount, 0);
  });

  testWidgets('tapping the rest of a claimed card still calls onTap normally', (
    tester,
  ) async {
    var cardTapCount = 0;
    await pumpCard(
      tester,
      provider: claimedProvider,
      onTap: () => cardTapCount++,
    );

    await tester.tap(find.text('Speedy Plumbing'));
    await tester.pump();

    expect(cardTapCount, 1);
  });
}
