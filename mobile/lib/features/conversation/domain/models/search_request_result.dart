import '../../../../shared/models/ranked_provider_result.dart';

/// Mirrors the backend's `SearchRequestStatus` enum
/// (`backend/app/modules/search/models.py`, AI-002) -- the outcome of the
/// `search.search_requests` row created once an AI Conversation session
/// completes (`ConversationSessionResponse.search_request_id`, Decision 6).
enum SearchRequestResultStatus {
  matched,
  unmatched,
  pendingManualMatch;

  static SearchRequestResultStatus fromWire(String value) => switch (value) {
    'matched' => SearchRequestResultStatus.matched,
    'unmatched' => SearchRequestResultStatus.unmatched,
    'pending_manual_match' => SearchRequestResultStatus.pendingManualMatch,
    // Defensive only -- the backend enum has exactly these three values.
    _ => SearchRequestResultStatus.pendingManualMatch,
  };
}

/// Mirrors the backend's `SearchRequestResultResponse`
/// (`backend/app/modules/search/schemas.py`, AI-002, Decision 6) --
/// `GET /search-requests/{id}`'s payload. Identical in shape whether the
/// request was resolved by the automated matcher or by an admin (AC4) --
/// nothing in this model, or the backend response it mirrors, ever
/// distinguishes the two.
class SearchRequestResult {
  const SearchRequestResult({
    required this.status,
    this.matchedProviders = const [],
  });

  factory SearchRequestResult.fromJson(Map<String, dynamic> json) {
    final providersJson =
        json['matched_providers'] as List<dynamic>? ?? const [];
    return SearchRequestResult(
      status: SearchRequestResultStatus.fromWire(json['status'] as String),
      matchedProviders: providersJson
          .cast<Map<String, dynamic>>()
          .map(RankedProviderResult.fromJson)
          .toList(),
    );
  }

  final SearchRequestResultStatus status;
  final List<RankedProviderResult> matchedProviders;

  /// Still waiting on a human to resolve the low-confidence session
  /// (AC2/AC3) -- the mobile client must keep showing the existing, honest
  /// waiting copy while this is true, polling rather than surfacing any new
  /// customer-facing state (`16_UX_GUIDELINES.md` invisibility rule).
  bool get isPending => status == SearchRequestResultStatus.pendingManualMatch;

  bool get isResolved => !isPending;
}
