import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/visibility_analytics_exception.dart';

/// Renders a [VisibilityAnalyticsException] as a plain-language, localized
/// string -- never the backend's raw message, a status code, or an
/// internal identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `lead_error_copy.dart`'s pattern. [VisibilityAnalyticsErrorType.notFound]
/// reuses `providerListingNotFoundMessage` -- the exact same underlying
/// condition ("the caller has no Provider listing yet") `lead_error_copy.
/// dart` already renders that copy for, so this deliberately does not
/// introduce a second, near-duplicate string for the same case.
String visibilityAnalyticsErrorMessage(
  BuildContext context,
  VisibilityAnalyticsException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    VisibilityAnalyticsErrorType.network => l10n.networkErrorMessage,
    VisibilityAnalyticsErrorType.notFound =>
      l10n.providerListingNotFoundMessage,
    VisibilityAnalyticsErrorType.unknown => l10n.genericErrorMessage,
  };
}
