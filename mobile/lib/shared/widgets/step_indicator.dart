import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';
import '../../l10n/generated/app_localizations.dart';

/// A generic, reusable step indicator for multi-step forms/wizards —
/// this codebase's first (`Plan_S04_PRO-001.md` item 21, AC9's "step
/// indicator visible across the multi-step form"). Deliberately has no
/// domain coupling — any future multi-step flow can reuse it as-is, per
/// `docs/AI/07_UI_GUIDELINES.md`'s "duplicate UI components are
/// prohibited" rule.
///
/// Renders [totalSteps] equal-width segments; the first [currentStep]
/// segments (1-indexed, inclusive) are drawn in the theme's primary color,
/// the remainder in a muted surface tone. [stepLabels], when supplied, must
/// have exactly one entry per step — the current step's label is shown
/// below the segments.
class StepIndicator extends StatelessWidget {
  const StepIndicator({
    super.key,
    required this.currentStep,
    required this.totalSteps,
    this.stepLabels,
  }) : assert(totalSteps > 0, 'totalSteps must be positive'),
       assert(
         currentStep >= 1 && currentStep <= totalSteps,
         'currentStep must be between 1 and totalSteps, inclusive',
       );

  // Note: `stepLabels.length == totalSteps` is intentionally not asserted
  // here -- `List.length` isn't a const-evaluable expression, which would
  // break every `const StepIndicator(...)` call site. A mismatched
  // `stepLabels` surfaces immediately as a `RangeError` at `build()` time
  // instead (see `stepLabels![currentStep - 1]` below).

  /// 1-indexed — the first step is `1`, not `0`.
  final int currentStep;

  final int totalSteps;

  /// Optional per-step labels (e.g. "Type", "Basic info", "Details").
  final List<String>? stepLabels;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final l10n = AppLocalizations.of(context);

    return Semantics(
      label: l10n.stepIndicatorSemanticLabel(currentStep, totalSteps),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              for (var step = 1; step <= totalSteps; step++) ...[
                if (step > 1) const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: Container(
                    key: ValueKey('step-indicator-segment-$step'),
                    height: 4,
                    decoration: BoxDecoration(
                      color: step <= currentStep
                          ? colorScheme.primary
                          : colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (stepLabels != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              stepLabels![currentStep - 1],
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
