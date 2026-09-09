import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/location_picker/location_capture_field.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../state/search_filters_controller.dart';
import '../utils/search_error_copy.dart';

/// The minimal, structured (non-AI) Search entry point (S-06's "quick-start
/// category chips" slice, `Plan_S06_DIR-001.md` Decision 6) -- a category
/// chip picker, an editable origin location (pre-filled from the
/// customer's default saved address), and a radius selector, ending in a
/// single "Search" action that navigates to the Search Results screen
/// (S-08) with the chosen filters.
class SearchFiltersScreen extends ConsumerWidget {
  const SearchFiltersScreen({super.key});

  void _onSearch(WidgetRef ref, BuildContext context) {
    final state = ref.read(searchFiltersControllerProvider);
    if (!state.canSearch) return;
    final args = (
      category: state.selectedCategory,
      latitude: state.latitude!,
      longitude: state.longitude!,
      radiusKm: state.radiusKm,
    );
    context.push(AppRoutes.searchResults, extra: args);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(searchFiltersControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.searchFiltersTitle)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _CategorySection(state: state),
              const SizedBox(height: AppSpacing.xl),
              _LocationSection(state: state),
              const SizedBox(height: AppSpacing.xl),
              _RadiusSection(state: state),
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                key: const ValueKey('search-filters-search-button'),
                label: l10n.searchButtonLabel,
                onPressed: state.canSearch
                    ? () => _onSearch(ref, context)
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CategorySection extends ConsumerWidget {
  const _CategorySection({required this.state});

  final SearchFiltersState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.searchCategorySectionTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.sm),
        if (state.isLoadingCategories)
          Center(child: LoadingIndicator(label: l10n.loadingLabel))
        else if (state.categoriesError != null)
          AppErrorMessage(
            message: searchErrorMessage(context, state.categoriesError!),
          )
        else
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              ChoiceChip(
                key: const ValueKey('search-category-chip-all'),
                label: Text(l10n.searchAnyCategoryChipLabel),
                selected: state.selectedCategory == null,
                onSelected: (_) => ref
                    .read(searchFiltersControllerProvider.notifier)
                    .selectCategory(null),
              ),
              for (final category in state.categories)
                ChoiceChip(
                  key: ValueKey('search-category-chip-${category.label}'),
                  label: Text(category.label),
                  selected: state.selectedCategory == category.label,
                  onSelected: (_) => ref
                      .read(searchFiltersControllerProvider.notifier)
                      .selectCategory(category.label),
                ),
            ],
          ),
      ],
    );
  }
}

class _LocationSection extends ConsumerWidget {
  const _LocationSection({required this.state});

  final SearchFiltersState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.searchLocationSectionTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.sm),
        if (state.isLoadingLocation)
          Center(child: LoadingIndicator(label: l10n.loadingLabel))
        else
          Text(
            state.locationLabel ?? l10n.locationNotSetLabel,
            key: const ValueKey('search-location-label'),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        const SizedBox(height: AppSpacing.sm),
        LocationCaptureField(
          onPicked: (result) => ref
              .read(searchFiltersControllerProvider.notifier)
              .setLocation(result),
        ),
      ],
    );
  }
}

class _RadiusSection extends ConsumerWidget {
  const _RadiusSection({required this.state});

  final SearchFiltersState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.searchRadiusValueLabel(state.radiusKm.toStringAsFixed(0)),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        Slider(
          key: const ValueKey('search-radius-slider'),
          value: state.radiusKm,
          min: 1,
          max: SearchFiltersState.maxRadiusKm,
          divisions: SearchFiltersState.maxRadiusKm.toInt() - 1,
          label: state.radiusKm.toStringAsFixed(0),
          onChanged: (value) => ref
              .read(searchFiltersControllerProvider.notifier)
              .setRadiusKm(value),
        ),
      ],
    );
  }
}
