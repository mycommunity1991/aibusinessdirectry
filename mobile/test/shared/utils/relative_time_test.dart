import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/utils/relative_time.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// `shared/utils/relative_time.dart` (LEAD-001, AC1's "relative
/// timestamp"). Every fixture is computed as an offset from `DateTime.now()`
/// taken at the start of each test -- a "fixed now" for that test's own
/// duration -- rather than a literal historical date, since
/// [formatRelativeTime] always compares against the real clock.
void main() {
  Future<String> render(WidgetTester tester, DateTime value) async {
    late String result;
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) {
            result = formatRelativeTime(context, value);
            return const SizedBox();
          },
        ),
      ),
    );
    return result;
  }

  testWidgets('a moment under a minute ago renders "Just now"', (tester) async {
    final now = DateTime.now();
    expect(await render(tester, now), 'Just now');
  });

  testWidgets('5 minutes ago renders "5 minutes ago"', (tester) async {
    final now = DateTime.now();
    expect(
      await render(tester, now.subtract(const Duration(minutes: 5))),
      '5 minutes ago',
    );
  });

  testWidgets('1 minute ago renders the singular form', (tester) async {
    final now = DateTime.now();
    expect(
      await render(tester, now.subtract(const Duration(minutes: 1))),
      '1 minute ago',
    );
  });

  testWidgets('3 hours ago renders "3 hours ago"', (tester) async {
    final now = DateTime.now();
    expect(
      await render(tester, now.subtract(const Duration(hours: 3))),
      '3 hours ago',
    );
  });

  testWidgets('4 days ago renders "4 days ago"', (tester) async {
    final now = DateTime.now();
    expect(
      await render(tester, now.subtract(const Duration(days: 4))),
      '4 days ago',
    );
  });

  testWidgets(
    'beyond ~30 days falls back to an absolute short date, not a day count',
    (tester) async {
      final now = DateTime.now();
      final value = now.subtract(const Duration(days: 45));
      final result = await render(tester, value);

      expect(result, isNot(contains('days ago')));
      expect(result, isNot(contains('ago')));
    },
  );
}
