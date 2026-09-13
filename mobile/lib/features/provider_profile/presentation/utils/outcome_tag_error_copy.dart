import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/outcome_tag_exception.dart';

/// Renders an [OutcomeTagException] as a plain-language, localized string --
/// never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors `contact_error_copy.dart`'s
/// pattern. In practice, only [OutcomeTagErrorType.network]/[unknown] ever
/// reach this -- [OutcomeTagPromptSheet] closes quietly for
/// [OutcomeTagErrorType.notFound]/[alreadyExists] instead of showing this
/// message (both are effectively-unreachable edge cases meaning "nothing
/// more to do here").
String outcomeTagErrorMessage(BuildContext context, OutcomeTagException error) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    OutcomeTagErrorType.network => l10n.networkErrorMessage,
    OutcomeTagErrorType.notFound => l10n.genericErrorMessage,
    OutcomeTagErrorType.alreadyExists => l10n.genericErrorMessage,
    OutcomeTagErrorType.unknown => l10n.genericErrorMessage,
  };
}
