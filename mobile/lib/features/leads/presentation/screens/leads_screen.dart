import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/utils/relative_time.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/models/lead.dart';
import '../../domain/models/lead_exception.dart';
import '../../state/leads_controller.dart';
import '../utils/lead_error_copy.dart';

/// LEAD-001 -- My Leads (`Plan_S10_LEAD-001.md`, AC1-AC5). Lists Contact
/// Views for the caller's own Provider listing, most-recent-first (AC2),
/// each showing only category context / relative time / outcome status --
/// deliberately zero customer-identifying detail anywhere on this screen
/// (AC3, Decision 4).
class LeadsScreen extends ConsumerStatefulWidget {
  const LeadsScreen({super.key});

  @override
  ConsumerState<LeadsScreen> createState() => _LeadsScreenState();
}

class _LeadsScreenState extends ConsumerState<LeadsScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    // Mirrors `SearchResultsScreen`'s own post-frame-callback pattern
    // (`features/search/presentation/screens/search_results_screen.dart`)
    // -- `LeadsController` starts idle and never auto-loads itself, so a
    // test can construct it deterministically (see
    // `leads_controller_test.dart`).
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(leadsControllerProvider.notifier).load();
    });
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final threshold = _scrollController.position.maxScrollExtent - 200;
    if (_scrollController.position.pixels >= threshold) {
      ref.read(leadsControllerProvider.notifier).loadMore();
    }
  }

  Future<void> _onRefresh() =>
      ref.read(leadsControllerProvider.notifier).refresh();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(leadsControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.leadsScreenTitle)),
      body: SafeArea(
        child: switch (state.status) {
          LeadsStatus.idle || LeadsStatus.loading => Center(
            child: LoadingIndicator(label: l10n.loadingLabel),
          ),
          LeadsStatus.error => _LeadsErrorState(
            error: state.error!,
            onRetry: () => ref.read(leadsControllerProvider.notifier).load(),
          ),
          LeadsStatus.loaded =>
            state.leads.isEmpty
                ? _LeadsEmptyState(
                    message: l10n.leadsEmptyStateMessage,
                    onRefresh: _onRefresh,
                  )
                : RefreshIndicator(
                    onRefresh: _onRefresh,
                    child: ListView.builder(
                      key: const ValueKey('leads-list'),
                      controller: _scrollController,
                      // Always scrollable, even when the loaded list is
                      // short enough to fit the viewport -- otherwise a
                      // short list would have no overscroll to pull
                      // against, silently breaking AC2's pull-to-refresh
                      // requirement for exactly that case.
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      itemCount:
                          state.leads.length + (state.isLoadingMore ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index >= state.leads.length) {
                          return const Padding(
                            padding: EdgeInsets.symmetric(
                              vertical: AppSpacing.md,
                            ),
                            child: Center(child: LoadingIndicator(size: 24)),
                          );
                        }
                        return _LeadCard(lead: state.leads[index]);
                      },
                    ),
                  ),
        },
      ),
    );
  }
}

class _LeadsErrorState extends StatelessWidget {
  const _LeadsErrorState({required this.error, required this.onRetry});

  final LeadException error;
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
            AppErrorMessage(message: leadErrorMessage(context, error)),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
          ],
        ),
      ),
    );
  }
}

/// The "no leads yet" empty state (AC2) -- still wrapped in a genuinely
/// working [RefreshIndicator] (mirrors `_ZeroResultsEmptyState`'s exact
/// `RefreshIndicator` + `LayoutBuilder` + `ConstrainedBox(minHeight: ...)`
/// shape, `features/search/presentation/screens/search_results_screen.
/// dart`), so a provider can always pull-to-refresh even while the list is
/// empty.
class _LeadsEmptyState extends StatelessWidget {
  const _LeadsEmptyState({required this.message, required this.onRefresh});

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
                      Icons.visibility_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      message,
                      key: const ValueKey('leads-empty-state'),
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

/// One lead's card -- category context (or Decision 3's honest fallback),
/// a relative timestamp (AC1), and an outcome-status chip (AC1/AC5).
/// Deliberately renders nothing else: [Lead] itself carries no
/// customer-identifying field to render even if this widget wanted to
/// (AC3, Decision 4).
class _LeadCard extends StatelessWidget {
  const _LeadCard({required this.lead});

  final Lead lead;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    lead.categoryName ?? l10n.leadsNoCategoryContextLabel,
                    style: textTheme.titleMedium,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    formatRelativeTime(context, lead.viewedAt),
                    style: textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            _LeadOutcomeChip(status: lead.outcomeStatus),
          ],
        ),
      ),
    );
  }
}

/// A compact outcome-status chip -- three visually distinct styles for
/// Hired/Not hired/Not yet reported (AC1/AC5), mirroring
/// `_VerificationStatusChip`/`_StatusBadge`'s existing "colored container +
/// icon + label" convention (`features/provider/presentation/screens/
/// storefront_screen.dart`, `features/verification/presentation/screens/
/// verification_status_screen.dart`).
class _LeadOutcomeChip extends StatelessWidget {
  const _LeadOutcomeChip({required this.status});

  final LeadOutcomeStatus status;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    final (label, background, foreground, icon) = switch (status) {
      LeadOutcomeStatus.hired => (
        l10n.leadsOutcomeHiredLabel,
        AppColors.successContainer,
        AppColors.onSuccessContainer,
        Icons.check_circle_outline,
      ),
      LeadOutcomeStatus.notHired => (
        l10n.leadsOutcomeNotHiredLabel,
        colorScheme.errorContainer,
        colorScheme.onErrorContainer,
        Icons.cancel_outlined,
      ),
      // `unknown` is a forward-compatibility-only fallback (see `Lead
      // OutcomeStatus.fromWire`'s doc) -- the backend never returns it
      // today, so it renders identically to `notYetReported`, the most
      // honest available bucket, rather than a fourth, invented style.
      LeadOutcomeStatus.notYetReported || LeadOutcomeStatus.unknown => (
        l10n.leadsOutcomeNotYetReportedLabel,
        colorScheme.secondaryContainer,
        colorScheme.onSecondaryContainer,
        Icons.hourglass_top_outlined,
      ),
    };

    return Container(
      key: ValueKey('lead-outcome-chip-${status.name}'),
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
