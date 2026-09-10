/// Mirrors the backend's `MessageResponse`
/// (`backend/app/modules/conversation/schemas.py`, AI-001, AC1) -- one
/// transcript entry in a [ConversationSession].
enum ConversationMessageSender {
  customer,
  ai;

  static ConversationMessageSender fromWire(String value) => switch (value) {
    'customer' => ConversationMessageSender.customer,
    'ai' => ConversationMessageSender.ai,
    // Defensive only -- the backend enum has exactly these two values
    // (`MessageSender`); an unrecognized value should never occur.
    _ => ConversationMessageSender.ai,
  };
}

class ConversationMessage {
  const ConversationMessage({
    required this.id,
    required this.sender,
    required this.content,
    required this.sequenceNumber,
    required this.createdAt,
  });

  factory ConversationMessage.fromJson(Map<String, dynamic> json) {
    return ConversationMessage(
      id: json['id'] as String,
      sender: ConversationMessageSender.fromWire(json['sender'] as String),
      content: json['content'] as String,
      sequenceNumber: (json['sequence_number'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final ConversationMessageSender sender;
  final String content;
  final int sequenceNumber;
  final DateTime createdAt;
}
