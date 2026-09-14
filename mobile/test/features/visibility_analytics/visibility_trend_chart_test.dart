import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/presentation/widgets/visibility_trend_chart.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// LEAD-002 Decision 7 -- `VisibilityTrendChart`
/// (`Plan_S10_LEAD-002.md`, Frontend item 2). Confirms the dependency-free
/// `CustomPainter`-based chart paints without throwing for every
/// documented edge-case input.
void main() {
  List<VisibilityDailyPoint> buildTrend(
    List<int> searchAppearances,
    List<int> contactViews,
  ) {
    final today = DateTime.utc(2026, 1, 30);
    return [
      for (var i = 0; i < searchAppearances.length; i++)
        VisibilityDailyPoint(
          date: today.subtract(
            Duration(days: searchAppearances.length - 1 - i),
          ),
          searchAppearances: searchAppearances[i],
          contactViews: contactViews[i],
        ),
    ];
  }

  Future<void> pumpChart(
    WidgetTester tester,
    List<VisibilityDailyPoint> dailyTrend,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: VisibilityTrendChart(dailyTrend: dailyTrend)),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('paints without throwing for 30 days that are all zero', (
    tester,
  ) async {
    final dailyTrend = buildTrend(List.filled(30, 0), List.filled(30, 0));

    await pumpChart(tester, dailyTrend);

    expect(tester.takeException(), isNull);
    expect(find.byType(VisibilityTrendChart), findsOneWidget);
  });

  testWidgets('paints without throwing for a single non-zero day among 30', (
    tester,
  ) async {
    final searchAppearances = List.filled(30, 0);
    final contactViews = List.filled(30, 0);
    searchAppearances[15] = 7;
    contactViews[15] = 3;
    final dailyTrend = buildTrend(searchAppearances, contactViews);

    await pumpChart(tester, dailyTrend);

    expect(tester.takeException(), isNull);
  });

  testWidgets('paints without throwing when all 30 days are non-zero', (
    tester,
  ) async {
    final dailyTrend = buildTrend(
      [for (var i = 0; i < 30; i++) i + 1],
      [for (var i = 0; i < 30; i++) 30 - i],
    );

    await pumpChart(tester, dailyTrend);

    expect(tester.takeException(), isNull);
  });

  testWidgets('paints without throwing for an empty daily trend', (
    tester,
  ) async {
    await pumpChart(tester, const []);

    expect(tester.takeException(), isNull);
  });

  testWidgets('renders the legend row with both series labels', (tester) async {
    final dailyTrend = buildTrend(List.filled(30, 1), List.filled(30, 1));

    await pumpChart(tester, dailyTrend);

    expect(find.text('Search appearances'), findsOneWidget);
    expect(find.text('Contact views'), findsOneWidget);
  });
}
