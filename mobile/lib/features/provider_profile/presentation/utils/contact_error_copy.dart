import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/contact_exception.dart';

/// Renders a [ContactException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors `claim_error_copy.dart`'s
/// pattern, including a specific, clear message for the self-dealing
/// rejection (AC3/AC4, Decision 10, `Plan_S08_CON-001.md`).
String contactErrorMessage(BuildContext context, ContactException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ContactErrorType.network => l10n.networkErrorMessage,
    ContactErrorType.selfDealing => l10n.contactSelfDealingMessage,
    ContactErrorType.notFound => l10n.contactProviderNotFoundMessage,
    ContactErrorType.unknown => l10n.genericErrorMessage,
  };
}
