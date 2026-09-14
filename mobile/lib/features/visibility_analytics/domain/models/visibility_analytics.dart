/// Mirrors the backend's `TrendDirection` `StrEnum`
/// (`backend/app/modules/contact/schemas.py`, LEAD-002, Decision 5) --
/// computed server-side by comparing the current 30-day window against the
/// immediately preceding one, never re-derived from raw counts on this side
/// (AC1).
enum TrendDirection {
  up,
  down,
  flat,

  /// Forward-compatibility fallback for a string this app doesn't
  /// recognize yet -- mirrors `LeadOutcomeStatus.fromWire`'s own
  /// defensive-only `unknown` case (`features/leads/domain/models/
  /// lead.dart`). The backend's `TrendDirection` enum has exactly three
  /// values today.
  unknown;

  static TrendDirection fromWire(String value) => switch (value) {
    'up' => TrendDirection.up,
    'down' => TrendDirection.down,
    'flat' => TrendDirection.flat,
    _ => TrendDirection.unknown,
  };
}

/// Mirrors the backend's `VisibilityMetric`
/// (`backend/app/modules/contact/schemas.py`, LEAD-002) -- one headline
/// stat's 30-day total plus its short trend indicator (AC1).
class VisibilityMetric {
  const VisibilityMetric({required this.totalLast30Days, required this.trend});

  factory VisibilityMetric.fromJson(Map<String, dynamic> json) {
    return VisibilityMetric(
      totalLast30Days: (json['total_last_30_days'] as num).toInt(),
      trend: TrendDirection.fromWire(json['trend'] as String),
    );
  }

  final int totalLast30Days;
  final TrendDirection trend;
}

/// Mirrors the backend's `VisibilityDailyPoint`
/// (`backend/app/modules/contact/schemas.py`, LEAD-002) -- one zero-filled
/// calendar day's pair of counts (Decision 4). Deliberately carries no
/// customer-identifying or per-event field (Decision 8).
class VisibilityDailyPoint {
  const VisibilityDailyPoint({
    required this.date,
    required this.searchAppearances,
    required this.contactViews,
  });

  factory VisibilityDailyPoint.fromJson(Map<String, dynamic> json) {
    return VisibilityDailyPoint(
      date: DateTime.parse(json['date'] as String),
      searchAppearances: (json['search_appearances'] as num).toInt(),
      contactViews: (json['contact_views'] as num).toInt(),
    );
  }

  final DateTime date;
  final int searchAppearances;
  final int contactViews;
}

/// Mirrors the backend's `VisibilityAnalyticsResponse`
/// (`backend/app/modules/contact/schemas.py`, LEAD-002, Decision 3) --
/// `GET /providers/me/visibility-analytics`'s single, non-paginated
/// payload.
class VisibilityAnalytics {
  const VisibilityAnalytics({
    required this.hasSufficientData,
    required this.searchAppearances,
    required this.contactViews,
    required this.dailyTrend,
  });

  factory VisibilityAnalytics.fromJson(Map<String, dynamic> json) {
    return VisibilityAnalytics(
      hasSufficientData: json['has_sufficient_data'] as bool,
      searchAppearances: VisibilityMetric.fromJson(
        json['search_appearances'] as Map<String, dynamic>,
      ),
      contactViews: VisibilityMetric.fromJson(
        json['contact_views'] as Map<String, dynamic>,
      ),
      dailyTrend: (json['daily_trend'] as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .map(VisibilityDailyPoint.fromJson)
          .toList(),
    );
  }

  /// AC4's explicit gate -- the mobile client branches purely on this
  /// boolean, never re-deriving "is this enough" from the numbers itself
  /// (Decision 6).
  final bool hasSufficientData;
  final VisibilityMetric searchAppearances;
  final VisibilityMetric contactViews;

  /// Always exactly 30 ascending-date entries, zero-filled server-side
  /// (Decision 4) -- even when [hasSufficientData] is `false`.
  final List<VisibilityDailyPoint> dailyTrend;
}
