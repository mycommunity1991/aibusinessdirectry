import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:ai_marketplace_app/shared/widgets/step_indicator.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _pump(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light(),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(body: child),
    ),
  );
}

Color _segmentColor(WidgetTester tester, int step) {
  final container = tester.widget<Container>(
    find.byKey(ValueKey('step-indicator-segment-$step')),
  );
  final decoration = container.decoration! as BoxDecoration;
  return decoration.color!;
}

void main() {
  group('StepIndicator', () {
    testWidgets('renders exactly totalSteps segments', (tester) async {
      await _pump(tester, const StepIndicator(currentStep: 2, totalSteps: 3));

      for (var step = 1; step <= 3; step++) {
        expect(
          find.byKey(ValueKey('step-indicator-segment-$step')),
          findsOneWidget,
        );
      }
      expect(
        find.byKey(const ValueKey('step-indicator-segment-4')),
        findsNothing,
      );
    });

    testWidgets(
      'segments up to and including currentStep are highlighted, later ones are not',
      (tester) async {
        await _pump(tester, const StepIndicator(currentStep: 2, totalSteps: 3));

        final theme = AppTheme.light();
        final colorScheme = theme.colorScheme;

        expect(_segmentColor(tester, 1), colorScheme.primary);
        expect(_segmentColor(tester, 2), colorScheme.primary);
        expect(_segmentColor(tester, 3), colorScheme.surfaceContainerHighest);
      },
    );

    testWidgets('shows the current step label when stepLabels is provided', (
      tester,
    ) async {
      await _pump(
        tester,
        const StepIndicator(
          currentStep: 2,
          totalSteps: 3,
          stepLabels: ['Type', 'Basic info', 'Details'],
        ),
      );

      expect(find.text('Basic info'), findsOneWidget);
      expect(find.text('Type'), findsNothing);
      expect(find.text('Details'), findsNothing);
    });

    testWidgets('renders no label text when stepLabels is omitted', (
      tester,
    ) async {
      await _pump(tester, const StepIndicator(currentStep: 1, totalSteps: 3));

      expect(find.byType(Text), findsNothing);
    });

    testWidgets('exposes a "Step X of Y" semantic label for screen readers', (
      tester,
    ) async {
      await _pump(tester, const StepIndicator(currentStep: 2, totalSteps: 3));

      expect(find.bySemanticsLabel('Step 2 of 3'), findsOneWidget);
    });
  });
}
