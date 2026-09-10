import 'conversation_message.dart';

/// Mirrors the backend's `ConversationStatus`
/// (`backend/app/modules/conversation/models.py`, AI-001, Decision 5).
/// [routedToAdmin] and [abandoned] are both terminal, non-`active` states
/// from the mobile client's perspective -- neither is ever surfaced as a
/// fake results list (Decision 1); [routedToAdmin] gets the same honest,
/// plain completion confirmation as [completed].
enum ConversationSessionStatus {
  active,
  completed,
  routedToAdmin,
  abandoned;

  static ConversationSessionStatus fromWire(String value) => switch (value) {
    'active' => ConversationSessionStatus.active,
    'completed' => ConversationSessionStatus.completed,
    'routed_to_admin' => ConversationSessionStatus.routedToAdmin,
    'abandoned' => ConversationSessionStatus.abandoned,
    // Defensive only -- the backend enum has exactly these four values.
    _ => ConversationSessionStatus.active,
  };
}

/// Mirrors the backend's `ConversationSessionResponse`
/// (`backend/app/modules/conversation/schemas.py`, AI-001, Decision 7).
/// Deliberately has no confidence/score field at all -- the backend never
/// sends one (AC6) -- so there is nothing for this model, or any widget
/// built from it, to accidentally render.
class ConversationSession {
  const ConversationSession({
    required this.id,
    required this.status,
    required this.messages,
    this.categoryId,
    this.quickReplyOptions,
  });

  factory ConversationSession.fromJson(Map<String, dynamic> json) {
    final messagesJson = json['messages'] as List<dynamic>? ?? const [];
    final quickReplyOptionsJson = json['quick_reply_options'] as List<dynamic>?;
    return ConversationSession(
      id: json['id'] as String,
      status: ConversationSessionStatus.fromWire(json['status'] as String),
      categoryId: json['category_id'] as String?,
      messages: messagesJson
          .cast<Map<String, dynamic>>()
          .map(ConversationMessage.fromJson)
          .toList(),
      quickReplyOptions: quickReplyOptionsJson?.cast<String>(),
    );
  }

  final String id;
  final ConversationSessionStatus status;
  final String? categoryId;
  final List<ConversationMessage> messages;

  /// Chip choices for the current turn, if the AI expects a selection
  /// rather than free text. `null` when free text is expected, or when
  /// [status] is no longer [ConversationSessionStatus.active].
  final List<String>? quickReplyOptions;

  bool get isActive => status == ConversationSessionStatus.active;

  bool get isTerminal => !isActive;

  bool get hasQuickReplyOptions =>
      quickReplyOptions != null && quickReplyOptions!.isNotEmpty;
}
