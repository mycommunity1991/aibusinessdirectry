import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/verification_exception.dart';

/// Renders a [VerificationException] as a plain-language, localized
/// string -- never the backend's raw message, a status code, or an
/// internal identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `provider_error_copy.dart`'s pattern.
String verificationErrorMessage(
  BuildContext context,
  VerificationException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    VerificationErrorType.network => l10n.networkErrorMessage,
    VerificationErrorType.providerNotFound =>
      l10n.providerListingNotFoundMessage,
    VerificationErrorType.documentTooLarge =>
      l10n.verificationDocumentTooLargeMessage,
    VerificationErrorType.documentInvalidType =>
      l10n.verificationDocumentInvalidTypeMessage,
    VerificationErrorType.documentRequired =>
      l10n.verificationDocumentRequiredMessage,
    VerificationErrorType.submissionNotAllowed =>
      l10n.verificationSubmissionNotAllowedMessage,
    VerificationErrorType.unknown => l10n.genericErrorMessage,
  };
}
