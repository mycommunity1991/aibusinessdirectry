import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/provider_exception.dart';

/// Renders a [ProviderException] as a plain-language, localized string —
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `saved_address_error_copy.dart`'s pattern, including a specific message
/// for the "you already have a listing" 409 case (AC8/AC10).
String providerErrorMessage(BuildContext context, ProviderException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ProviderErrorType.network => l10n.networkErrorMessage,
    ProviderErrorType.alreadyExists => l10n.providerAlreadyExistsMessage,
    ProviderErrorType.unknown => l10n.genericErrorMessage,
  };
}
