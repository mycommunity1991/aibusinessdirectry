import 'package:flutter/widgets.dart';

import '../../../l10n/generated/app_localizations.dart';
import 'location_service.dart';

/// Resolves a [LocationServiceException] to plain-language, localized copy
/// — shared by [LocationPickerScreen] and any other caller of
/// [LocationService] (e.g. the Customer domain's Address Form screen),
/// so this switch is never duplicated per call site.
String locationServiceErrorMessage(
  BuildContext context,
  LocationServiceException exception,
) {
  final l10n = AppLocalizations.of(context);
  return switch (exception.type) {
    LocationServiceErrorType.permissionDenied =>
      l10n.locationPermissionDeniedMessage,
    LocationServiceErrorType.serviceDisabled =>
      l10n.locationServiceDisabledMessage,
    LocationServiceErrorType.unknown => l10n.genericErrorMessage,
  };
}
