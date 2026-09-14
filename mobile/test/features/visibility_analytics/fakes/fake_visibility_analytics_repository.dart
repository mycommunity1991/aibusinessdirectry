import 'package:ai_marketplace_app/features/visibility_analytics/data/visibility_analytics_repository.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics.dart';
import 'package:ai_marketplace_app/features/visibility_analytics/domain/models/visibility_analytics_exception.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [VisibilityAnalyticsRepository] -- no real
/// Dio/network calls are ever made. Mirrors `fake_lead_repository.dart`'s
/// pattern.
class FakeVisibilityAnalyticsRepository extends VisibilityAnalyticsRepository {
  FakeVisibilityAnalyticsRepository({this.result, this.error}) : super(Dio());

  /// The value `getMyVisibilityAnalytics` resolves with, if [error] is
  /// `null`.
  final VisibilityAnalytics? result;

  /// The failure `getMyVisibilityAnalytics` throws, if any.
  final VisibilityAnalyticsException? error;

  int getMyVisibilityAnalyticsCallCount = 0;

  @override
  Future<VisibilityAnalytics> getMyVisibilityAnalytics() async {
    getMyVisibilityAnalyticsCallCount++;
    if (error != null) {
      throw error!;
    }
    return result!;
  }
}

/// Builds a 30-entry, ascending-date daily series -- defaults to all zeros
/// so a caller only needs to override the handful of days it cares about.
List<VisibilityDailyPoint> buildDailyTrend({
  Map<int, int> searchAppearancesByIndex = const {},
  Map<int, int> contactViewsByIndex = const {},
}) {
  final today = DateTime.utc(2026, 1, 30);
  return [
    for (var i = 0; i < 30; i++)
      VisibilityDailyPoint(
        date: today.subtract(Duration(days: 29 - i)),
        searchAppearances: searchAppearancesByIndex[i] ?? 0,
        contactViews: contactViewsByIndex[i] ?? 0,
      ),
  ];
}

VisibilityAnalytics buildVisibilityAnalytics({
  bool hasSufficientData = true,
  VisibilityMetric searchAppearances = const VisibilityMetric(
    totalLast30Days: 42,
    trend: TrendDirection.up,
  ),
  VisibilityMetric contactViews = const VisibilityMetric(
    totalLast30Days: 7,
    trend: TrendDirection.down,
  ),
  List<VisibilityDailyPoint>? dailyTrend,
}) {
  return VisibilityAnalytics(
    hasSufficientData: hasSufficientData,
    searchAppearances: searchAppearances,
    contactViews: contactViews,
    dailyTrend: dailyTrend ?? buildDailyTrend(),
  );
}
