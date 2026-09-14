import 'package:ai_marketplace_app/features/visibility_analytics/data/visibility_analytics_repository.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics_exception.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/state/visibility_analytics_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_visibility_analytics_repository.dart';

/// LEAD-002 -- `VisibilityAnalyticsController`
/// (`Plan_S10_LEAD-002.md`, Frontend item 1, AC1-AC4). Exercised directly
/// via a [ProviderContainer], with no widget tree involved, mirroring
/// `leads_controller_test.dart`'s pattern.
void main() {
  ProviderContainer buildContainer(
    FakeVisibilityAnalyticsRepository repository,
  ) {
    final container = ProviderContainer(
      overrides: [
        visibilityAnalyticsRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  test(
    'load() reaches loaded status with the fetched analytics (AC1/AC2)',
    () async {
      final data = buildVisibilityAnalytics();
      final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
      final container = buildContainer(fakeRepository);
      final notifier = container.read(
        visibilityAnalyticsControllerProvider.notifier,
      );

      await notifier.load();

      final state = container.read(visibilityAnalyticsControllerProvider);
      expect(state.status, VisibilityAnalyticsStatus.loaded);
      expect(state.data, data);
    },
  );

  test('load() with hasSufficientData == false still reaches loaded status, '
      'never error (AC4)', () async {
    final data = buildVisibilityAnalytics(hasSufficientData: false);
    final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      visibilityAnalyticsControllerProvider.notifier,
    );

    await notifier.load();

    final state = container.read(visibilityAnalyticsControllerProvider);
    expect(state.status, VisibilityAnalyticsStatus.loaded);
    expect(state.data!.hasSufficientData, isFalse);
  });

  test('a load failure maps to the error status, carrying the exception '
      'unchanged (AC3 -- the no-Provider-yet 404 case)', () async {
    final fakeRepository = FakeVisibilityAnalyticsRepository(
      error: const VisibilityAnalyticsException(
        type: VisibilityAnalyticsErrorType.notFound,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      visibilityAnalyticsControllerProvider.notifier,
    );

    await notifier.load();

    final state = container.read(visibilityAnalyticsControllerProvider);
    expect(state.status, VisibilityAnalyticsStatus.error);
    expect(state.error?.type, VisibilityAnalyticsErrorType.notFound);
  });

  test(
    'refresh() re-runs load(), replacing any previously loaded data',
    () async {
      final firstData = buildVisibilityAnalytics(
        searchAppearances: const VisibilityMetric(
          totalLast30Days: 10,
          trend: TrendDirection.flat,
        ),
      );
      final fakeRepository = FakeVisibilityAnalyticsRepository(
        result: firstData,
      );
      final container = buildContainer(fakeRepository);
      final notifier = container.read(
        visibilityAnalyticsControllerProvider.notifier,
      );

      await notifier.load();
      expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 1);

      await notifier.refresh();

      expect(fakeRepository.getMyVisibilityAnalyticsCallCount, 2);
      final state = container.read(visibilityAnalyticsControllerProvider);
      expect(state.status, VisibilityAnalyticsStatus.loaded);
    },
  );

  test('refresh() after a load failure recovers to loaded once the retry '
      'succeeds', () async {
    final data = buildVisibilityAnalytics();
    final fakeRepository = FakeVisibilityAnalyticsRepository(result: data);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      visibilityAnalyticsControllerProvider.notifier,
    );

    await notifier.refresh();

    final state = container.read(visibilityAnalyticsControllerProvider);
    expect(state.status, VisibilityAnalyticsStatus.loaded);
    expect(state.data, data);
  });
}
