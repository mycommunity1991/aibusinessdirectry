/// One weekday's availability -- mirrors the backend's
/// `WeekdayAvailabilityResponse`/`WeekdayAvailabilityInput`
/// (`backend/app/modules/provider/schemas.py`, PRO-002, AC3). `GET
/// /providers/me/availability` always returns exactly 7 of these, one per
/// weekday (Decision 3, `Plan_S04_PRO-002.md`).
///
/// [weekday] is the lowercase wire value the backend's `Weekday` enum
/// expects/returns (e.g. `"monday"`) -- matches
/// `shared/widgets/weekly_hours_editor.dart`'s `weeklyHoursOrderedDays`
/// keys exactly, so no enum-to-string conversion is needed at the call
/// site.
class WeekdayAvailability {
  const WeekdayAvailability({
    required this.weekday,
    required this.isOpen,
    this.openTime,
    this.closeTime,
    this.isEmergencyAvailable = false,
  });

  factory WeekdayAvailability.fromJson(Map<String, dynamic> json) {
    return WeekdayAvailability(
      weekday: json['weekday'] as String,
      isOpen: json['is_open'] as bool,
      openTime: json['open_time'] as String?,
      closeTime: json['close_time'] as String?,
      isEmergencyAvailable: json['is_emergency_available'] as bool,
    );
  }

  final String weekday;
  final bool isOpen;

  /// 24-hour "HH:MM"; `null` when [isOpen] is `false`.
  final String? openTime;
  final String? closeTime;

  /// A separate urgent/emergency-availability flag, independent of
  /// [isOpen] (PRO-002, AC3).
  final bool isEmergencyAvailable;

  Map<String, dynamic> toJson() {
    return {
      'weekday': weekday,
      'is_open': isOpen,
      'open_time': openTime,
      'close_time': closeTime,
      'is_emergency_available': isEmergencyAvailable,
    };
  }
}
