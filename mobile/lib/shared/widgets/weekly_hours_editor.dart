import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';
import '../../l10n/generated/app_localizations.dart';

/// Canonical lowercase weekday keys, Monday-first -- matches the backend's
/// `Weekday` enum wire values (`backend/app/modules/provider/models.py`)
/// and this codebase's existing `operating_hours` JSON shape. Both the
/// onboarding wizard's Business Details screen (PRO-001) and the
/// Storefront's Availability section (PRO-002) key their per-day state by
/// these same strings.
const List<String> weeklyHoursOrderedDays = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

/// One weekday's editable hours state -- generic, no domain coupling
/// (mirrors `StepIndicator`'s "no domain coupling" precedent,
/// `Plan_S04_PRO-001.md` item 21). Feature-level code (`BusinessDetails
/// Screen`, `StorefrontScreen`'s availability section) converts to/from its
/// own request/response shapes at the call site.
class WeeklyHoursDayValue {
  const WeeklyHoursDayValue({
    required this.isOpen,
    this.openTime,
    this.closeTime,
    this.isEmergencyAvailable = false,
  });

  final bool isOpen;
  final TimeOfDay? openTime;
  final TimeOfDay? closeTime;

  /// A separate urgent/emergency-availability flag (PRO-002, AC3) --
  /// independent of [isOpen] (a provider may be unavailable for regular
  /// hours on a given day but still reachable for emergencies).
  final bool isEmergencyAvailable;

  WeeklyHoursDayValue copyWith({
    bool? isOpen,
    TimeOfDay? openTime,
    TimeOfDay? closeTime,
    bool? isEmergencyAvailable,
  }) {
    return WeeklyHoursDayValue(
      isOpen: isOpen ?? this.isOpen,
      openTime: openTime ?? this.openTime,
      closeTime: closeTime ?? this.closeTime,
      isEmergencyAvailable: isEmergencyAvailable ?? this.isEmergencyAvailable,
    );
  }
}

/// Formats a [TimeOfDay] as 24-hour "HH:MM" -- the exact wire shape the
/// backend's `operating_hours`/`WeekdayAvailabilityInput` schemas expect.
String formatTimeOfDay(TimeOfDay time) {
  final hour = time.hour.toString().padLeft(2, '0');
  final minute = time.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

/// Parses a 24-hour "HH:MM" wire string into a [TimeOfDay].
TimeOfDay parseTimeOfDay(String value) {
  final parts = value.split(':');
  return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
}

/// The full, localized weekday name for one of [weeklyHoursOrderedDays]'s
/// wire-value keys -- a top-level function (rather than a private method
/// scoped to [WeeklyHoursEditor]) so the Provider Profile screen's
/// read-only hours display (CON-001, AC5) can render the same day labels
/// without duplicating this switch (`docs/AI/08_CODING_STANDARDS.md`,
/// "never create duplicate code").
String weekdayLabel(AppLocalizations l10n, String day) {
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

/// A generic, reusable weekly operating-hours editor -- factored out of
/// PRO-001's `BusinessDetailsScreen` (`_OperatingHoursRow`) so PRO-002's
/// Storefront Availability section can reuse the exact same per-weekday
/// toggle-plus-time-pickers UI instead of a second copy
/// (`docs/AI/08_CODING_STANDARDS.md`, "no duplicate widgets"). Extended
/// here with an optional per-weekday emergency-availability toggle
/// (PRO-002, AC3) that PRO-001's onboarding editor never needed.
///
/// A fully controlled component: renders from [values] and reports every
/// change via [onChanged] -- it holds no state of its own, so the same
/// [values] map driving both the onboarding wizard's in-memory draft and
/// the Storefront's `StorefrontController` state works identically.
class WeeklyHoursEditor extends StatelessWidget {
  const WeeklyHoursEditor({
    super.key,
    required this.values,
    required this.onChanged,
    this.showEmergencyToggle = false,
  });

  /// Keyed by [weeklyHoursOrderedDays]; a day missing from this map is
  /// rendered as closed.
  final Map<String, WeeklyHoursDayValue> values;

  final void Function(String day, WeeklyHoursDayValue value) onChanged;

  /// Shows the per-weekday emergency-availability toggle (PRO-002) --
  /// `false` by default so PRO-001's onboarding usage renders identically
  /// to before this widget was factored out.
  final bool showEmergencyToggle;

  WeeklyHoursDayValue _valueFor(String day) =>
      values[day] ?? const WeeklyHoursDayValue(isOpen: false);

  Future<void> _pickTime(
    BuildContext context,
    String day, {
    required bool isOpenTime,
  }) async {
    final current = _valueFor(day);
    final initial = isOpenTime
        ? (current.openTime ?? const TimeOfDay(hour: 9, minute: 0))
        : (current.closeTime ?? const TimeOfDay(hour: 18, minute: 0));
    final picked = await showTimePicker(context: context, initialTime: initial);
    if (picked == null) return;
    onChanged(
      day,
      isOpenTime
          ? current.copyWith(openTime: picked)
          : current.copyWith(closeTime: picked),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final day in weeklyHoursOrderedDays)
          _WeeklyHoursRow(
            key: ValueKey('weekly-hours-row-$day'),
            dayLabel: weekdayLabel(l10n, day),
            value: _valueFor(day),
            showEmergencyToggle: showEmergencyToggle,
            onOpenChanged: (isOpen) =>
                onChanged(day, _valueFor(day).copyWith(isOpen: isOpen)),
            onTapOpenTime: () => _pickTime(context, day, isOpenTime: true),
            onTapCloseTime: () => _pickTime(context, day, isOpenTime: false),
            onEmergencyChanged: (value) => onChanged(
              day,
              _valueFor(day).copyWith(isEmergencyAvailable: value),
            ),
          ),
      ],
    );
  }
}

/// One weekday row: an open/closed toggle plus, when open, tappable
/// open/close time buttons (AC5/AC3), and -- when
/// [showEmergencyToggle] is set -- a second, indented row with the
/// emergency-availability switch (PRO-002, AC3).
class _WeeklyHoursRow extends StatelessWidget {
  const _WeeklyHoursRow({
    super.key,
    required this.dayLabel,
    required this.value,
    required this.showEmergencyToggle,
    required this.onOpenChanged,
    required this.onTapOpenTime,
    required this.onTapCloseTime,
    required this.onEmergencyChanged,
  });

  final String dayLabel;
  final WeeklyHoursDayValue value;
  final bool showEmergencyToggle;
  final ValueChanged<bool> onOpenChanged;
  final VoidCallback onTapOpenTime;
  final VoidCallback onTapCloseTime;
  final ValueChanged<bool> onEmergencyChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(flex: 2, child: Text(dayLabel)),
              Switch(value: value.isOpen, onChanged: onOpenChanged),
              if (value.isOpen) ...[
                Expanded(
                  child: TextButton(
                    onPressed: onTapOpenTime,
                    child: Text(
                      (value.openTime ?? const TimeOfDay(hour: 9, minute: 0))
                          .format(context),
                    ),
                  ),
                ),
                const Icon(Icons.arrow_forward, size: 16),
                Expanded(
                  child: TextButton(
                    onPressed: onTapCloseTime,
                    child: Text(
                      (value.closeTime ?? const TimeOfDay(hour: 18, minute: 0))
                          .format(context),
                    ),
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
          if (showEmergencyToggle)
            Padding(
              padding: const EdgeInsets.only(left: AppSpacing.md),
              child: SwitchListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(
                  l10n.emergencyAvailableLabel,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                value: value.isEmergencyAvailable,
                onChanged: onEmergencyChanged,
              ),
            ),
        ],
      ),
    );
  }
}
