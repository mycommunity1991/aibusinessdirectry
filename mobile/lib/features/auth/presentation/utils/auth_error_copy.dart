import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/auth_exception.dart';

/// Resolves an [AuthException] to plain-language, localized copy for
/// display — per `docs/AI/16_UX_GUIDELINES.md`'s error-message formula and
/// AC10 (never a raw status code or internal identifier).
///
/// Every failure — including [AuthErrorType.invalidCode]/
/// [AuthErrorType.tooManyAttempts] — resolves to a client-owned, localized
/// string, never the backend's raw English message (FU-3,
/// `Walkthrough_S02_AUTH-001.md`). This keeps Arabic-locale users from ever
/// seeing untranslated English copy, and keeps the client's wording
/// independent of the backend's (which is free to change without a mobile
/// release).
String authErrorMessage(BuildContext context, AuthException exception) {
  final l10n = AppLocalizations.of(context);
  switch (exception.type) {
    case AuthErrorType.invalidCode:
      return l10n.otpInvalidCodeMessage;
    case AuthErrorType.tooManyAttempts:
      return l10n.otpTooManyAttemptsMessage;
    case AuthErrorType.network:
      return l10n.networkErrorMessage;
    case AuthErrorType.unknown:
      return l10n.genericErrorMessage;
  }
}
