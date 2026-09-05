import 'dart:io';

/// The signing-in device's platform + a best-effort human-readable name
/// (AUTH-003, AC6), sent on every login-shaped request
/// (`verify-otp`/`google`/`apple`) so the backend can record/update a
/// `Device` row (`DeviceContext` — `backend/app/modules/identity/schemas.py`).
///
/// Derived from `dart:io Platform` only — no new package is added for this
/// (`device_info_plus` or similar is deliberately not used, Plan Decision 13).
class DeviceContext {
  const DeviceContext({required this.devicePlatform, this.deviceName});

  /// Builds the current device's context. The backend's `DevicePlatform`
  /// enum only has `ios`/`android` — anything that isn't iOS is reported
  /// as `android`, which covers every real Flutter mobile target.
  factory DeviceContext.current() {
    return DeviceContext(
      devicePlatform: Platform.isIOS ? 'ios' : 'android',
      deviceName: _bestEffortDeviceName(),
    );
  }

  /// `"ios"` or `"android"` — matches the backend's `DevicePlatform` enum
  /// values exactly.
  final String devicePlatform;

  /// A best-effort, human-readable device label, e.g. `"iOS 17.4"`. `null`
  /// if it can't be determined — the backend's `device_name` is optional
  /// for exactly this reason.
  final String? deviceName;

  static String? _bestEffortDeviceName() {
    try {
      final platformName = Platform.isIOS ? 'iOS' : 'Android';
      return '$platformName ${Platform.operatingSystemVersion}';
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic> toJson() => {
    'device_platform': devicePlatform,
    'device_name': deviceName,
  };
}
