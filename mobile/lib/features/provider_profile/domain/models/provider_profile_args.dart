/// Arguments passed from a provider result card's tap to the Provider
/// Profile screen (S-09, CON-001) via GoRouter's `extra`, and used to key
/// both [ProviderProfileController]/[ContactRevealController] (mirrors
/// `OtpEntryArgs`'s record-typedef pattern, `features/auth/domain/models/
/// otp_entry_args.dart`).
///
/// [searchRequestId] is `null` when reached from the structured (non-AI)
/// search path (`SearchResultsScreen`, DIR-001), which creates no
/// `search.search_requests` row at all -- and the session's real,
/// already-known id when reached from the AI Conversation results view
/// (AI-002), threaded down from `ConversationController`'s own polling
/// state (Decision 4, `Plan_S08_CON-001.md`).
typedef ProviderProfileArgs = ({String providerId, String? searchRequestId});
