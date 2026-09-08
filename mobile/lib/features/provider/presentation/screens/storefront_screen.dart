import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/data/verification_status_summary_repository.dart';
import '../../../../shared/models/provider_type.dart';
import '../../../../shared/models/verification_status_summary.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/location_picker/location_capture_field.dart';
import '../../../../shared/widgets/location_picker/location_pick_result.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/weekly_hours_editor.dart';
import '../../domain/models/portfolio_photo.dart';
import '../../domain/models/provider.dart' as domain;
import '../../domain/models/provider_exception.dart';
import '../../domain/models/update_provider_request.dart';
import '../../domain/models/weekday_availability.dart';
import '../../state/storefront_controller.dart';
import '../utils/provider_error_copy.dart';
import '../widgets/portfolio_manager.dart';

/// S-25 — Manage My Storefront (PRO-002): the ongoing storefront-editing
/// screen, distinct from PRO-001's one-time onboarding wizard. Four
/// independently-saveable sections (AC5) -- basic info (incl. category
/// labels), subtype-specific details, portfolio, and availability -- each
/// with its own Save action, loading state, and error/success feedback
/// (`docs/AI/16_UX_GUIDELINES.md`: "every user-initiated action gets
/// acknowledgment"). Saving one section never resubmits another's fields.
class StorefrontScreen extends ConsumerWidget {
  const StorefrontScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(storefrontControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.storefrontTitle)),
      body: SafeArea(
        child: state.isLoading
            ? Center(child: LoadingIndicator(label: l10n.loadingLabel))
            : state.loadError != null
            ? _LoadError(error: state.loadError!)
            : _StorefrontSections(provider: state.provider!, state: state),
      ),
    );
  }
}

class _LoadError extends ConsumerWidget {
  const _LoadError({required this.error});

  final ProviderException error;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(message: providerErrorMessage(context, error)),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(
              onPressed: () =>
                  ref.read(storefrontControllerProvider.notifier).load(),
              child: Text(l10n.retryLabel),
            ),
          ],
        ),
      ),
    );
  }
}

class _StorefrontSections extends StatelessWidget {
  const _StorefrontSections({required this.provider, required this.state});

  final domain.Provider provider;
  final StorefrontState state;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _VerificationStatusChip(),
          const SizedBox(height: AppSpacing.lg),
          _BasicInfoSection(provider: provider),
          if (provider.providerType == ProviderType.business &&
              provider.businessProfile != null)
            _BusinessDetailsSection(profile: provider.businessProfile!),
          if (provider.providerType == ProviderType.freelancer &&
              provider.freelancerProfile != null)
            _FreelancerDetailsSection(profile: provider.freelancerProfile!),
          _PortfolioSection(photos: state.portfolio),
          _AvailabilitySection(availability: state.availability),
        ],
      ),
    );
  }
}

/// A titled card wrapper shared by every Storefront section -- keeps each
/// section's own visual grouping consistent without a new named component
/// (`docs/AI/07_UI_GUIDELINES.md`'s `card-standard`).
class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            child,
          ],
        ),
      ),
    );
  }
}

void _showSavedSnackBar(BuildContext context) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(AppLocalizations.of(context).changesSavedMessage)),
  );
}

/// A small verification-status chip/banner linking to S-20 (VER-001,
/// Decision, Mobile item 30) -- the most reasonable available entry point
/// to Verification given the Provider Dashboard (S-23) hasn't been built
/// by any prior story. Reads its data from the shared
/// [verificationStatusSummaryProvider] (`shared/data/`), not
/// `features/verification/`, so `features/provider/` never depends
/// directly on another feature (`docs/AI/02_ARCHITECTURE.md`: "Features
/// must not depend directly on each other. Shared functionality belongs
/// in shared modules.") -- only the `AppRoutes.verificationStatus` route
/// constant (from `core/routing/`) crosses into Verification's screen.
class _VerificationStatusChip extends ConsumerWidget {
  const _VerificationStatusChip();

  String _labelFor(AppLocalizations l10n, VerificationStatusSummary? summary) {
    return switch (summary) {
      null || VerificationStatusSummary.notStarted =>
        l10n.verificationStatusChipNotStartedLabel,
      VerificationStatusSummary.underReview =>
        l10n.verificationStatusUnderReviewBadge,
      VerificationStatusSummary.approved =>
        l10n.verificationStatusApprovedBadge,
      VerificationStatusSummary.rejected =>
        l10n.verificationStatusRejectedBadge,
    };
  }

  IconData _iconFor(VerificationStatusSummary? summary) {
    return switch (summary) {
      null || VerificationStatusSummary.notStarted => Icons.verified_outlined,
      VerificationStatusSummary.underReview => Icons.hourglass_top_outlined,
      VerificationStatusSummary.approved => Icons.verified_outlined,
      VerificationStatusSummary.rejected => Icons.error_outline,
    };
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final asyncSummary = ref.watch(verificationStatusSummaryProvider);

    if (asyncSummary.isLoading) return const SizedBox.shrink();

    final summary = asyncSummary.valueOrNull;

    return InkWell(
      key: const ValueKey('storefront-verification-status-chip'),
      borderRadius: BorderRadius.circular(AppRadius.small),
      onTap: () => context.push(AppRoutes.verificationStatus),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(AppRadius.small),
        ),
        child: Row(
          children: [
            Icon(_iconFor(summary), color: colorScheme.onSecondaryContainer),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                _labelFor(l10n, summary),
                style: TextStyle(color: colorScheme.onSecondaryContainer),
              ),
            ),
            Icon(Icons.chevron_right, color: colorScheme.onSecondaryContainer),
          ],
        ),
      ),
    );
  }
}

/// Section (a): basic info -- display name, phone, WhatsApp, description,
/// and the category-labels editor (Decision 1, `Plan_S04_PRO-002.md` --
/// category labels are edited as part of basic info). Save calls
/// [StorefrontController.saveBasicInfo] only.
class _BasicInfoSection extends ConsumerStatefulWidget {
  const _BasicInfoSection({required this.provider});

  final domain.Provider provider;

  @override
  ConsumerState<_BasicInfoSection> createState() => _BasicInfoSectionState();
}

class _BasicInfoSectionState extends ConsumerState<_BasicInfoSection> {
  late final _displayNameController = TextEditingController(
    text: widget.provider.displayName,
  );
  late final _phoneCountryCodeController = TextEditingController(
    text: widget.provider.phoneCountryCode ?? '',
  );
  late final _phoneNumberController = TextEditingController(
    text: widget.provider.phoneNumber ?? '',
  );
  late final _whatsappController = TextEditingController(
    text: widget.provider.whatsappNumber ?? '',
  );
  late final _descriptionController = TextEditingController(
    text: widget.provider.description ?? '',
  );
  late List<domain.CategoryLabel> _categoryLabels = List.of(
    widget.provider.categoryLabels,
  );

  @override
  void dispose() {
    _displayNameController.dispose();
    _phoneCountryCodeController.dispose();
    _phoneNumberController.dispose();
    _whatsappController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  bool get _canSave =>
      _displayNameController.text.trim().isNotEmpty &&
      _phoneCountryCodeController.text.trim().isNotEmpty &&
      _phoneNumberController.text.trim().isNotEmpty &&
      _categoryLabels.isNotEmpty &&
      _categoryLabels.where((label) => label.isPrimary).length == 1;

  Future<void> _onSave() async {
    if (!_canSave) return;
    final whatsapp = _whatsappController.text.trim();
    final description = _descriptionController.text.trim();
    final ok = await ref
        .read(storefrontControllerProvider.notifier)
        .saveBasicInfo(
          displayName: _displayNameController.text.trim(),
          phoneCountryCode: _phoneCountryCodeController.text.trim(),
          phoneNumber: _phoneNumberController.text.trim(),
          whatsappNumber: whatsapp.isEmpty ? null : whatsapp,
          description: description.isEmpty ? null : description,
          categoryLabels: _categoryLabels,
        );
    if (!mounted || !ok) return;
    _showSavedSnackBar(context);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(storefrontControllerProvider);

    return _SectionCard(
      title: l10n.storefrontBasicInfoSectionTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (state.basicInfoError != null) ...[
            AppErrorMessage(
              message: providerErrorMessage(context, state.basicInfoError!),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          AppTextField(
            label: l10n.providerDisplayNameFieldLabel,
            controller: _displayNameController,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              SizedBox(
                width: 96,
                child: AppTextField(
                  label: l10n.countryCodeFieldLabel,
                  controller: _phoneCountryCodeController,
                  keyboardType: TextInputType.phone,
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: AppTextField(
                  label: l10n.phoneNumberFieldLabel,
                  controller: _phoneNumberController,
                  keyboardType: TextInputType.phone,
                  onChanged: (_) => setState(() {}),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            label: l10n.providerWhatsappFieldLabel,
            controller: _whatsappController,
            keyboardType: TextInputType.phone,
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            label: l10n.providerDescriptionFieldLabel,
            controller: _descriptionController,
          ),
          const SizedBox(height: AppSpacing.lg),
          _CategoryLabelsEditor(
            labels: _categoryLabels,
            onChanged: (labels) => setState(() => _categoryLabels = labels),
          ),
          const SizedBox(height: AppSpacing.lg),
          PrimaryButton(
            key: const ValueKey('storefront-basic-info-save'),
            label: l10n.saveLabel,
            isLoading: state.basicInfoSaving,
            onPressed: _canSave && !state.basicInfoSaving ? _onSave : null,
          ),
        ],
      ),
    );
  }
}

/// The category-labels editor (PRO-002, Decision 1) -- up to 5 free-text
/// labels, exactly one primary. The first label added becomes primary by
/// construction; tapping any chip's star switches primary to it.
class _CategoryLabelsEditor extends StatefulWidget {
  const _CategoryLabelsEditor({required this.labels, required this.onChanged});

  final List<domain.CategoryLabel> labels;
  final ValueChanged<List<domain.CategoryLabel>> onChanged;

  static const maxLabels = 5;

  @override
  State<_CategoryLabelsEditor> createState() => _CategoryLabelsEditorState();
}

class _CategoryLabelsEditorState extends State<_CategoryLabelsEditor> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _add() {
    final text = _controller.text.trim();
    if (text.isEmpty ||
        widget.labels.length >= _CategoryLabelsEditor.maxLabels) {
      return;
    }
    if (widget.labels.any(
      (label) => label.label.toLowerCase() == text.toLowerCase(),
    )) {
      return;
    }
    final isFirst = widget.labels.isEmpty;
    widget.onChanged([
      ...widget.labels,
      domain.CategoryLabel(label: text, isPrimary: isFirst),
    ]);
    setState(_controller.clear);
  }

  void _remove(domain.CategoryLabel label) {
    final remaining = widget.labels
        .where((existing) => existing.label != label.label)
        .toList();
    if (label.isPrimary && remaining.isNotEmpty) {
      remaining[0] = domain.CategoryLabel(
        label: remaining[0].label,
        isPrimary: true,
      );
    }
    widget.onChanged(remaining);
  }

  void _setPrimary(domain.CategoryLabel label) {
    widget.onChanged([
      for (final existing in widget.labels)
        domain.CategoryLabel(
          label: existing.label,
          isPrimary: existing.label == label.label,
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.storefrontCategoriesSectionTitle,
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: AppSpacing.sm),
        if (widget.labels.isNotEmpty)
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              for (final label in widget.labels)
                InputChip(
                  key: ValueKey('category-chip-${label.label}'),
                  avatar: Icon(
                    label.isPrimary ? Icons.star : Icons.star_border,
                  ),
                  tooltip: l10n.setPrimaryCategoryTooltip,
                  label: Text(label.label),
                  onPressed: () => _setPrimary(label),
                  onDeleted: () => _remove(label),
                ),
            ],
          ),
        if (widget.labels.length < _CategoryLabelsEditor.maxLabels) ...[
          const SizedBox(height: AppSpacing.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: AppTextField(
                  label: l10n.providerCategoryFieldLabel,
                  hintText: l10n.providerCategoryFieldHint,
                  controller: _controller,
                  textInputAction: TextInputAction.done,
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              IconButton(
                icon: const Icon(Icons.add_circle_outline),
                onPressed: _controller.text.trim().isEmpty ? null : _add,
              ),
            ],
          ),
        ],
      ],
    );
  }
}

/// Section (b), Business path: address/map location, weekly operating
/// hours (PRO-001's `business_profiles.operating_hours` field -- distinct
/// from the new provider-level Availability section below), an optional
/// delivery radius, and an optional trade license number. Save calls
/// [StorefrontController.saveBusinessDetails] only.
class _BusinessDetailsSection extends ConsumerStatefulWidget {
  const _BusinessDetailsSection({required this.profile});

  final domain.BusinessProfile profile;

  @override
  ConsumerState<_BusinessDetailsSection> createState() =>
      _BusinessDetailsSectionState();
}

class _BusinessDetailsSectionState
    extends ConsumerState<_BusinessDetailsSection> {
  late final _addressLineController = TextEditingController(
    text: widget.profile.addressLine,
  );
  late final _cityController = TextEditingController(
    text: widget.profile.city ?? '',
  );
  late final _regionController = TextEditingController(
    text: widget.profile.region ?? '',
  );
  late final _tradeLicenseController = TextEditingController(
    text: widget.profile.tradeLicenseNumber ?? '',
  );

  late double? _latitude = widget.profile.latitude;
  late double? _longitude = widget.profile.longitude;
  late bool _offersDelivery = widget.profile.deliveryRadiusMeters != null;
  late double _deliveryRadiusMeters =
      (widget.profile.deliveryRadiusMeters ?? 5000).toDouble();
  late final Map<String, WeeklyHoursDayValue> _hours = {
    for (final day in weeklyHoursOrderedDays)
      day: _dayValueFrom(widget.profile.operatingHours?[day]),
  };

  static WeeklyHoursDayValue _dayValueFrom(domain.OperatingHoursEntry? entry) {
    if (entry == null) {
      return const WeeklyHoursDayValue(
        isOpen: false,
        openTime: TimeOfDay(hour: 9, minute: 0),
        closeTime: TimeOfDay(hour: 18, minute: 0),
      );
    }
    return WeeklyHoursDayValue(
      isOpen: true,
      openTime: parseTimeOfDay(entry.open),
      closeTime: parseTimeOfDay(entry.close),
    );
  }

  @override
  void dispose() {
    _addressLineController.dispose();
    _cityController.dispose();
    _regionController.dispose();
    _tradeLicenseController.dispose();
    super.dispose();
  }

  bool get _hasLocation => _latitude != null && _longitude != null;

  bool get _canSave => _addressLineController.text.trim().isNotEmpty;

  void _applyPickResult(LocationPickResult result) {
    setState(() {
      _latitude = result.latitude;
      _longitude = result.longitude;
      if (result.addressLine != null) {
        _addressLineController.text = result.addressLine!;
      }
      if (result.city != null) _cityController.text = result.city!;
      if (result.region != null) _regionController.text = result.region!;
    });
  }

  Map<String, domain.OperatingHoursEntry?>? _buildOperatingHours() {
    if (_hours.values.every((day) => !day.isOpen)) return null;
    return {
      for (final day in weeklyHoursOrderedDays)
        day: _hours[day]!.isOpen
            ? domain.OperatingHoursEntry(
                open: formatTimeOfDay(_hours[day]!.openTime!),
                close: formatTimeOfDay(_hours[day]!.closeTime!),
              )
            : null,
    };
  }

  Future<void> _onSave() async {
    if (!_canSave) return;
    final city = _cityController.text.trim();
    final region = _regionController.text.trim();
    final tradeLicense = _tradeLicenseController.text.trim();
    final ok = await ref
        .read(storefrontControllerProvider.notifier)
        .saveBusinessDetails(
          UpdateBusinessDetails(
            addressLine: _addressLineController.text.trim(),
            city: city.isEmpty ? null : city,
            region: region.isEmpty ? null : region,
            latitude: _latitude,
            longitude: _longitude,
            operatingHours: _buildOperatingHours(),
            deliveryRadiusMeters: _offersDelivery
                ? _deliveryRadiusMeters.round()
                : null,
            tradeLicenseNumber: tradeLicense.isEmpty ? null : tradeLicense,
          ),
        );
    if (!mounted || !ok) return;
    _showSavedSnackBar(context);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(storefrontControllerProvider);

    return _SectionCard(
      title: l10n.businessDetailsTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (state.detailsError != null) ...[
            AppErrorMessage(
              message: providerErrorMessage(context, state.detailsError!),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          AppTextField(
            label: l10n.addressLineFieldLabel,
            controller: _addressLineController,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            label: l10n.addressCityFieldLabel,
            controller: _cityController,
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            label: l10n.addressRegionFieldLabel,
            controller: _regionController,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            _hasLocation
                ? l10n.locationPinnedLabel(
                    _latitude!.toStringAsFixed(4),
                    _longitude!.toStringAsFixed(4),
                  )
                : l10n.locationNotSetLabel,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          LocationCaptureField(onPicked: _applyPickResult),
          const SizedBox(height: AppSpacing.xl),
          Text(
            l10n.operatingHoursLabel,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          WeeklyHoursEditor(
            values: _hours,
            onChanged: (day, value) => setState(() => _hours[day] = value),
          ),
          const SizedBox(height: AppSpacing.xl),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.offersDeliveryLabel),
            value: _offersDelivery,
            onChanged: (value) => setState(() => _offersDelivery = value),
          ),
          if (_offersDelivery) ...[
            Text(
              l10n.deliveryRadiusValueLabel(
                (_deliveryRadiusMeters / 1000).toStringAsFixed(1),
              ),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            Slider(
              value: _deliveryRadiusMeters,
              min: 500,
              max: 20000,
              divisions: 39,
              onChanged: (value) =>
                  setState(() => _deliveryRadiusMeters = value),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            label: l10n.tradeLicenseNumberFieldLabel,
            controller: _tradeLicenseController,
          ),
          const SizedBox(height: AppSpacing.xl),
          PrimaryButton(
            key: const ValueKey('storefront-details-save'),
            label: l10n.saveLabel,
            isLoading: state.detailsSaving,
            onPressed: _canSave && !state.detailsSaving ? _onSave : null,
          ),
        ],
      ),
    );
  }
}

/// Section (b), Freelancer path: base location, service radius, skill
/// tags, and optional years of experience. Save calls
/// [StorefrontController.saveFreelancerDetails] only.
class _FreelancerDetailsSection extends ConsumerStatefulWidget {
  const _FreelancerDetailsSection({required this.profile});

  final domain.FreelancerProfile profile;

  @override
  ConsumerState<_FreelancerDetailsSection> createState() =>
      _FreelancerDetailsSectionState();
}

class _FreelancerDetailsSectionState
    extends ConsumerState<_FreelancerDetailsSection> {
  final _skillController = TextEditingController();
  final _yearsExperienceController = TextEditingController();

  late double? _latitude = widget.profile.baseLatitude;
  late double? _longitude = widget.profile.baseLongitude;
  late double _serviceRadiusMeters = widget.profile.serviceRadiusMeters
      .toDouble();
  late final List<String> _skills = List.of(widget.profile.skills ?? []);

  @override
  void initState() {
    super.initState();
    _yearsExperienceController.text =
        widget.profile.yearsExperience?.toString() ?? '';
  }

  @override
  void dispose() {
    _skillController.dispose();
    _yearsExperienceController.dispose();
    super.dispose();
  }

  bool get _hasLocation => _latitude != null && _longitude != null;

  void _applyPickResult(LocationPickResult result) {
    setState(() {
      _latitude = result.latitude;
      _longitude = result.longitude;
    });
  }

  void _addSkill() {
    final skill = _skillController.text.trim();
    if (skill.isEmpty || _skills.contains(skill)) return;
    setState(() {
      _skills.add(skill);
      _skillController.clear();
    });
  }

  void _removeSkill(String skill) => setState(() => _skills.remove(skill));

  Future<void> _onSave() async {
    if (!_hasLocation) return;
    final yearsText = _yearsExperienceController.text.trim();
    final ok = await ref
        .read(storefrontControllerProvider.notifier)
        .saveFreelancerDetails(
          UpdateFreelancerDetails(
            baseLatitude: _latitude,
            baseLongitude: _longitude,
            serviceRadiusMeters: _serviceRadiusMeters.round(),
            skills: _skills,
            yearsExperience: yearsText.isEmpty ? null : int.tryParse(yearsText),
          ),
        );
    if (!mounted || !ok) return;
    _showSavedSnackBar(context);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(storefrontControllerProvider);

    return _SectionCard(
      title: l10n.freelancerDetailsTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (state.detailsError != null) ...[
            AppErrorMessage(
              message: providerErrorMessage(context, state.detailsError!),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          Text(
            _hasLocation
                ? l10n.locationPinnedLabel(
                    _latitude!.toStringAsFixed(4),
                    _longitude!.toStringAsFixed(4),
                  )
                : l10n.locationNotSetLabel,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          LocationCaptureField(onPicked: _applyPickResult),
          const SizedBox(height: AppSpacing.xl),
          Text(
            l10n.serviceRadiusValueLabel(
              (_serviceRadiusMeters / 1000).toStringAsFixed(1),
            ),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Slider(
            value: _serviceRadiusMeters,
            min: 500,
            max: 50000,
            divisions: 99,
            onChanged: (value) => setState(() => _serviceRadiusMeters = value),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            l10n.skillsFieldLabel,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: AppTextField(
                  label: l10n.addASkillFieldLabel,
                  controller: _skillController,
                  textInputAction: TextInputAction.done,
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              IconButton(
                icon: const Icon(Icons.add_circle_outline),
                onPressed: _skillController.text.trim().isEmpty
                    ? null
                    : _addSkill,
              ),
            ],
          ),
          if (_skills.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                for (final skill in _skills)
                  Chip(
                    label: Text(skill),
                    onDeleted: () => _removeSkill(skill),
                  ),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.lg),
          AppTextField(
            label: l10n.yearsExperienceFieldLabel,
            controller: _yearsExperienceController,
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: AppSpacing.xl),
          PrimaryButton(
            key: const ValueKey('storefront-details-save'),
            label: l10n.saveLabel,
            isLoading: state.detailsSaving,
            onPressed: _hasLocation && !state.detailsSaving ? _onSave : null,
          ),
        ],
      ),
    );
  }
}

/// Section (c): the portfolio manager. Actions persist immediately (see
/// `PortfolioManager`'s own doc) -- no separate Save button here.
class _PortfolioSection extends ConsumerWidget {
  const _PortfolioSection({required this.photos});

  final List<PortfolioPhoto> photos;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return _SectionCard(
      title: l10n.storefrontPortfolioSectionTitle,
      child: PortfolioManager(
        photos: photos,
        onPhotosChanged: (updated) => ref
            .read(storefrontControllerProvider.notifier)
            .setPortfolio(updated),
      ),
    );
  }
}

/// Section (d): weekly availability, via the shared `WeeklyHoursEditor`
/// with the emergency-availability toggle enabled (PRO-002, AC3) -- applies
/// to both Business and Freelancer providers alike, distinct from the
/// Business-only `operating_hours` field in section (b). Save calls
/// [StorefrontController.saveAvailability] only.
class _AvailabilitySection extends ConsumerStatefulWidget {
  const _AvailabilitySection({required this.availability});

  final List<WeekdayAvailability> availability;

  @override
  ConsumerState<_AvailabilitySection> createState() =>
      _AvailabilitySectionState();
}

class _AvailabilitySectionState extends ConsumerState<_AvailabilitySection> {
  late final Map<String, WeeklyHoursDayValue> _hours = _initialHours();

  Map<String, WeeklyHoursDayValue> _initialHours() {
    final byDay = {
      for (final entry in widget.availability) entry.weekday: entry,
    };
    return {
      for (final day in weeklyHoursOrderedDays) day: _dayValueFrom(byDay[day]),
    };
  }

  static WeeklyHoursDayValue _dayValueFrom(WeekdayAvailability? entry) {
    if (entry == null || !entry.isOpen) {
      return WeeklyHoursDayValue(
        isOpen: false,
        openTime: const TimeOfDay(hour: 9, minute: 0),
        closeTime: const TimeOfDay(hour: 18, minute: 0),
        isEmergencyAvailable: entry?.isEmergencyAvailable ?? false,
      );
    }
    return WeeklyHoursDayValue(
      isOpen: true,
      openTime: parseTimeOfDay(entry.openTime!),
      closeTime: parseTimeOfDay(entry.closeTime!),
      isEmergencyAvailable: entry.isEmergencyAvailable,
    );
  }

  Future<void> _onSave() async {
    final entries = [
      for (final day in weeklyHoursOrderedDays)
        WeekdayAvailability(
          weekday: day,
          isOpen: _hours[day]!.isOpen,
          openTime: _hours[day]!.isOpen
              ? formatTimeOfDay(_hours[day]!.openTime!)
              : null,
          closeTime: _hours[day]!.isOpen
              ? formatTimeOfDay(_hours[day]!.closeTime!)
              : null,
          isEmergencyAvailable: _hours[day]!.isEmergencyAvailable,
        ),
    ];
    final ok = await ref
        .read(storefrontControllerProvider.notifier)
        .saveAvailability(entries);
    if (!mounted || !ok) return;
    _showSavedSnackBar(context);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(storefrontControllerProvider);

    return _SectionCard(
      title: l10n.storefrontAvailabilitySectionTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (state.availabilityError != null) ...[
            AppErrorMessage(
              message: providerErrorMessage(context, state.availabilityError!),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          WeeklyHoursEditor(
            values: _hours,
            showEmergencyToggle: true,
            onChanged: (day, value) => setState(() => _hours[day] = value),
          ),
          const SizedBox(height: AppSpacing.lg),
          PrimaryButton(
            key: const ValueKey('storefront-availability-save'),
            label: l10n.saveLabel,
            isLoading: state.availabilitySaving,
            onPressed: state.availabilitySaving ? null : _onSave,
          ),
        ],
      ),
    );
  }
}
