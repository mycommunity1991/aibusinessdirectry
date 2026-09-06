import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/customer_profile_exception.dart';

/// Renders a [CustomerProfileException] as a plain-language, localized
/// string — never the backend's raw message, a status code, or an
/// internal identifier (`docs/AI/06_SECURITY.md`).
///
/// Reuses the same generic copy `features/auth` already ships
/// (`networkErrorMessage`/`genericErrorMessage`) rather than duplicating
/// near-identical strings for a second feature.
String customerProfileErrorMessage(
  BuildContext context,
  CustomerProfileException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    CustomerProfileErrorType.network => l10n.networkErrorMessage,
    CustomerProfileErrorType.unknown => l10n.genericErrorMessage,
  };
}
