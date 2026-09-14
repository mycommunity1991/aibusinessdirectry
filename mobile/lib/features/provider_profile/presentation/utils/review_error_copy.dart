import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/review_exception.dart';

/// Renders a [ReviewException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `outcome_tag_error_copy.dart`'s pattern, but -- unlike that pattern --
/// [WriteReviewScreen] shows this same generic message inline for *every*
/// [ReviewErrorType], including [notFound]/[anchorNotVerified]/
/// [alreadyExists]: a full-screen form the customer just filled in
/// deserves explicit feedback rather than [OutcomeTagPromptSheet]'s
/// quiet-close treatment, even though these three are effectively-unreachable
/// edge cases in the normal flow (AC6's own guard already means this screen
/// is never reached without a real `hired=true` submission).
String reviewErrorMessage(BuildContext context, ReviewException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ReviewErrorType.network => l10n.networkErrorMessage,
    ReviewErrorType.notFound => l10n.genericErrorMessage,
    ReviewErrorType.anchorNotVerified => l10n.genericErrorMessage,
    ReviewErrorType.alreadyExists => l10n.genericErrorMessage,
    ReviewErrorType.unknown => l10n.genericErrorMessage,
  };
}
