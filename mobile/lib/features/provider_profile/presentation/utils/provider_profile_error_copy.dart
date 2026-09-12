import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/provider_profile_exception.dart';

/// Renders a [ProviderProfileException] as a plain-language, localized
/// string -- never the backend's raw message, a status code, or an
/// internal identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `claim_error_copy.dart`/`search_error_copy.dart`'s pattern.
String providerProfileErrorMessage(
  BuildContext context,
  ProviderProfileException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ProviderProfileErrorType.network => l10n.networkErrorMessage,
    ProviderProfileErrorType.notFound => l10n.providerProfileNotFoundMessage,
    ProviderProfileErrorType.unknown => l10n.genericErrorMessage,
  };
}
