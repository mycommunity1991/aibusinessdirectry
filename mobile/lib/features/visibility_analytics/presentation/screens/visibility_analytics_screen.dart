import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/models/visibility_analytics.dart';
import '../../domain/models/visibility_analytics_exception.dart';
import '../../state/visibility_analytics_controller.dart';
import '../utils/visibility_analytics_error_copy.dart';
import '../widgets/visibility_trend_chart.dart';

/// LEAD-002 -- My Visibility (`Plan_S10_LEAD-002.md`, AC1-AC5). Shows the
/// caller's own Provider listing's search-appearances and contact-views
/// headline stats plus a 30-day trend chart, both aggregated entirely
/// server-side from `search.provider_matches`/`contact.contact_views`
/// (Decision 1/2) -- this screen never computes or re-derives any
/// aggregate itself.
class VisibilityAnalyticsScreen extends ConsumerStatefulWidget {
  const VisibilityAnalyticsScreen({super.key});

  @override
  ConsumerState<VisibilityAnalyticsScreen> createState() =>
      _VisibilityAnalyticsScreenState();
}

class _VisibilityAnalyticsScreenState
    extends ConsumerState<VisibilityAnalyticsScreen> {
  @override
  void initState() {
    super.initState();
    // Mirrors `LeadsScreen`'s own post-frame-callback pattern --
    // `VisibilityAnalyticsController` starts idle and never auto-loads
    // itself, so a test can construct it deterministically.
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(visibilityAnalyticsControllerProvider.notifier).load();
    });
  }

  Future<void> _onRefresh() =>
      ref.read(visibilityAnalyticsControllerProvider.notifier).refresh();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(visibilityAnalyticsControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.visibilityAnalyticsScreenTitle)),
      body: SafeArea(
        child: switch (state.status) {
          VisibilityAnalyticsStatus.idle || VisibilityAnalyticsStatus.loading =>
            Center(child: LoadingIndicator(label: l10n.loadingLabel)),
          VisibilityAnalyticsStatus.error => _VisibilityAnalyticsErrorState(
            error: state.error!,
            onRetry: () =>
                ref.read(visibilityAnalyticsControllerProvider.notifier).load(),
          ),
          VisibilityAnalyticsStatus.loaded =>
            state.data!.hasSufficientData
                ? _VisibilityAnalyticsLoadedBody(
                    data: state.data!,
                    onRefresh: _onRefresh,
                  )
                : _NotEnoughDataEmptyState(onRefresh: _onRefresh),
        },
      ),
    );
  }
}

class _VisibilityAnalyticsErrorState extends StatelessWidget {
  const _VisibilityAnalyticsErrorState({
    required this.error,
    required this.onRetry,
  });

  final VisibilityAnalyticsException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(
              message: visibilityAnalyticsErrorMessage(context, error),
            ),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
          ],
        ),
      ),
    );
  }
}

/// The "not enough data yet" state (AC4) -- rendered *instead of* the
/// headline stat cards/chart entirely, textually distinct from the loaded
/// body, still wrapped in a genuinely working [RefreshIndicator] (mirrors
/// `_LeadsEmptyState`'s exact `RefreshIndicator` + `LayoutBuilder` +
/// `ConstrainedBox(minHeight: ...)` scrollable-when-empty shape,
/// `features/leads/presentation/screens/leads_screen.dart`), so a
/// newly-onboarded provider can always pull-to-refresh once real activity
/// starts appearing.
class _NotEnoughDataEmptyState extends StatelessWidget {
  const _NotEnoughDataEmptyState({required this.onRefresh});

  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.insights_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      l10n.visibilityAnalyticsNotEnoughDataMessage,
                      key: const ValueKey(
                        'visibility-analytics-not-enough-data',
                      ),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The loaded body once [VisibilityAnalytics.hasSufficientData] is `true`
/// (AC1/AC2) -- two headline stat cards plus the 30-day trend chart, all
/// inside a genuinely working [RefreshIndicator] over an always-scrollable
/// body (so pull-to-refresh works even if the content is shorter than the
/// viewport).
class _VisibilityAnalyticsLoadedBody extends StatelessWidget {
  const _VisibilityAnalyticsLoadedBody({
    required this.data,
    required this.onRefresh,
  });

  final VisibilityAnalytics data;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: SingleChildScrollView(
        key: const ValueKey('visibility-analytics-loaded-body'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _StatCard(
                    metricKey: 'search-appearances',
                    label: l10n.visibilityAnalyticsSearchAppearancesLabel,
                    metric: data.searchAppearances,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: _StatCard(
                    metricKey: 'contact-views',
                    label: l10n.visibilityAnalyticsContactViewsLabel,
                    metric: data.contactViews,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: VisibilityTrendChart(dailyTrend: data.dailyTrend),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// One headline stat card (AC1) -- the 30-day total plus a compact
/// icon+label trend indicator, mirroring `_LeadOutcomeChip`'s "colored
/// container + icon + label" convention
/// (`features/leads/presentation/screens/leads_screen.dart`).
class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.metricKey,
    required this.label,
    required this.metric,
  });

  /// A stable, human-readable discriminator ("search-appearances"/
  /// "contact-views") used only to key the nested [_TrendIndicator]
  /// uniquely per card -- never rendered.
  final String metricKey;
  final String label;
  final VisibilityMetric metric;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      key: ValueKey('visibility-stat-card-$metricKey'),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: textTheme.bodyMedium),
            const SizedBox(height: AppSpacing.xs),
            Text('${metric.totalLast30Days}', style: textTheme.headlineMedium),
            const SizedBox(height: AppSpacing.sm),
            _TrendIndicator(metricKey: metricKey, trend: metric.trend),
          ],
        ),
      ),
    );
  }
}

/// A compact trend chip -- three visually distinct styles for up/down/flat
/// (AC1), mirroring `_LeadOutcomeChip`'s existing "colored container +
/// icon + label" convention (`features/leads/presentation/screens/
/// leads_screen.dart`).
class _TrendIndicator extends StatelessWidget {
  const _TrendIndicator({required this.metricKey, required this.trend});

  final String metricKey;
  final TrendDirection trend;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    final (label, background, foreground, icon) = switch (trend) {
      TrendDirection.up => (
        l10n.visibilityAnalyticsTrendUpLabel,
        AppColors.successContainer,
        AppColors.onSuccessContainer,
        Icons.arrow_upward,
      ),
      TrendDirection.down => (
        l10n.visibilityAnalyticsTrendDownLabel,
        colorScheme.errorContainer,
        colorScheme.onErrorContainer,
        Icons.arrow_downward,
      ),
      // `unknown` is a forward-compatibility-only fallback (see
      // `TrendDirection.fromWire`'s doc) -- the backend never returns it
      // today, so it renders identically to `flat`, the most honest
      // available bucket, rather than a fourth, invented style.
      TrendDirection.flat || TrendDirection.unknown => (
        l10n.visibilityAnalyticsTrendFlatLabel,
        colorScheme.secondaryContainer,
        colorScheme.onSecondaryContainer,
        Icons.trending_flat,
      ),
    };

    return Container(
      key: ValueKey('visibility-trend-indicator-$metricKey-${trend.name}'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: foreground),
          const SizedBox(width: AppSpacing.xs),
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: foreground),
          ),
        ],
      ),
    );
  }
}
