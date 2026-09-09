import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/claim_exception.dart';

/// Renders a [ClaimException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `search_error_copy.dart`/`provider_error_copy.dart`'s pattern.
String claimErrorMessage(BuildContext context, ClaimException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ClaimErrorType.network => l10n.networkErrorMessage,
    ClaimErrorType.targetNotFound => l10n.claimTargetNotFoundMessage,
    ClaimErrorType.publicNumberUnavailable =>
      l10n.claimPublicNumberUnavailableMessage,
    ClaimErrorType.invalidCode => l10n.claimInvalidCodeMessage,
    ClaimErrorType.alreadyClaimed => l10n.claimAlreadyClaimedMessage,
    ClaimErrorType.tooManyAttempts => l10n.claimTooManyAttemptsMessage,
    ClaimErrorType.unknown => l10n.genericErrorMessage,
  };
}
