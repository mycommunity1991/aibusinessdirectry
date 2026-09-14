/// Mirrors the backend's `ReviewResponse`
/// (`backend/app/modules/review/schemas.py`, REV-002, AC1) --
/// `POST /contact-views/{contact_view_id}/review`'s success payload.
class Review {
  const Review({
    required this.id,
    required this.contactViewId,
    required this.providerId,
    required this.rating,
    required this.comment,
    required this.createdAt,
  });

  factory Review.fromJson(Map<String, dynamic> json) {
    return Review(
      id: json['id'] as String,
      contactViewId: json['contact_view_id'] as String,
      providerId: json['provider_id'] as String,
      rating: json['rating'] as int,
      comment: json['comment'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final String contactViewId;
  final String providerId;

  /// 1-5 (AC3).
  final int rating;

  /// Optional free text -- `null` when the customer left no comment.
  final String? comment;
  final DateTime createdAt;
}
