/// Mirrors the backend's `NotificationResponse`
/// (`backend/app/modules/notification/schemas.py`, `ENG-001`, AC6,
/// Decision 10) -- `GET /notifications`/`PATCH /notifications/{id}/read`'s
/// per-item payload. Raw fields only, client-computed grouping (`ADR-046`'s
/// "raw fields, client-computed, never a server-computed enum" precedent):
/// [NotificationsInboxScreen] groups rows into New/Earlier by
/// `readAt == null` itself, and deep-links each row by [relatedEntityType].
class NotificationItem {
  const NotificationItem({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    this.relatedEntityType,
    this.relatedEntityId,
    this.readAt,
    required this.createdAt,
  });

  factory NotificationItem.fromJson(Map<String, dynamic> json) {
    return NotificationItem(
      id: json['id'] as String,
      type: json['type'] as String,
      title: json['title'] as String,
      body: json['body'] as String,
      relatedEntityType: json['related_entity_type'] as String?,
      relatedEntityId: json['related_entity_id'] as String?,
      readAt: json['read_at'] == null
          ? null
          : DateTime.parse(json['read_at'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final String type;
  final String title;
  final String body;

  /// `null` for a notification with no linked entity (none exist yet in
  /// practice -- every one of this story's four trigger types sets one),
  /// but modeled as nullable to mirror the backend's own nullable column
  /// honestly.
  final String? relatedEntityType;
  final String? relatedEntityId;

  /// `null` = unread ("New"); a real timestamp = read ("Earlier") --
  /// AC6's New/Earlier grouping boundary.
  final DateTime? readAt;
  final DateTime createdAt;

  /// A copy with [readAt] replaced -- used for an optimistic local update
  /// after `PATCH /notifications/{id}/read` resolves, without re-fetching
  /// the whole list.
  NotificationItem copyWithReadAt(DateTime readAt) {
    return NotificationItem(
      id: id,
      type: type,
      title: title,
      body: body,
      relatedEntityType: relatedEntityType,
      relatedEntityId: relatedEntityId,
      readAt: readAt,
      createdAt: createdAt,
    );
  }
}
