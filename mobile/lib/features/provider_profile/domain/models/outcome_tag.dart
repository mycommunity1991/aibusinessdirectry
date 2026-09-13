/// Mirrors the backend's `OutcomeTagResponse`
/// (`backend/app/modules/contact/schemas.py`, REV-001, AC1) --
/// `POST /contact-views/{contact_view_id}/outcome-tag`'s success payload.
/// Deliberately carries no payment amount, job-completion detail, or
/// scheduling field anywhere (AC4).
class OutcomeTag {
  const OutcomeTag({
    required this.id,
    required this.contactViewId,
    required this.hired,
    required this.submittedAt,
  });

  factory OutcomeTag.fromJson(Map<String, dynamic> json) {
    return OutcomeTag(
      id: json['id'] as String,
      contactViewId: json['contact_view_id'] as String,
      hired: json['hired'] as bool,
      submittedAt: DateTime.parse(json['submitted_at'] as String),
    );
  }

  final String id;
  final String contactViewId;

  /// Did the customer hire this provider? A `false` value is retained as a
  /// real signal, not discarded (AC5) -- this model never coerces it to
  /// absent.
  final bool hired;
  final DateTime submittedAt;
}
