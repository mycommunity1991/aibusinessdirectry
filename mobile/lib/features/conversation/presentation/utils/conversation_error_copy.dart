import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/conversation_exception.dart';

/// Renders a [ConversationException] as a plain-language, localized string
/// -- never the backend's raw message, a status code, or an internal
/// identifier (`docs/AI/06_SECURITY.md`). Mirrors `claim_error_copy.dart`'s
/// pattern.
String conversationErrorMessage(
  BuildContext context,
  ConversationException error,
) {
  final l10n = AppLocalizations.of(context);
  return switch (error.type) {
    ConversationErrorType.network => l10n.networkErrorMessage,
    ConversationErrorType.sessionNotFound =>
      l10n.aiConversationSessionNotFoundMessage,
    ConversationErrorType.sessionNotActive =>
      l10n.aiConversationSessionNotActiveMessage,
    ConversationErrorType.answerNotRevisable =>
      l10n.aiConversationAnswerNotRevisableMessage,
    ConversationErrorType.validationFailed =>
      l10n.aiConversationValidationFailedMessage,
    ConversationErrorType.unknown => l10n.genericErrorMessage,
  };
}
