import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/saved_address_exception.dart';

/// Renders a [SavedAddressException] as a plain-language, localized string
/// — never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `customer_error_copy.dart`'s pattern.
String savedAddressErrorMessage(
  BuildContext context,
  SavedAddressException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    SavedAddressErrorType.network => l10n.networkErrorMessage,
    SavedAddressErrorType.notFound => l10n.savedAddressNotFoundMessage,
    SavedAddressErrorType.unknown => l10n.genericErrorMessage,
  };
}
