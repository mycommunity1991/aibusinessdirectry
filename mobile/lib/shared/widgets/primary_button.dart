import 'package:flutter/material.dart';

/// The single, reusable primary-action button used across every screen —
/// per `docs/AI/07_UI_GUIDELINES.md` ("duplicate UI components are
/// prohibited"), no screen should build its own `FilledButton` for its
/// primary action.
///
/// Shows a loading spinner in place of its label while [isLoading] is
/// true, and disables itself while loading or when [onPressed] is null,
/// per the loading-state rules in `docs/AI/07_UI_GUIDELINES.md`.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return FilledButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: colorScheme.onSecondary,
              ),
            )
          : Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[Icon(icon), const SizedBox(width: 8)],
                Text(label),
              ],
            ),
    );
  }
}
