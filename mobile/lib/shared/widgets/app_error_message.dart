import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';

/// The single, reusable inline error-state banner — per
/// `docs/AI/07_UI_GUIDELINES.md` ("duplicate UI components are
/// prohibited") and `docs/AI/16_UX_GUIDELINES.md`'s error-message formula:
/// always plain-language, never a stack trace, HTTP status code, or
/// internal identifier.
class AppErrorMessage extends StatelessWidget {
  const AppErrorMessage({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(AppRadius.small),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.error_outline,
            color: colorScheme.onErrorContainer,
            size: 20,
          ),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: colorScheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
