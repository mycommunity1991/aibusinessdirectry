/// The category of failure behind a [ConversationException].
///
/// Deliberately coarse-grained, mirroring `claim_exception.dart`'s
/// [ClaimErrorType]: the UI layer never needs a raw HTTP status code or
/// backend error identifier (`docs/AI/06_SECURITY.md`), only enough to pick
/// the right plain-language, localized copy.
enum ConversationErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// The target session either doesn't exist, or doesn't belong to the
  /// caller -- the response never reveals which (backend 404,
  /// `ensure_owner_or_not_found`).
  sessionNotFound,

  /// The session is no longer `active` (already `completed`,
  /// `routed_to_admin`, or `abandoned`) -- backend 409.
  sessionNotActive,

  /// `message_id` does not reference an existing customer message in this
  /// session, or the session can no longer be revised -- backend 422 from
  /// `PATCH /conversations/{id}/answers/{messageId}` specifically (AC8,
  /// Decision 5). Never inferred from status code alone -- only that call
  /// site maps its 422s here (see `ConversationRepository.reviseAnswer`).
  answerNotRevisable,

  /// The request body failed backend field validation (a plain FastAPI
  /// `RequestValidationError`, e.g. the 2000-character limit on
  /// `StartConversationRequest.message`/`SubmitTurnRequest.content`) --
  /// backend 422 from any endpoint *other than* the revise-answer one.
  /// Semantically unrelated to [answerNotRevisable] even though both
  /// arrive as HTTP 422.
  validationFailed,

  /// Anything else (401/403 the screen shouldn't normally hit since it's
  /// only reachable while authenticated, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language conversation-flow failure, thrown by
/// [ConversationRepository]. Carries only [type] -- never the backend's
/// raw `message` string, an HTTP status code, or an internal error
/// identifier.
class ConversationException implements Exception {
  const ConversationException({required this.type});

  final ConversationErrorType type;

  @override
  String toString() => 'ConversationException(type: $type)';
}
