import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/lead_exception.dart';

/// Renders a [LeadException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors `provider_error_copy.
/// dart`'s pattern. [LeadErrorType.notFound] reuses
/// `providerListingNotFoundMessage` -- the exact same underlying condition
/// ("the caller has no Provider listing yet") `provider_error_copy.dart`
/// already renders that copy for, so this deliberately does not introduce
/// a second, near-duplicate string for the same case.
String leadErrorMessage(BuildContext context, LeadException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    LeadErrorType.network => l10n.networkErrorMessage,
    LeadErrorType.notFound => l10n.providerListingNotFoundMessage,
    LeadErrorType.unknown => l10n.genericErrorMessage,
  };
}
