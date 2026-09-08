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
import '../../domain/models/provider.dart' show OperatingHoursEntry;
import '../../state/provider_onboarding_controller.dart';
import '../utils/provider_error_copy.dart';

/// Lowercase weekday keys matching the backend's `operating_hours` JSONB
/// shape (`backend/app/modules/provider/schemas.py`, AC5).
const List<String> _weekdays = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

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

  final Map<String, bool> _isOpenDay = {
    for (final day in _weekdays) day: false,
  };
  final Map<String, TimeOfDay> _openTimes = {
    for (final day in _weekdays) day: const TimeOfDay(hour: 9, minute: 0),
  };
  final Map<String, TimeOfDay> _closeTimes = {
    for (final day in _weekdays) day: const TimeOfDay(hour: 18, minute: 0),
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

  Future<void> _pickTime(String day, {required bool isOpenTime}) async {
    final initial = isOpenTime ? _openTimes[day]! : _closeTimes[day]!;
    final picked = await showTimePicker(context: context, initialTime: initial);
    if (picked == null || !mounted) return;
    setState(() {
      if (isOpenTime) {
        _openTimes[day] = picked;
      } else {
        _closeTimes[day] = picked;
      }
    });
  }

  /// Builds the request's operating-hours map, or `null` if the user never
  /// toggled any day open — the whole field is optional (AC5), so a wizard
  /// pass that never touches it must not send an all-closed dict.
  Map<String, OperatingHoursEntry?>? _buildOperatingHours() {
    if (_isOpenDay.values.every((isOpen) => !isOpen)) {
      return null;
    }
    return {
      for (final day in _weekdays)
        day: _isOpenDay[day]!
            ? OperatingHoursEntry(
                open: _formatTime(_openTimes[day]!),
                close: _formatTime(_closeTimes[day]!),
              )
            : null,
    };
  }

  String _formatTime(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
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
              for (final day in _weekdays)
                _OperatingHoursRow(
                  dayLabel: _weekdayLabel(l10n, day),
                  isOpen: _isOpenDay[day]!,
                  openTime: _openTimes[day]!,
                  closeTime: _closeTimes[day]!,
                  onOpenChanged: (value) =>
                      setState(() => _isOpenDay[day] = value),
                  onTapOpenTime: () => _pickTime(day, isOpenTime: true),
                  onTapCloseTime: () => _pickTime(day, isOpenTime: false),
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

  String _weekdayLabel(AppLocalizations l10n, String day) {
    return switch (day) {
      'monday' => l10n.weekdayMonday,
      'tuesday' => l10n.weekdayTuesday,
      'wednesday' => l10n.weekdayWednesday,
      'thursday' => l10n.weekdayThursday,
      'friday' => l10n.weekdayFriday,
      'saturday' => l10n.weekdaySaturday,
      _ => l10n.weekdaySunday,
    };
  }
}

/// One weekday row of the operating-hours editor — an open/closed toggle
/// plus, when open, tappable open/close time buttons (AC5).
class _OperatingHoursRow extends StatelessWidget {
  const _OperatingHoursRow({
    required this.dayLabel,
    required this.isOpen,
    required this.openTime,
    required this.closeTime,
    required this.onOpenChanged,
    required this.onTapOpenTime,
    required this.onTapCloseTime,
  });

  final String dayLabel;
  final bool isOpen;
  final TimeOfDay openTime;
  final TimeOfDay closeTime;
  final ValueChanged<bool> onOpenChanged;
  final VoidCallback onTapOpenTime;
  final VoidCallback onTapCloseTime;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          Expanded(flex: 2, child: Text(dayLabel)),
          Switch(value: isOpen, onChanged: onOpenChanged),
          if (isOpen) ...[
            Expanded(
              child: TextButton(
                onPressed: onTapOpenTime,
                child: Text(openTime.format(context)),
              ),
            ),
            const Icon(Icons.arrow_forward, size: 16),
            Expanded(
              child: TextButton(
                onPressed: onTapCloseTime,
                child: Text(closeTime.format(context)),
              ),
            ),
          ] else
            Expanded(
              flex: 2,
              child: Text(
                l10n.closedLabel,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
        ],
      ),
    );
  }
}
