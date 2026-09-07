import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../app_error_message.dart';
import '../loading_indicator.dart';
import '../primary_button.dart';
import 'location_error_copy.dart';
import 'location_pick_result.dart';
import 'location_service.dart';

/// A generic, reusable "map-pin + current-location" picker
/// (`Plan_S03_CUS-002.md` Decision 7, item 13). Deliberately has no
/// Customer-domain imports/knowledge so a future Provider-domain business/
/// freelancer location screen (S-18a/b, not this story) can reuse it as-is.
///
/// Full-screen map with a fixed center pin (per AC3): panning the map moves
/// the pin implicitly by moving the map under it, exactly like every
/// standard "drop a pin" picker. "Use current location" recentres on the
/// device's current position. "Confirm this location" reverse-geocodes the
/// current center and pops with a [LocationPickResult] — `null` if the user
/// backs out without confirming.
///
/// [mapViewBuilder] defaults to a real [GoogleMap] and exists purely so
/// widget tests can substitute a plain, non-platform-view widget instead —
/// `google_maps_flutter`'s real map is a platform view backed by native
/// method channels that cannot run inside `flutter_test`
/// (`Plan_S03_CUS-002.md`: "no real GoogleMap/geolocator/geocoding platform
/// channel calls in tests").
class LocationPickerScreen extends ConsumerStatefulWidget {
  const LocationPickerScreen({
    super.key,
    this.initialCenter = _defaultInitialCenter,
    this.mapViewBuilder = _defaultMapViewBuilder,
  });

  /// The map's starting center before the user pans or uses current
  /// location — a UAE-first default (Dubai), fully overridable by callers
  /// targeting another country (`docs/AI/04_DATABASE.md`'s "kept generic,
  /// not UAE-specific" note applies to this default too).
  static const LatLng _defaultInitialCenter = LatLng(25.2048, 55.2708);

  final LatLng initialCenter;
  final LocationMapViewBuilder mapViewBuilder;

  static Widget _defaultMapViewBuilder(
    BuildContext context, {
    required LatLng center,
    required ValueChanged<LatLng> onCenterChanged,
    required ValueChanged<GoogleMapController> onMapCreated,
  }) {
    return GoogleMap(
      initialCameraPosition: CameraPosition(target: center, zoom: 16),
      onMapCreated: onMapCreated,
      onCameraMove: (position) => onCenterChanged(position.target),
      myLocationButtonEnabled: false,
      zoomControlsEnabled: false,
    );
  }

  @override
  ConsumerState<LocationPickerScreen> createState() =>
      _LocationPickerScreenState();
}

/// Builds the widget that renders the actual interactive map — see
/// [LocationPickerScreen.mapViewBuilder]'s doc for why this is injectable.
typedef LocationMapViewBuilder =
    Widget Function(
      BuildContext context, {
      required LatLng center,
      required ValueChanged<LatLng> onCenterChanged,
      required ValueChanged<GoogleMapController> onMapCreated,
    });

class _LocationPickerScreenState extends ConsumerState<LocationPickerScreen> {
  late LatLng _center;
  GoogleMapController? _mapController;
  bool _isLocating = false;
  bool _isConfirming = false;
  LocationServiceException? _error;

  @override
  void initState() {
    super.initState();
    _center = widget.initialCenter;
  }

  Future<void> _useCurrentLocation() async {
    setState(() {
      _isLocating = true;
      _error = null;
    });
    try {
      final fix = await ref.read(locationServiceProvider).getCurrentLocation();
      final newCenter = LatLng(fix.latitude, fix.longitude);
      setState(() {
        _center = newCenter;
        _isLocating = false;
      });
      await _mapController?.animateCamera(CameraUpdate.newLatLng(newCenter));
    } on LocationServiceException catch (error) {
      setState(() {
        _isLocating = false;
        _error = error;
      });
    }
  }

  Future<void> _confirm() async {
    setState(() => _isConfirming = true);
    final reverseGeocoded = await ref
        .read(locationServiceProvider)
        .reverseGeocode(
          latitude: _center.latitude,
          longitude: _center.longitude,
        );
    if (!mounted) return;
    final result =
        reverseGeocoded ??
        LocationPickResult(
          latitude: _center.latitude,
          longitude: _center.longitude,
        );
    Navigator.of(context).pop(result);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.locationPickerTitle)),
      body: Stack(
        children: [
          Positioned.fill(
            child: widget.mapViewBuilder(
              context,
              center: _center,
              onCenterChanged: (center) => setState(() => _center = center),
              onMapCreated: (controller) => _mapController = controller,
            ),
          ),
          // A fixed center pin -- decorative only, always exactly screen
          // center (AC3's "map-pin selection"); the map itself moves under
          // it as the user pans.
          IgnorePointer(
            child: Center(
              child: Icon(
                Icons.location_pin,
                size: 48,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
          Positioned(
            left: AppSpacing.md,
            right: AppSpacing.md,
            bottom: AppSpacing.md,
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_error != null) ...[
                    AppErrorMessage(
                      message: locationServiceErrorMessage(context, _error!),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                  ],
                  OutlinedButton.icon(
                    onPressed: _isLocating ? null : _useCurrentLocation,
                    icon: _isLocating
                        ? LoadingIndicator(size: 18, label: l10n.loadingLabel)
                        : const Icon(Icons.my_location),
                    label: Text(l10n.useCurrentLocationLabel),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  PrimaryButton(
                    label: l10n.confirmLocationLabel,
                    isLoading: _isConfirming,
                    onPressed: _isConfirming ? null : _confirm,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
