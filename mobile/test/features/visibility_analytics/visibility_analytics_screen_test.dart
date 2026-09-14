import 'package:ai_marketplace_app/features/visibility_analytics/data/visibility_analytics_repository.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics_exception.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/presentation/screens/visibility_analytics_screen.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/presentation/widgets/visibility_trend_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_visibility_analytics_repository.dart';

/// LEAD-002 -- `VisibilityAnalyticsScreen` (`Plan_S10_LEAD-002.md`,
/// AC1-AC4).
void main() {
  testWidgets('shows a loading indicator before the first load resolves', (
    tester,
  ) async {
    final fakeRepository = FakeVisibilityAnalyticsRepository(
      result: buildVisibilityAnalytics(),
    );
    await pumpScreen(
      tester,
      child: const VisibilityAnalyticsScreen(),
      overrides: [
        visibilityAnalyticsRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    // Deliberately no `pumpAndSettle` yet -- asserts the very first
    // rendered frame, before `VisibilityAnalyticsController.load()`'s
    // post-frame-callback trigger has resolved (idle and loading share the
    // same UI branch).
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();
  });

  testWidgets(
    'a load failure shows a plain-language error, with a working retry '
    '(AC3 -- the caller-has-no-provider-yet 404 case)',
    (tester) async {
      final fakeRepository = FakeVisibilityAnalyticsRepository(
        error: const VisibilityAnalyticsException(
          type: VisibilityAnalyticsErrorType.notFound,
        ),
      );
      await pumpScreen(
        tester,
        child: const VisibilityAnalyticsScreen(),
        overrides: [
          visibilityAnalyticsRepositoryProvider.overrideWithValue(
            fakeRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.text("We couldn't find your provider listing."),
        findsOneWidget,
      );
      expect(find.text('Try again'), findsOneWidget);

      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 2);
    },
  );

  group('AC1 -- headline stats and trend labels', () {
    testWidgets('both headline stats render their 30-day totals and labels', (
      tester,
    ) async {
      final data = buildVisibilityAnalytics(
        searchAppearances: const VisibilityMetric(
          totalLast30Days: 123,
          trend: TrendDirection.up,
        ),
        contactViews: const VisibilityMetric(
          totalLast30Days: 9,
          trend: TrendDirection.down,
        ),
      );
      final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
      await pumpScreen(
        tester,
        child: const VisibilityAnalyticsScreen(),
        overrides: [
          visibilityAnalyticsRepositoryProvider.overrideWithValue(
            fakeRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Search appearances'), findsWidgets);
      expect(find.text('Contact views'), findsWidgets);
      expect(find.text('123'), findsOneWidget);
      expect(find.text('9'), findsOneWidget);
    });

    for (final trend in [
      TrendDirection.up,
      TrendDirection.down,
      TrendDirection.flat,
    ]) {
      testWidgets(
        'renders the correct trend label for TrendDirection.${trend.name} '
        'on both headline stats',
        (tester) async {
          final data = buildVisibilityAnalytics(
            searchAppearances: VisibilityMetric(
              totalLast30Days: 5,
              trend: trend,
            ),
            contactViews: VisibilityMetric(totalLast30Days: 3, trend: trend),
          );
          final fakeRepository = FakeVisibilityAnalyticsRepository(
            result: data,
          );
          await pumpScreen(
            tester,
            child: const VisibilityAnalyticsScreen(),
            overrides: [
              visibilityAnalyticsRepositoryProvider.overrideWithValue(
                fakeRepository,
              ),
            ],
          );
          await tester.pumpAndSettle();

          final expectedLabel = switch (trend) {
            TrendDirection.up => 'Up',
            TrendDirection.down => 'Down',
            TrendDirection.flat || TrendDirection.unknown => 'Flat',
          };
          expect(find.text(expectedLabel), findsNWidgets(2));
          expect(
            find.byKey(
              ValueKey(
                'visibility-trend-indicator-search-appearances-${trend.name}',
              ),
            ),
            findsOneWidget,
          );
          expect(
            find.byKey(
              ValueKey(
                'visibility-trend-indicator-contact-views-${trend.name}',
              ),
            ),
            findsOneWidget,
          );
        },
      );
    }

    testWidgets(
      'an unrecognized trend value falls back to the "Flat" copy, never a '
      'blank/crashing indicator (forward-compatibility)',
      (tester) async {
        final data = buildVisibilityAnalytics(
          searchAppearances: const VisibilityMetric(
            totalLast30Days: 5,
            trend: TrendDirection.unknown,
          ),
        );
        final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
        await pumpScreen(
          tester,
          child: const VisibilityAnalyticsScreen(),
          overrides: [
            visibilityAnalyticsRepositoryProvider.overrideWithValue(
              fakeRepository,
            ),
          ],
        );
        await tester.pumpAndSettle();

        expect(find.text('Flat'), findsWidgets);
      },
    );
  });

  group('AC2 -- trend chart', () {
    testWidgets(
      'the chart widget renders without error for a full 30-point fixture',
      (tester) async {
        final dailyTrend = buildDailyTrend(
          searchAppearancesByIndex: {for (var i = 0; i < 30; i++) i: i + 1},
          contactViewsByIndex: {for (var i = 0; i < 30; i++) i: i},
        );
        final data = buildVisibilityAnalytics(dailyTrend: dailyTrend);
        final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
        await pumpScreen(
          tester,
          child: const VisibilityAnalyticsScreen(),
          overrides: [
            visibilityAnalyticsRepositoryProvider.overrideWithValue(
              fakeRepository,
            ),
          ],
        );
        await tester.pumpAndSettle();

        expect(find.byType(VisibilityTrendChart), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  });

  group('AC4 -- "not enough data yet" empty state', () {
    testWidgets(
      'renders instead of the stat cards/chart when hasSufficientData is '
      'false, and is genuinely pull-to-refreshable via a real fling',
      (tester) async {
        final fakeRepository = FakeVisibilityAnalyticsRepository(
          result: buildVisibilityAnalytics(hasSufficientData: false),
        );
        await pumpScreen(
          tester,
          child: const VisibilityAnalyticsScreen(),
          overrides: [
            visibilityAnalyticsRepositoryProvider.overrideWithValue(
              fakeRepository,
            ),
          ],
        );
        await tester.pumpAndSettle();

        expect(
          find.text(
            'Not enough data yet — once customers start finding and '
            'contacting you, your visibility stats will show up here.',
          ),
          findsOneWidget,
        );
        expect(find.byType(VisibilityTrendChart), findsNothing);
        expect(
          find.byKey(const ValueKey('visibility-stat-card-search-appearances')),
          findsNothing,
        );
        expect(find.byType(RefreshIndicator), findsOneWidget);
        expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 1);

        // A real swipe gesture on the scrollable underneath the
        // RefreshIndicator -- not just asserting the widget type exists --
        // per AC4's literal "remains pull-to-refreshable" requirement.
        await tester.fling(
          find.byType(SingleChildScrollView),
          const Offset(0, 300),
          1000,
        );
        await tester.pump();
        await tester.pump(const Duration(seconds: 1));
        await tester.pumpAndSettle();

        expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 2);
      },
    );

    testWidgets('does not render when only one of the two metrics is non-zero '
        '(hasSufficientData is true)', (tester) async {
      // Deliberately asymmetric -- search appearances genuinely zero,
      // contact views genuinely positive -- so this test actually
      // exercises the "only one metric non-zero" case its name claims,
      // not merely the (already-covered-elsewhere) both-non-zero default
      // fixture.
      final fakeRepository = FakeVisibilityAnalyticsRepository(
        result: buildVisibilityAnalytics(
          hasSufficientData: true,
          searchAppearances: const VisibilityMetric(
            totalLast30Days: 0,
            trend: TrendDirection.flat,
          ),
          contactViews: const VisibilityMetric(
            totalLast30Days: 4,
            trend: TrendDirection.up,
          ),
        ),
      );
      await pumpScreen(
        tester,
        child: const VisibilityAnalyticsScreen(),
        overrides: [
          visibilityAnalyticsRepositoryProvider.overrideWithValue(
            fakeRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('visibility-analytics-not-enough-data')),
        findsNothing,
      );
      expect(find.byType(VisibilityTrendChart), findsOneWidget);
    });
  });

  testWidgets(
    'a loaded, sufficient-data body is also genuinely pull-to-refreshable',
    (tester) async {
      final fakeRepository = FakeVisibilityAnalyticsRepository(
        result: buildVisibilityAnalytics(),
      );
      await pumpScreen(
        tester,
        child: const VisibilityAnalyticsScreen(),
        overrides: [
          visibilityAnalyticsRepositoryProvider.overrideWithValue(
            fakeRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 1);

      await tester.fling(
        find.byType(SingleChildScrollView),
        const Offset(0, 300),
        1000,
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 2);
    },
  );
}
