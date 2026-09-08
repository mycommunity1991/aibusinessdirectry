import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../app_error_message.dart';
import '../loading_indicator.dart';
import 'location_error_copy.dart';
import 'location_pick_result.dart';
import 'location_picker_screen.dart';
import 'location_service.dart';

/// A "Pick on map" + "Use current location" action pair wired to
/// [LocationPickerScreen]/[LocationService] — the single-lat/lng-capture
/// pattern first built by CUS-002's `AddressFormScreen` and reused as-is by
/// PRO-001's `BusinessDetailsScreen`/`FreelancerDetailsScreen`, factored out
/// here to avoid a second/third copy of the same picker-plus-locate wiring
/// (`docs/AI/07_UI_GUIDELINES.md`, "duplicate UI components are
/// prohibited").
///
/// Stateless with respect to the picked location itself — [onPicked] fires
/// with a [LocationPickResult] every time the caller successfully picks or
/// locates; the caller owns displaying the resulting coordinates/derived
/// address fields.
class LocationCaptureField extends ConsumerStatefulWidget {
  const LocationCaptureField({super.key, required this.onPicked});

  final ValueChanged<LocationPickResult> onPicked;

  @override
  ConsumerState<LocationCaptureField> createState() =>
      _LocationCaptureFieldState();
}

class _LocationCaptureFieldState extends ConsumerState<LocationCaptureField> {
  bool _isLocating = false;
  LocationServiceException? _error;

  Future<void> _pickOnMap() async {
    final result = await Navigator.of(context).push<LocationPickResult>(
      MaterialPageRoute(builder: (_) => const LocationPickerScreen()),
    );
    if (result != null && mounted) {
      widget.onPicked(result);
    }
  }

  Future<void> _useCurrentLocation() async {
    setState(() {
      _isLocating = true;
      _error = null;
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
      widget.onPicked(
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
        _error = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_error != null) ...[
          AppErrorMessage(
            message: locationServiceErrorMessage(context, _error!),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
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
      ],
    );
  }
}
