/// The category of failure behind a [NotificationException]. Deliberately
/// coarse-grained, mirroring `lead_exception.dart`'s [LeadErrorType]
/// pattern -- the UI layer never needs a raw HTTP status code or backend
/// error identifier (`docs/AI/06_SECURITY.md`).
///
/// Only two cases exist here (unlike `LeadErrorType`'s three) -- every
/// `/notifications*` endpoint (`ENG-001`, Decision 10) is gated by plain
/// `get_current_user` only, with no caller-has-no-X-yet 404 case analogous
/// to `LeadRepository.listMyLeads`'s "no Provider listing yet."
/// `PATCH .../read`'s 404 (wrong/missing `notification_id`) is not
/// user-triggerable from the Inbox screen's own UI (every id it acts on
/// came from that same list a moment earlier), so it is not modeled as its
/// own case here -- it falls into [unknown], the same honest, catch-all
/// bucket [NotificationRepository] uses for it.
enum NotificationErrorType {
  /// The request never reached the server (no connectivity, timeout, DNS).
  network,

  /// Anything else (401 the screen shouldn't normally hit since it's only
  /// reachable while authenticated, 404, 5xx, or an unrecognized shape).
  unknown,
}

/// A plain-language Notifications load/action failure, thrown by
/// [NotificationRepository]. Carries only [type] -- never the backend's raw
/// `message` string, an HTTP status code, or an internal error identifier.
class NotificationException implements Exception {
  const NotificationException({required this.type});

  final NotificationErrorType type;

  @override
  String toString() => 'NotificationException(type: $type)';
}
