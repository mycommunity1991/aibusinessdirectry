import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// Pumps a single [child] widget under a minimal ProviderScope +
/// localizations shell -- mirrors `features/claim/test_helpers.dart`'s
/// `pumpClaimScreen` pattern, kept local to this feature's tests. The AI
/// Conversation screen never navigates elsewhere internally (all of its
/// interactivity -- revise, start over, quick replies -- is in-screen
/// state), so no `GoRouter` is needed here.
Future<void> pumpConversationScreen(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
  Locale locale = const Locale('en'),
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.light(),
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: child,
      ),
    ),
  );
}

/// Fails if any [Text] widget currently in the tree contains something
/// that looks like a raw confidence/score value (e.g. `0.75`) -- AC6's
/// "never shows a raw confidence score to the user," asserted at the
/// widget-tree level, not just by this screen's models having no such
/// field to render in the first place.
void expectNoConfidenceValueRendered(WidgetTester tester) {
  final texts = tester.widgetList<Text>(find.byType(Text));
  final pattern = RegExp(r'\b[01]\.\d{1,3}\b');
  for (final text in texts) {
    final data = text.data ?? '';
    expect(
      pattern.hasMatch(data),
      isFalse,
      reason: 'Found what looks like a raw confidence value in "$data"',
    );
  }
}
