import 'package:ai_marketplace_app/shared/widgets/location_picker/location_pick_result.dart';
import 'package:ai_marketplace_app/shared/widgets/location_picker/location_service.dart';

/// A hermetic test double for [LocationService] — no real
/// `geolocator`/`geocoding` platform channel is ever invoked. Mirrors
/// `fake_auth_repository.dart`'s pattern for faking a plugin-backed
/// dependency at its repository/service-layer boundary.
class FakeLocationService implements LocationService {
  FakeLocationService({
    LocationFix? currentLocation,
    this.getCurrentLocationError,
    this.reverseGeocodeResult,
  }) : _currentLocation =
           currentLocation ??
           const LocationFix(latitude: 25.2, longitude: 55.3);

  final LocationFix _currentLocation;
  final LocationServiceException? getCurrentLocationError;
  final LocationPickResult? reverseGeocodeResult;

  int getCurrentLocationCallCount = 0;
  int reverseGeocodeCallCount = 0;

  @override
  Future<LocationFix> getCurrentLocation() async {
    getCurrentLocationCallCount++;
    if (getCurrentLocationError != null) {
      throw getCurrentLocationError!;
    }
    return _currentLocation;
  }

  @override
  Future<LocationPickResult?> reverseGeocode({
    required double latitude,
    required double longitude,
  }) async {
    reverseGeocodeCallCount++;
    return reverseGeocodeResult ??
        LocationPickResult(latitude: latitude, longitude: longitude);
  }
}
