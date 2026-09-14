/// Mirrors the backend's `LeadOutcomeStatus` `StrEnum`
/// (`backend/app/modules/contact/schemas.py`, LEAD-001, Decision 5) --
/// computed server-side from `outcome_tags.hired`'s presence/value, never
/// re-derived from a raw boolean/absence on this side (AC5).
enum LeadOutcomeStatus {
  hired,
  notHired,
  notYetReported,

  /// Forward-compatibility fallback for a string this app doesn't
  /// recognize yet -- mirrors `SearchRequestResultStatus.fromWire`'s own
  /// defensive-only `_` case (`features/conversation/domain/models/
  /// search_request_result.dart`). The backend's `LeadOutcomeStatus` enum
  /// has exactly three values today.
  unknown;

  static LeadOutcomeStatus fromWire(String value) => switch (value) {
    'hired' => LeadOutcomeStatus.hired,
    'not_hired' => LeadOutcomeStatus.notHired,
    'not_yet_reported' => LeadOutcomeStatus.notYetReported,
    _ => LeadOutcomeStatus.unknown,
  };
}

/// Mirrors the backend's `LeadResponse`
/// (`backend/app/modules/contact/schemas.py`, LEAD-001, Decision 4) --
/// `GET /providers/me/leads`'s per-item payload. Deliberately carries no
/// `customer_id`, `display_name`, `avatar_url`, or any other
/// customer-identifying field (AC3) -- this model's field set is the
/// entire wire contract, not a subset picked for display.
class Lead {
  const Lead({
    required this.id,
    required this.categoryName,
    required this.viewedAt,
    required this.outcomeStatus,
  });

  factory Lead.fromJson(Map<String, dynamic> json) {
    return Lead(
      id: json['id'] as String,
      categoryName: json['category_name'] as String?,
      viewedAt: DateTime.parse(json['viewed_at'] as String),
      outcomeStatus: LeadOutcomeStatus.fromWire(
        json['outcome_status'] as String,
      ),
    );
  }

  final String id;

  /// `null` when no category/request context is resolvable (Decision 3) --
  /// either no `search_request_id` at all (structured browse path), or a
  /// `search_request_id` whose own `category_id` is itself `null`. The
  /// presentation layer renders an honest fallback string in this case,
  /// never a fabricated category guess.
  final String? categoryName;
  final DateTime viewedAt;
  final LeadOutcomeStatus outcomeStatus;
}
