import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/notification_exception.dart';

/// Renders a [NotificationException] as a plain-language, localized string
/// -- never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors `lead_error_copy.dart`/
/// `visibility_analytics_error_copy.dart`'s pattern.
String notificationErrorMessage(
  BuildContext context,
  NotificationException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    NotificationErrorType.network => l10n.networkErrorMessage,
    NotificationErrorType.unknown => l10n.genericErrorMessage,
  };
}
