import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';
import '../models/ranked_provider_result.dart';
import 'provider_result_card.dart';

/// Renders a non-empty, already-ranked list of [RankedProviderResult] as a
/// scrollable column of [ProviderResultCard]s (`Plan_S07_AI-002.md`, Mobile
/// item 25).
///
/// Extracted out of `features/search/presentation/screens/
/// search_results_screen.dart` (S-08, DIR-001) so both `features/search`
/// and `features/conversation` (S-07's ranked-results state once an AI
/// conversation session completes, AI-002 Decision 6) render provider
/// results through this one shared widget -- avoiding a third instance of
/// the direct cross-feature-import debt already logged as
/// `13_OPEN_DECISIONS.md` item 12.
///
/// Deliberately does not own loading/error/empty states -- those differ in
/// copy between the two call sites (Decision 7's "textually distinct empty
/// states" rule) and stay owned by each screen. This widget's only job is
/// rendering an already-resolved, non-empty [results] list plus optional
/// pull-to-refresh, identically regardless of caller.
class RankedProviderResultsList extends StatelessWidget {
  const RankedProviderResultsList({
    super.key,
    required this.results,
    this.onTap,
    this.onClaimTap,
    this.onRefresh,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
  });

  final List<RankedProviderResult> results;

  /// Called with the tapped result's [RankedProviderResult.id] when a card
  /// (other than its unclaimed banner) is tapped.
  final ValueChanged<String>? onTap;

  /// Called with the tapped result's [RankedProviderResult.id] when an
  /// unclaimed card's banner CTA is tapped. Only ever reachable for a
  /// result with `isClaimed == false`.
  final ValueChanged<String>? onClaimTap;

  /// Pull-to-refresh callback. `null` disables pull-to-refresh entirely
  /// (e.g. while a result set is still being polled for, `features/
  /// conversation` may prefer not to offer a redundant manual refresh).
  final Future<void> Function()? onRefresh;

  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final list = ListView.builder(
      key: const ValueKey('ranked-provider-results-list'),
      padding: padding,
      itemCount: results.length,
      itemBuilder: (context, index) {
        final result = results[index];
        return ProviderResultCard(
          provider: result,
          onTap: onTap == null ? null : () => onTap!(result.id),
          onClaimTap: onClaimTap == null ? null : () => onClaimTap!(result.id),
        );
      },
    );

    final refresh = onRefresh;
    if (refresh == null) return list;
    return RefreshIndicator(onRefresh: refresh, child: list);
  }
}
