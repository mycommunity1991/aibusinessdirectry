import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/location_picker/location_error_copy.dart';
import '../../../../shared/widgets/location_picker/location_pick_result.dart';
import '../../../../shared/widgets/location_picker/location_picker_screen.dart';
import '../../../../shared/widgets/location_picker/location_service.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/address_form_mode.dart';
import '../../domain/models/saved_address.dart';
import '../../state/address_form_controller.dart';
import '../utils/saved_address_error_copy.dart';

export '../../domain/models/address_form_mode.dart' show AddressFormMode;

/// The single, shared Add/Edit Address screen (`Plan_S03_CUS-002.md`
/// Decision 7) used for all three entry points:
///  - S-05, the skippable first-address prompt at registration
///    (`skippable: true`, wrapped by `AddFirstAddressScreen`),
///  - S-12, Saved Addresses add/edit (`skippable: false`),
///  - the AC5 re-prompt from Home's temporary "Find a Service" stub
///    (`skippable: false`, non-empty [subtitle]).
///
/// `latitude`/`longitude` are never a raw numeric text input — Save stays
/// disabled until the user has set a location via "Pick on map" or "Use
/// current location" at least once, matching the database's `NOT NULL`
/// requirement (AC3).
class AddressFormScreen extends ConsumerStatefulWidget {
  const AddressFormScreen({
    super.key,
    required this.mode,
    this.skippable = false,
    this.existingAddress,
    this.titleOverride,
    this.subtitle,
    this.showDefaultToggle = true,
    this.forcedIsDefault = false,
  }) : assert(
         mode != AddressFormMode.edit || existingAddress != null,
         'edit mode requires existingAddress',
       );

  final AddressFormMode mode;

  /// Whether a "Skip" link is shown (S-05 only, AC4) — skipping navigates
  /// straight to Home with no repository call.
  final bool skippable;

  /// Required, and used to prefill every field, when [mode] is
  /// [AddressFormMode.edit].
  final SavedAddress? existingAddress;

  /// Overrides the default mode-based title (e.g. S-05's "Add your first
  /// address" instead of the generic "Add address").
  final String? titleOverride;

  /// Optional contextual copy shown under the title (e.g. S-05's
  /// reassurance that skipping is safe, or the AC5 re-prompt's "Add an
  /// address to search for services near you").
  final String? subtitle;

  /// Whether the "Set as default address" switch is shown at all. `false`
  /// for S-05's first-address prompt, where the address is necessarily the
  /// customer's first and is always saved as default without asking
  /// (`Plan_S03_CUS-002.md` item 21) — see [forcedIsDefault].
  final bool showDefaultToggle;

  /// The `is_default` value used when [showDefaultToggle] is `false`.
  /// Ignored otherwise (the on-screen switch's value is used instead).
  final bool forcedIsDefault;

  @override
  ConsumerState<AddressFormScreen> createState() => _AddressFormScreenState();
}

class _AddressFormScreenState extends ConsumerState<AddressFormScreen> {
  final _labelController = TextEditingController();
  final _addressLineController = TextEditingController();
  final _cityController = TextEditingController();
  final _regionController = TextEditingController();
  final _countryCodeController = TextEditingController();

  double? _latitude;
  double? _longitude;
  bool _isDefault = false;
  bool _isLocating = false;
  LocationServiceException? _locationError;

  @override
  void initState() {
    super.initState();
    final existing = widget.existingAddress;
    if (existing != null) {
      _labelController.text = existing.label ?? '';
      _addressLineController.text = existing.addressLine;
      _cityController.text = existing.city ?? '';
      _regionController.text = existing.region ?? '';
      _countryCodeController.text = existing.countryCode;
      _latitude = existing.latitude;
      _longitude = existing.longitude;
      _isDefault = existing.isDefault;
    } else {
      _isDefault = widget.forcedIsDefault;
    }
  }

  @override
  void dispose() {
    _labelController.dispose();
    _addressLineController.dispose();
    _cityController.dispose();
    _regionController.dispose();
    _countryCodeController.dispose();
    super.dispose();
  }

  bool get _hasLocation => _latitude != null && _longitude != null;

  bool get _canSave =>
      _addressLineController.text.trim().isNotEmpty &&
      _countryCodeController.text.trim().length == 2 &&
      _hasLocation;

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

  Future<void> _pickOnMap() async {
    final result = await Navigator.of(context).push<LocationPickResult>(
      MaterialPageRoute(builder: (_) => const LocationPickerScreen()),
    );
    if (result != null && mounted) {
      _applyPickResult(result);
    }
  }

  Future<void> _useCurrentLocation() async {
    setState(() {
      _isLocating = true;
      _locationError = null;
    });
    try {
      final locationService = ref.read(locationServiceProvider);
      final fix = await locationService.getCurrentLocation();
      final reverseGeocoded = await locationService.reverseGeocode(
        latitude: fix.latitude,
        longitude: fix.longitude,
      );
      if (!mounted) return;
      setState(() => _isLocating = false);
      _applyPickResult(
        reverseGeocoded ??
            LocationPickResult(
              latitude: fix.latitude,
              longitude: fix.longitude,
            ),
      );
    } on LocationServiceException catch (error) {
      if (!mounted) return;
      setState(() {
        _isLocating = false;
        _locationError = error;
      });
    }
  }

  Future<void> _onSave() async {
    if (!_canSave) return;
    final controller = ref.read(addressFormControllerProvider.notifier);
    final label = _labelController.text.trim();
    final city = _cityController.text.trim();
    final region = _regionController.text.trim();
    final effectiveIsDefault = widget.showDefaultToggle
        ? _isDefault
        : widget.forcedIsDefault;

    final SavedAddress? saved;
    if (widget.mode == AddressFormMode.edit) {
      saved = await controller.update(
        widget.existingAddress!.id,
        label: label.isEmpty ? null : label,
        addressLine: _addressLineController.text.trim(),
        city: city.isEmpty ? null : city,
        region: region.isEmpty ? null : region,
        countryCode: _countryCodeController.text.trim().toUpperCase(),
        latitude: _latitude!,
        longitude: _longitude!,
        isDefault: effectiveIsDefault,
      );
    } else {
      saved = await controller.create(
        label: label.isEmpty ? null : label,
        addressLine: _addressLineController.text.trim(),
        city: city.isEmpty ? null : city,
        region: region.isEmpty ? null : region,
        countryCode: _countryCodeController.text.trim().toUpperCase(),
        latitude: _latitude!,
        longitude: _longitude!,
        isDefault: effectiveIsDefault,
      );
    }

    if (!mounted || saved == null) return;
    _closeAfterSuccess();
  }

  void _closeAfterSuccess() {
    if (widget.skippable) {
      // Reached via `context.go` during registration, replacing the stack
      // — there is nothing to pop back to (AC4).
      context.go(AppRoutes.homePlaceholder);
    } else {
      context.pop(true);
    }
  }

  void _onSkip() {
    // Skipping never calls the repository — registration/session is already
    // fully complete by the time this screen renders (AC4).
    context.go(AppRoutes.homePlaceholder);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final formState = ref.watch(addressFormControllerProvider);
    final title =
        widget.titleOverride ??
        (widget.mode == AddressFormMode.edit
            ? l10n.addressFormEditTitle
            : l10n.addressFormAddTitle);

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          if (widget.skippable)
            TextButton(onPressed: _onSkip, child: Text(l10n.skipLabel)),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.subtitle != null) ...[
                Text(
                  widget.subtitle!,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: AppSpacing.lg),
              ],
              if (formState.error != null) ...[
                AppErrorMessage(
                  message: savedAddressErrorMessage(context, formState.error!),
                ),
                const SizedBox(height: AppSpacing.md),
              ],
              AppTextField(
                label: l10n.addressLabelFieldLabel,
                controller: _labelController,
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.addressLineFieldLabel,
                controller: _addressLineController,
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.addressCityFieldLabel,
                controller: _cityController,
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.addressRegionFieldLabel,
                controller: _regionController,
                onChanged: (_) => setState(() {}),
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
              const SizedBox(height: AppSpacing.lg),
              if (_locationError != null) ...[
                AppErrorMessage(
                  message: locationServiceErrorMessage(
                    context,
                    _locationError!,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
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
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _pickOnMap,
                      child: Text(l10n.pickOnMapLabel),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _isLocating ? null : _useCurrentLocation,
                      child: _isLocating
                          ? LoadingIndicator(size: 18, label: l10n.loadingLabel)
                          : Text(l10n.useCurrentLocationLabel),
                    ),
                  ),
                ],
              ),
              if (!_hasLocation) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  l10n.addressFormLocationRequiredHint,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (widget.showDefaultToggle) ...[
                const SizedBox(height: AppSpacing.lg),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.setAsDefaultLabel),
                  value: _isDefault,
                  onChanged: (value) => setState(() => _isDefault = value),
                ),
              ],
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                label: l10n.saveLabel,
                isLoading: formState.isSaving,
                onPressed: _canSave && !formState.isSaving ? _onSave : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
