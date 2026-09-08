import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/weekly_hours_editor.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Pumps [WeeklyHoursEditor] wrapped in a [StatefulBuilder] so the widget
/// under test is exercised as the fully-controlled component it is —
/// [onValuesChanged] is invoked with the full, updated map after every
/// [WeeklyHoursEditor.onChanged] callback, mirroring how both
/// `BusinessDetailsScreen` and the Storefront's Availability section wire
/// it up in the real app.
Future<void> _pumpEditor(
  WidgetTester tester, {
  required Map<String, WeeklyHoursDayValue> initialValues,
  bool showEmergencyToggle = false,
  required void Function(Map<String, WeeklyHoursDayValue>) onValuesChanged,
}) async {
  var values = initialValues;
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: StatefulBuilder(
          builder: (context, setState) {
            return SingleChildScrollView(
              child: WeeklyHoursEditor(
                values: values,
                showEmergencyToggle: showEmergencyToggle,
                onChanged: (day, value) {
                  setState(() {
                    values = {...values, day: value};
                  });
                  onValuesChanged(values);
                },
              ),
            );
          },
        ),
      ),
    ),
  );
}

void main() {
  group('WeeklyHoursEditor (shared, PRO-001/PRO-002 item 24)', () {
    testWidgets('renders all seven weekdays, closed by default', (
      tester,
    ) async {
      await _pumpEditor(
        tester,
        initialValues: const {},
        onValuesChanged: (_) {},
      );

      expect(find.text('Monday'), findsOneWidget);
      expect(find.text('Tuesday'), findsOneWidget);
      expect(find.text('Wednesday'), findsOneWidget);
      expect(find.text('Thursday'), findsOneWidget);
      expect(find.text('Friday'), findsOneWidget);
      expect(find.text('Saturday'), findsOneWidget);
      expect(find.text('Sunday'), findsOneWidget);
      expect(find.text('Closed'), findsNWidgets(7));
    });

    testWidgets(
      'toggling a day open reveals time buttons and reports the change',
      (tester) async {
        Map<String, WeeklyHoursDayValue>? latest;
        await _pumpEditor(
          tester,
          initialValues: const {},
          onValuesChanged: (v) => latest = v,
        );

        final mondayRow = find.byKey(const ValueKey('weekly-hours-row-monday'));
        final mondaySwitch = find.descendant(
          of: mondayRow,
          matching: find.byType(Switch),
        );
        expect(mondaySwitch, findsOneWidget);

        await tester.tap(mondaySwitch);
        await tester.pump();

        expect(latest, isNotNull);
        expect(latest!['monday']!.isOpen, isTrue);
        expect(
          find.descendant(of: mondayRow, matching: find.byType(TextButton)),
          findsNWidgets(2),
        );
      },
    );

    testWidgets('tapping a time button opens a time picker and reports it', (
      tester,
    ) async {
      Map<String, WeeklyHoursDayValue>? latest;
      await _pumpEditor(
        tester,
        initialValues: const {
          'monday': WeeklyHoursDayValue(
            isOpen: true,
            openTime: TimeOfDay(hour: 9, minute: 0),
            closeTime: TimeOfDay(hour: 18, minute: 0),
          ),
        },
        onValuesChanged: (v) => latest = v,
      );

      final mondayRow = find.byKey(const ValueKey('weekly-hours-row-monday'));
      final openTimeButton = find
          .descendant(of: mondayRow, matching: find.byType(TextButton))
          .first;

      await tester.tap(openTimeButton);
      await tester.pumpAndSettle();

      // Confirm the picker with its default (unchanged) time.
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();

      expect(latest, isNotNull);
      expect(latest!['monday']!.openTime, isNotNull);
    });

    testWidgets('the emergency-availability toggle is hidden by default', (
      tester,
    ) async {
      await _pumpEditor(
        tester,
        initialValues: const {},
        onValuesChanged: (_) {},
      );

      expect(find.text('Available for emergencies'), findsNothing);
    });

    testWidgets('showEmergencyToggle renders a per-weekday emergency switch, '
        'independent of open/closed state', (tester) async {
      Map<String, WeeklyHoursDayValue>? latest;
      await _pumpEditor(
        tester,
        initialValues: const {},
        showEmergencyToggle: true,
        onValuesChanged: (v) => latest = v,
      );

      expect(find.text('Available for emergencies'), findsNWidgets(7));

      final mondayRow = find.byKey(const ValueKey('weekly-hours-row-monday'));
      final switchesInRow = find.descendant(
        of: mondayRow,
        matching: find.byType(Switch),
      );
      // The plain open/closed Switch, plus the emergency SwitchListTile's
      // own internal Switch.
      expect(switchesInRow, findsNWidgets(2));

      await tester.tap(switchesInRow.last);
      await tester.pump();

      expect(latest, isNotNull);
      expect(latest!['monday']!.isEmergencyAvailable, isTrue);
      // Toggling emergency availability never implicitly opens the day.
      expect(latest!['monday']!.isOpen, isFalse);
    });
  });
}
