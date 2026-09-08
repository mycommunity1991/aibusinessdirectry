import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/location_picker/location_capture_field.dart';
import '../../../../shared/widgets/location_picker/location_pick_result.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/step_indicator.dart';
import '../../domain/models/create_provider_request.dart';
import '../../state/provider_onboarding_controller.dart';
import '../utils/provider_error_copy.dart';

/// S-18b — Freelancer subtype details (PRO-001, AC6): base location/map
/// pin, a service-radius slider, skill tags, and an optional
/// years-of-experience field. The final wizard step for the Freelancer
/// path — Submit calls `ProviderOnboardingController.submit` directly
/// (Decision 2, `Plan_S04_PRO-001.md`).
class FreelancerDetailsScreen extends ConsumerStatefulWidget {
  const FreelancerDetailsScreen({super.key});

  @override
  ConsumerState<FreelancerDetailsScreen> createState() =>
      _FreelancerDetailsScreenState();
}

class _FreelancerDetailsScreenState
    extends ConsumerState<FreelancerDetailsScreen> {
  final _countryCodeController = TextEditingController();
  final _skillController = TextEditingController();
  final _yearsExperienceController = TextEditingController();

  double? _latitude;
  double? _longitude;
  double _serviceRadiusMeters = 5000;
  final List<String> _skills = [];

  @override
  void initState() {
    super.initState();
    _countryCodeController.addListener(_onChanged);
    _skillController.addListener(_onChanged);
  }

  void _onChanged() => setState(() {});

  @override
  void dispose() {
    _countryCodeController.dispose();
    _skillController.dispose();
    _yearsExperienceController.dispose();
    super.dispose();
  }

  bool get _hasLocation =>
      _latitude != null &&
      _longitude != null &&
      _countryCodeController.text.trim().length == 2;

  bool get _canSubmit => _hasLocation;

  void _applyPickResult(LocationPickResult result) {
    setState(() {
      _latitude = result.latitude;
      _longitude = result.longitude;
      if (result.countryCode != null) {
        _countryCodeController.text = result.countryCode!.toUpperCase();
      }
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

  void _removeSkill(String skill) {
    setState(() => _skills.remove(skill));
  }

  Future<void> _onSubmit() async {
    if (!_canSubmit) return;
    final controller = ref.read(providerOnboardingControllerProvider.notifier);
    final yearsText = _yearsExperienceController.text.trim();

    controller.setFreelancerDetails(
      CreateFreelancerDetails(
        baseLatitude: _latitude!,
        baseLongitude: _longitude!,
        countryCode: _countryCodeController.text.trim().toUpperCase(),
        serviceRadiusMeters: _serviceRadiusMeters.round(),
        skills: _skills.isEmpty ? null : List.of(_skills),
        yearsExperience: yearsText.isEmpty ? null : int.tryParse(yearsText),
      ),
    );

    final provider = await controller.submit();
    if (!mounted || provider == null) return;
    // VER-001, Plan item 30 -- the wizard now lands on Verification
    // Upload (S-19) instead of Home, so a newly-listed provider is
    // guided straight into the trust gate.
    context.go(AppRoutes.verificationUpload);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final onboardingState = ref.watch(providerOnboardingControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.freelancerDetailsTitle)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const StepIndicator(
                currentStep: 3,
                totalSteps: providerWizardTotalSteps,
              ),
              const SizedBox(height: AppSpacing.lg),
              if (onboardingState.error != null) ...[
                AppErrorMessage(
                  message: providerErrorMessage(
                    context,
                    onboardingState.error!,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
              ],
              AppTextField(
                label: l10n.addressCountryCodeFieldLabel,
                hintText: l10n.addressCountryCodeHint,
                controller: _countryCodeController,
                maxLength: 2,
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp('[a-zA-Z]')),
                  TextInputFormatter.withFunction(
                    (oldValue, newValue) =>
                        newValue.copyWith(text: newValue.text.toUpperCase()),
                  ),
                ],
                onChanged: (_) => setState(() {}),
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
              if (!_hasLocation) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  l10n.addressFormLocationRequiredHint,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
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
                onChanged: (value) =>
                    setState(() => _serviceRadiusMeters = value),
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
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                label: l10n.submitLabel,
                isLoading: onboardingState.isSubmitting,
                onPressed: _canSubmit && !onboardingState.isSubmitting
                    ? _onSubmit
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
