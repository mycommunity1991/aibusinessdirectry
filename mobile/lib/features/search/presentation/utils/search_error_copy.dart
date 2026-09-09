import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/search_exception.dart';

/// Renders a [SearchException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors
/// `provider_error_copy.dart`'s pattern.
String searchErrorMessage(BuildContext context, SearchException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    SearchErrorType.network => l10n.networkErrorMessage,
    SearchErrorType.invalidRadius => l10n.searchInvalidRadiusMessage,
    SearchErrorType.unknown => l10n.genericErrorMessage,
  };
}
