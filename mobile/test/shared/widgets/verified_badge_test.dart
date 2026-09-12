import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/verified_badge.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// `VerifiedBadge` (`DESIGN.md`'s `badge-verified` component, CON-001,
/// Decision 8) -- always a paired checkmark icon plus a "Verified" text
/// label, never an icon alone (`16_UX_GUIDELINES.md`).
void main() {
  testWidgets('renders the "Verified" text label paired with an icon', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const Scaffold(body: VerifiedBadge()),
      ),
    );

    expect(find.text('Verified'), findsOneWidget);
    expect(find.byIcon(Icons.verified), findsOneWidget);
  });
}
