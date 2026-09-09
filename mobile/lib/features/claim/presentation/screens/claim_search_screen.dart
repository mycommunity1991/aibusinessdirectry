import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/claim_search_result.dart';
import '../../state/claim_search_controller.dart';
import '../utils/claim_error_copy.dart';

/// S-21 — Claim Search (CLM-001, AC3). A free-text search field over
/// still-unclaimed Google-seeded listings by name/address, and a
/// "Select listing" action per result that navigates to the Claim OTP
/// screen (S-22) with the chosen `providerId`.
class ClaimSearchScreen extends ConsumerStatefulWidget {
  const ClaimSearchScreen({super.key});

  @override
  ConsumerState<ClaimSearchScreen> createState() => _ClaimSearchScreenState();
}

class _ClaimSearchScreenState extends ConsumerState<ClaimSearchScreen> {
  final _queryController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _queryController.addListener(_onChanged);
  }

  void _onChanged() => setState(() {});

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  void _onSearch() {
    FocusScope.of(context).unfocus();
    ref
        .read(claimSearchControllerProvider.notifier)
        .search(_queryController.text);
  }

  void _onSelect(ClaimSearchResult result) {
    context.push(AppRoutes.claimOtp, extra: result.id);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(claimSearchControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.claimSearchTitle)),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l10n.claimSearchSubtitle,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.claimSearchFieldLabel,
                controller: _queryController,
                textInputAction: TextInputAction.search,
              ),
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(
                key: const ValueKey('claim-search-button'),
                label: l10n.searchButtonLabel,
                isLoading: state.status == ClaimSearchStatus.loading,
                onPressed: _queryController.text.trim().isEmpty
                    ? null
                    : _onSearch,
              ),
              const SizedBox(height: AppSpacing.lg),
              Expanded(child: _buildBody(context, state)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody(BuildContext context, ClaimSearchState state) {
    final l10n = AppLocalizations.of(context);

    return switch (state.status) {
      ClaimSearchStatus.idle => _EmptyState(
        message: l10n.claimSearchIdleMessage,
      ),
      ClaimSearchStatus.loading => Center(
        child: LoadingIndicator(label: l10n.loadingLabel),
      ),
      ClaimSearchStatus.error => Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: AppErrorMessage(
            message: claimErrorMessage(context, state.error!),
          ),
        ),
      ),
      ClaimSearchStatus.loaded =>
        state.results.isEmpty
            ? _EmptyState(message: l10n.claimSearchZeroResultsMessage)
            : ListView.builder(
                itemCount: state.results.length,
                itemBuilder: (context, index) => _ClaimResultTile(
                  result: state.results[index],
                  onSelect: () => _onSelect(state.results[index]),
                ),
              ),
    };
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        message,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodyLarge,
      ),
    );
  }
}

class _ClaimResultTile extends StatelessWidget {
  const _ClaimResultTile({required this.result, required this.onSelect});

  final ClaimSearchResult result;
  final VoidCallback onSelect;

  String? _addressText() {
    final parts = [
      if (result.addressLine != null && result.addressLine!.isNotEmpty)
        result.addressLine!,
      if (result.city != null && result.city!.isNotEmpty) result.city!,
    ];
    return parts.isEmpty ? null : parts.join(', ');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final addressText = _addressText();

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(result.displayName, style: textTheme.titleMedium),
            if (addressText != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                addressText,
                style: textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (result.phoneNumberMasked != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(result.phoneNumberMasked!, style: textTheme.bodySmall),
            ],
            const SizedBox(height: AppSpacing.sm),
            OutlinedButton(
              onPressed: onSelect,
              child: Text(l10n.claimSelectListingLabel),
            ),
          ],
        ),
      ),
    );
  }
}
