import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/models/search_exception.dart';
import '../../domain/models/search_filters_args.dart';
import '../../state/search_results_controller.dart';
import '../utils/search_error_copy.dart';
import '../widgets/provider_search_card.dart';

/// S-08 -- Search Results (`Plan_S06_DIR-001.md`, AC3/AC4/AC5). Renders
/// provider cards (photo, name, category labels, rating+count, distance),
/// a loading state, an error state, and Decision 7's two textually
/// distinct empty states:
///  - [SearchResultsStatus.idle] ("no search performed yet") -- reached
///    only if this screen is somehow opened with no [filters] at all; the
///    real app never does this (the Search Filters screen's "Search"
///    action always supplies filters), but the state is real and
///    independently reachable/testable, per Decision 7.
///  - [SearchResultsStatus.loaded] with an empty result list ("this search
///    returned nothing").
///
/// These two copy strings are never the same (AC4).
class SearchResultsScreen extends ConsumerStatefulWidget {
  const SearchResultsScreen({super.key, this.filters});

  final SearchFiltersArgs? filters;

  @override
  ConsumerState<SearchResultsScreen> createState() =>
      _SearchResultsScreenState();
}

class _SearchResultsScreenState extends ConsumerState<SearchResultsScreen> {
  @override
  void initState() {
    super.initState();
    final filters = widget.filters;
    if (filters != null) {
      SchedulerBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ref.read(searchResultsControllerProvider.notifier).search(filters);
      });
    }
  }

  Future<void> _onRefresh() async {
    final filters = widget.filters;
    if (filters == null) return;
    await ref.read(searchResultsControllerProvider.notifier).search(filters);
  }

  void _onCardTap(BuildContext context) {
    // S-09 (the real Provider Profile screen) doesn't exist yet -- a
    // simple "coming soon" acknowledgment is this story's accepted stub,
    // mirroring CUS-002's own precedent for a not-yet-built downstream
    // screen (`Plan_S06_DIR-001.md`, Mobile item 20).
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          AppLocalizations.of(context).providerProfileComingSoonMessage,
        ),
      ),
    );
  }

  /// CLM-001, Decision 8 -- the unclaimed banner's CTA navigates straight
  /// to the Claim OTP screen (S-22) for this specific listing, skipping
  /// the Claim Search screen (S-21) entirely, since the user already found
  /// this exact card here.
  void _onClaimTap(BuildContext context, String providerId) {
    context.push(AppRoutes.claimOtp, extra: providerId);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(searchResultsControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.searchResultsTitle)),
      body: SafeArea(
        child: switch (state.status) {
          SearchResultsStatus.idle => _PreSearchEmptyState(
            message: l10n.searchPreSearchEmptyStateMessage,
          ),
          SearchResultsStatus.loading => Center(
            child: LoadingIndicator(label: l10n.loadingLabel),
          ),
          SearchResultsStatus.error => _ErrorState(
            error: state.error!,
            onRetry: widget.filters == null ? null : _onRefresh,
          ),
          SearchResultsStatus.loaded =>
            state.results.isEmpty
                ? _ZeroResultsEmptyState(
                    message: l10n.searchZeroResultsMessage,
                    onRefresh: _onRefresh,
                  )
                : RefreshIndicator(
                    onRefresh: _onRefresh,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      itemCount: state.results.length,
                      itemBuilder: (context, index) => ProviderSearchCard(
                        provider: state.results[index],
                        onTap: () => _onCardTap(context),
                        onClaimTap: () =>
                            _onClaimTap(context, state.results[index].id),
                      ),
                    ),
                  ),
        },
      ),
    );
  }
}

/// Decision 7 -- the "no search performed yet" empty state, textually
/// distinct from [_ZeroResultsEmptyState] below.
class _PreSearchEmptyState extends StatelessWidget {
  const _PreSearchEmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search,
              size: 48,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              message,
              key: const ValueKey('search-pre-search-empty-state'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }
}

/// Decision 7 -- the "this search returned nothing" empty state,
/// textually distinct from [_PreSearchEmptyState] above. Still pull-to-
/// refresh-able, since widening the search area (the message's own
/// suggestion) usually means re-picking filters and searching again, but a
/// stale zero-result screen should never require a full navigation replay.
class _ZeroResultsEmptyState extends StatelessWidget {
  const _ZeroResultsEmptyState({
    required this.message,
    required this.onRefresh,
  });

  final String message;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
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
                      Icons.location_off_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      message,
                      key: const ValueKey('search-zero-results-empty-state'),
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

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});

  final SearchException error;
  final Future<void> Function()? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(message: searchErrorMessage(context, error)),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpacing.md),
              OutlinedButton(
                onPressed: () => onRetry!(),
                child: Text(l10n.retryLabel),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
