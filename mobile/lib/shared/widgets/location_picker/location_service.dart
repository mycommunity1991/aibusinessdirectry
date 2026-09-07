import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geocoding/geocoding.dart' as geocoding;
import 'package:geolocator/geolocator.dart';

import 'location_pick_result.dart';

/// The category of failure behind a [LocationServiceException].
enum LocationServiceErrorType {
  /// The user denied the location permission (once or permanently).
  permissionDenied,

  /// The device's location services (GPS) are turned off entirely.
  serviceDisabled,

  /// Anything else (a plugin/platform failure fetching a fix).
  unknown,
}

/// A plain-language "use current location" failure. Never a raw plugin
/// exception — mirrors every other repository/service exception in this
/// codebase (`docs/AI/06_SECURITY.md`).
class LocationServiceException implements Exception {
  const LocationServiceException({required this.type});

  final LocationServiceErrorType type;

  @override
  String toString() => 'LocationServiceException(type: $type)';
}

/// A single device-position fix.
class LocationFix {
  const LocationFix({required this.latitude, required this.longitude});

  final double latitude;
  final double longitude;
}

/// Abstracts device geolocation ("use current location") and
/// reverse-geocoding (coordinates → address components) behind one
/// interface, so [LocationPickerScreen] and any widget test can depend on
/// it without ever invoking the real `geolocator`/`geocoding` platform
/// channels (`Plan_S03_CUS-002.md`: "fakes/mocks at the repository layer",
/// mirroring how `google_sign_in`/`sign_in_with_apple` are faked via
/// `AuthRepository`).
abstract class LocationService {
  /// Requests the device's current position, handling the permission
  /// request inline. Throws a [LocationServiceException] if permission is
  /// denied or location services are off.
  Future<LocationFix> getCurrentLocation();

  /// Best-effort reverse geocode of [latitude]/[longitude] into address
  /// components. Returns `null` if nothing was found — never throws, since
  /// this is only ever a convenience prefill, never a blocking step
  /// (`Plan_S03_CUS-002.md` Decision 7: fields stay user-editable either
  /// way).
  Future<LocationPickResult?> reverseGeocode({
    required double latitude,
    required double longitude,
  });
}

/// The real, device-backed [LocationService] — wraps `geolocator` and
/// `geocoding` directly. Used everywhere except widget tests.
class DeviceLocationService implements LocationService {
  const DeviceLocationService();

  @override
  Future<LocationFix> getCurrentLocation() async {
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw const LocationServiceException(
        type: LocationServiceErrorType.permissionDenied,
      );
    }

    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LocationServiceException(
        type: LocationServiceErrorType.serviceDisabled,
      );
    }

    try {
      final position = await Geolocator.getCurrentPosition();
      return LocationFix(
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } on LocationServiceException {
      rethrow;
    } catch (_) {
      throw const LocationServiceException(
        type: LocationServiceErrorType.unknown,
      );
    }
  }

  @override
  Future<LocationPickResult?> reverseGeocode({
    required double latitude,
    required double longitude,
  }) async {
    try {
      final placemarks = await geocoding.placemarkFromCoordinates(
        latitude,
        longitude,
      );
      if (placemarks.isEmpty) {
        return null;
      }
      final placemark = placemarks.first;
      final streetParts = [
        placemark.street,
        placemark.subLocality,
      ].where((part) => part != null && part.isNotEmpty).join(', ');
      return LocationPickResult(
        latitude: latitude,
        longitude: longitude,
        addressLine: streetParts.isEmpty ? null : streetParts,
        city: placemark.locality?.isEmpty ?? true ? null : placemark.locality,
        region: placemark.administrativeArea?.isEmpty ?? true
            ? null
            : placemark.administrativeArea,
        countryCode: placemark.isoCountryCode,
      );
    } catch (_) {
      // Reverse geocoding is a best-effort convenience prefill only -- a
      // native geocoder failure must never block Save (Decision 7).
      return null;
    }
  }
}

final locationServiceProvider = Provider<LocationService>(
  (ref) => const DeviceLocationService(),
);
