import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/unclaimed_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// `UnclaimedBanner` (CLM-001, Decision 8; extracted from
/// `ProviderResultCard`'s former private `_UnclaimedBanner` by CON-001,
/// Decision 9, `Plan_S08_CON-001.md`) -- the shared, full-width Warning-
/// color banner now reused by both the search result card (S-08) and the
/// Provider Profile screen (S-09). This is the moved/adapted version of the
/// banner-specific coverage that previously lived only inline inside
/// `provider_result_card_test.dart`.
void main() {
  const bannerText = 'Unclaimed — Is this your business? Claim it';

  Future<void> pumpBanner(WidgetTester tester, {VoidCallback? onTap}) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: UnclaimedBanner(onTap: onTap)),
      ),
    );
  }

  testWidgets('renders the exact locked copy (16_UX_GUIDELINES.md, verbatim)', (
    tester,
  ) async {
    await pumpBanner(tester);

    expect(find.text(bannerText), findsOneWidget);
  });

  testWidgets('tapping the banner calls onTap', (tester) async {
    var tapCount = 0;
    await pumpBanner(tester, onTap: () => tapCount++);

    await tester.tap(find.text(bannerText));
    await tester.pump();

    expect(tapCount, 1);
  });

  testWidgets('renders with no onTap without throwing (defensive)', (
    tester,
  ) async {
    await pumpBanner(tester);

    await tester.tap(find.text(bannerText));
    await tester.pump();

    expect(find.text(bannerText), findsOneWidget);
  });
}
