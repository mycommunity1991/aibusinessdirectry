import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/visibility_analytics.dart';

/// LEAD-002 Decision 7 -- a small, dependency-free `CustomPainter`-based
/// dual-series trend chart, in place of a new charting package. Renders two
/// color-coded, non-interactive bar series (search appearances, contact
/// views) over the daily points passed in -- no axes, no zoom/pan, no
/// tooltips (AC2's literal "a chart is shown", not an interactive
/// requirement).
///
/// Pure presentational widget -- computes nothing business-logic-related
/// itself; [dailyTrend] is rendered exactly as given. Must not throw for
/// edge-case inputs (empty, all zeros, a single non-zero day, every day
/// non-zero) -- the painter guards every division against a zero
/// denominator.
class VisibilityTrendChart extends StatelessWidget {
  const VisibilityTrendChart({super.key, required this.dailyTrend});

  final List<VisibilityDailyPoint> dailyTrend;

  static const double _chartHeight = 160;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          key: const ValueKey('visibility-trend-chart'),
          height: _chartHeight,
          width: double.infinity,
          child: CustomPaint(
            painter: _VisibilityTrendChartPainter(
              dailyTrend: dailyTrend,
              searchAppearancesColor: colorScheme.primary,
              contactViewsColor: colorScheme.secondary,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _LegendEntry(
              color: colorScheme.primary,
              label: l10n.visibilityAnalyticsSearchAppearancesLabel,
            ),
            const SizedBox(width: AppSpacing.lg),
            _LegendEntry(
              color: colorScheme.secondary,
              label: l10n.visibilityAnalyticsContactViewsLabel,
            ),
          ],
        ),
      ],
    );
  }
}

/// A single "colored dot + label" legend item (Plan item 2 -- "a small
/// static legend row (two colored dots + labels) below the drawing area").
class _LegendEntry extends StatelessWidget {
  const _LegendEntry({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: AppSpacing.xs),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

/// Draws two side-by-side bar series, one bar-pair per daily point, scaled
/// to the taller of the two series' peak value across the whole window.
/// Deliberately no axes/gridlines/tooltips (Decision 7).
class _VisibilityTrendChartPainter extends CustomPainter {
  const _VisibilityTrendChartPainter({
    required this.dailyTrend,
    required this.searchAppearancesColor,
    required this.contactViewsColor,
  });

  final List<VisibilityDailyPoint> dailyTrend;
  final Color searchAppearancesColor;
  final Color contactViewsColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (dailyTrend.isEmpty || size.width <= 0 || size.height <= 0) return;

    final maxValue = dailyTrend.fold<int>(
      0,
      (max, point) => [
        max,
        point.searchAppearances,
        point.contactViews,
      ].reduce((a, b) => a > b ? a : b),
    );

    final slotWidth = size.width / dailyTrend.length;
    // Each daily slot holds two bars side by side, with small gaps -- never
    // a zero/negative width even for a single-day series.
    final barWidth = (slotWidth / 3).clamp(1.0, double.infinity);

    final searchPaint = Paint()..color = searchAppearancesColor;
    final contactPaint = Paint()..color = contactViewsColor;

    for (var i = 0; i < dailyTrend.length; i++) {
      final point = dailyTrend[i];
      final slotLeft = i * slotWidth;

      // `maxValue == 0` means every day in the window is genuinely zero
      // (the all-zero edge case) -- draw nothing rather than dividing by
      // zero.
      final searchHeight = maxValue == 0
          ? 0.0
          : (point.searchAppearances / maxValue) * size.height;
      final contactHeight = maxValue == 0
          ? 0.0
          : (point.contactViews / maxValue) * size.height;

      canvas.drawRect(
        Rect.fromLTWH(
          slotLeft,
          size.height - searchHeight,
          barWidth,
          searchHeight,
        ),
        searchPaint,
      );
      canvas.drawRect(
        Rect.fromLTWH(
          slotLeft + barWidth + 2,
          size.height - contactHeight,
          barWidth,
          contactHeight,
        ),
        contactPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _VisibilityTrendChartPainter oldDelegate) {
    return oldDelegate.dailyTrend != dailyTrend ||
        oldDelegate.searchAppearancesColor != searchAppearancesColor ||
        oldDelegate.contactViewsColor != contactViewsColor;
  }
}
