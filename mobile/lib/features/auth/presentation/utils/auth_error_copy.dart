import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/auth_exception.dart';

/// Resolves an [AuthException] to plain-language, localized copy for
/// display — per `docs/AI/16_UX_GUIDELINES.md`'s error-message formula and
/// AC10 (never a raw status code or internal identifier).
///
/// For [AuthErrorType.invalidCode]/[AuthErrorType.tooManyAttempts], the
/// backend's own message is already crafted to be plain-language and
/// non-revealing (`InvalidOtpError`/`OtpLockedError`), so it's used
/// directly with a localized fallback. Every other failure uses a
/// client-owned, localized message.
String authErrorMessage(BuildContext context, AuthException exception) {
  final l10n = AppLocalizations.of(context);
  switch (exception.type) {
    case AuthErrorType.invalidCode:
    case AuthErrorType.tooManyAttempts:
      return exception.serverMessage ?? l10n.genericErrorMessage;
    case AuthErrorType.network:
      return l10n.networkErrorMessage;
    case AuthErrorType.unknown:
      return l10n.genericErrorMessage;
  }
}
