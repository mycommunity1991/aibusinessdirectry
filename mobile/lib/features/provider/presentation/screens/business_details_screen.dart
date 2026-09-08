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
import '../../../../shared/widgets/weekly_hours_editor.dart';
import '../../domain/models/create_provider_request.dart';
import '../../domain/models/provider.dart' show OperatingHoursEntry;
import '../../state/provider_onboarding_controller.dart';
import '../utils/provider_error_copy.dart';

/// S-18a — Business subtype details (PRO-001, AC5): address/map location, a
/// weekly operating-hours editor, an optional delivery radius, and an
/// optional trade license number. The final wizard step for the Business
/// path — Submit calls `ProviderOnboardingController.submit` directly
/// (Decision 2, `Plan_S04_PRO-001.md` — a single end-of-wizard `POST`).
class BusinessDetailsScreen extends ConsumerStatefulWidget {
  const BusinessDetailsScreen({super.key});

  @override
  ConsumerState<BusinessDetailsScreen> createState() =>
      _BusinessDetailsScreenState();
}

class _BusinessDetailsScreenState extends ConsumerState<BusinessDetailsScreen> {
  final _addressLineController = TextEditingController();
  final _cityController = TextEditingController();
  final _regionController = TextEditingController();
  final _countryCodeController = TextEditingController();
  final _tradeLicenseController = TextEditingController();

  double? _latitude;
  double? _longitude;

  bool _offersDelivery = false;
  double _deliveryRadiusMeters = 5000;

  final Map<String, WeeklyHoursDayValue> _hours = {
    for (final day in weeklyHoursOrderedDays)
      day: const WeeklyHoursDayValue(
        isOpen: false,
        openTime: TimeOfDay(hour: 9, minute: 0),
        closeTime: TimeOfDay(hour: 18, minute: 0),
      ),
  };

  @override
  void initState() {
    super.initState();
    _addressLineController.addListener(_onChanged);
    _countryCodeController.addListener(_onChanged);
  }

  void _onChanged() => setState(() {});

  @override
  void dispose() {
    _addressLineController.dispose();
    _cityController.dispose();
    _regionController.dispose();
    _countryCodeController.dispose();
    _tradeLicenseController.dispose();
    super.dispose();
  }

  bool get _hasLocation =>
      _latitude != null &&
      _longitude != null &&
      _countryCodeController.text.trim().length == 2;

  bool get _canSubmit =>
      _addressLineController.text.trim().isNotEmpty && _hasLocation;

  void _applyPickResult(LocationPickResult result) {
    setState(() {
      _latitude = result.latitude;
      _longitude = result.longitude;
      if (result.addressLine != null) {
        _addressLineController.text = result.addressLine!;
      }
      if (result.city != null) {
        _cityController.text = result.city!;
      }
      if (result.region != null) {
        _regionController.text = result.region!;
      }
      if (result.countryCode != null) {
        _countryCodeController.text = result.countryCode!.toUpperCase();
      }
    });
  }

  /// Builds the request's operating-hours map, or `null` if the user never
  /// toggled any day open — the whole field is optional (AC5), so a wizard
  /// pass that never touches it must not send an all-closed dict.
  Map<String, OperatingHoursEntry?>? _buildOperatingHours() {
    if (_hours.values.every((day) => !day.isOpen)) {
      return null;
    }
    return {
      for (final day in weeklyHoursOrderedDays)
        day: _hours[day]!.isOpen
            ? OperatingHoursEntry(
                open: formatTimeOfDay(_hours[day]!.openTime!),
                close: formatTimeOfDay(_hours[day]!.closeTime!),
              )
            : null,
    };
  }

  Future<void> _onSubmit() async {
    if (!_canSubmit) return;
    final controller = ref.read(providerOnboardingControllerProvider.notifier);
    final city = _cityController.text.trim();
    final region = _regionController.text.trim();
    final tradeLicense = _tradeLicenseController.text.trim();

    controller.setBusinessDetails(
      CreateBusinessDetails(
        addressLine: _addressLineController.text.trim(),
        city: city.isEmpty ? null : city,
        region: region.isEmpty ? null : region,
        countryCode: _countryCodeController.text.trim().toUpperCase(),
        latitude: _latitude!,
        longitude: _longitude!,
        operatingHours: _buildOperatingHours(),
        deliveryRadiusMeters: _offersDelivery
            ? _deliveryRadiusMeters.round()
            : null,
        tradeLicenseNumber: tradeLicense.isEmpty ? null : tradeLicense,
      ),
    );

    final provider = await controller.submit();
    if (!mounted || provider == null) return;
    context.go(AppRoutes.homePlaceholder);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final onboardingState = ref.watch(providerOnboardingControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.businessDetailsTitle)),
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
                label: l10n.addressLineFieldLabel,
                controller: _addressLineController,
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
