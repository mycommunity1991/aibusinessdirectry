import 'package:flutter/material.dart';

/// The single, reusable loading indicator used across every async
/// operation — per `docs/AI/07_UI_GUIDELINES.md` ("duplicate UI components
/// are prohibited") and the loading-state rules ("never freeze the
/// interface").
class LoadingIndicator extends StatelessWidget {
  const LoadingIndicator({super.key, this.size = 32, this.label, this.color});

  final double size;

  /// Screen-reader label — every icon/spinner-only control needs one
  /// (`docs/AI/16_UX_GUIDELINES.md` — Accessibility).
  final String? label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: SizedBox(
        height: size,
        width: size,
        child: CircularProgressIndicator(
          strokeWidth: 3,
          color: color ?? Theme.of(context).colorScheme.primary,
        ),
      ),
    );
  }
}
