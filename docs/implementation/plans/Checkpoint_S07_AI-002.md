# Checkpoint — Sprint 07, Story AI-002 (Receive Matches Even When AI Confidence Is Low)

**Written by:** `frontend` agent
**Status:** Mobile (frontend) implementation complete. Backend already merged (`eb34f38`). Next: `tester`, then `architect`, then pause for user sign-off before `tech-lead` writes the Walkthrough / updates the tracker.

---

## Current task

Implement the mobile side of `Plan_S07_AI-002.md`'s "Mobile — Proposed Changes" (items 25–30): the shared
ranked-results widget extraction, `conversation_repository.dart`'s `getSearchRequestResults`, the
`ai_conversation_screen.dart` completion-state change with lifecycle-aware polling for `pending_manual_match`,
the controller's poll-timer, and the two required test-file extensions.

## Files touched

**New:**
- `mobile/lib/shared/models/ranked_provider_result.dart` — shared, nullable-distance provider-result model used
  by both `features/search` and `features/conversation`.
- `mobile/lib/shared/widgets/provider_result_card.dart` — moved/renamed from `features/search`'s
  `provider_search_card.dart`; now operates on `RankedProviderResult`; omits the distance line when
  `distanceMeters == null` (AI-002 Decision 2c) instead of guessing/zeroing it.
- `mobile/lib/shared/widgets/ranked_provider_results_list.dart` — the new shared list widget (Mobile item 25),
  consumed by both `SearchResultsScreen` (S-08) and `AiConversationScreen`'s resolved-results state (S-07).
- `mobile/lib/features/conversation/domain/models/search_request_result.dart` — mirrors
  `SearchRequestResultResponse`/`SearchRequestStatus` (backend `search` module).
- `mobile/test/shared/widgets/provider_result_card_test.dart` — moved/adapted from
  `mobile/test/features/search/provider_search_card_test.dart` (deleted), plus one new case for the
  `distanceMeters == null` rendering rule.

**Modified:**
- `mobile/lib/features/search/domain/models/search_result_provider.dart` — added
  `SearchResultProviderRanking.toRankedProviderResult()` mapping extension.
- `mobile/lib/features/search/presentation/screens/search_results_screen.dart` — renders results via the shared
  `RankedProviderResultsList` instead of a feature-local `ListView.builder`/`ProviderSearchCard`.
- `mobile/lib/features/conversation/domain/models/conversation_session.dart` — added
  `searchRequestId` field.
- `mobile/lib/features/conversation/data/conversation_repository.dart` — added
  `getSearchRequestResults(searchRequestId)` (`GET /search-requests/{id}`).
- `mobile/lib/features/conversation/state/conversation_controller.dart` — added
  `searchResults` to `ConversationState`; poll-timer lifecycle (`_syncResultsPolling`, `_pollResultsOnce`,
  `pausePolling`, `resumePolling`), cancelled on `startOver`/`dispose`; new
  `conversationResultsPollIntervalProvider` (default 5s, overridable for tests).
- `mobile/lib/features/conversation/presentation/screens/ai_conversation_screen.dart` — `_AiConversationScreenState`
  now mixes in `WidgetsBindingObserver` to pause/resume polling with app foreground/background lifecycle; the
  terminal-session branch now renders the shared ranked-results widget once `matched`/`unmatched` (new
  `_ResolvedResultsView`/`_NoMatchesState` widgets), while `pending_manual_match` keeps showing the **exact
  existing** `_CompletionBanner` copy verbatim (no new waiting string).
- `mobile/lib/l10n/app_en.arb` / `app_ar.arb` — two new strings: `aiConversationResultsHeading`,
  `aiConversationNoMatchesMessage` (both forbidden-word-clean; regenerated via `flutter gen-l10n`).
- `mobile/test/features/conversation/fakes/fake_conversation_repository.dart` — added
  `getSearchRequestResults` support (`getSearchRequestResultsResult`/`getSearchRequestResultsSequence`/
  `getSearchRequestResultsError`, call-count/last-arg tracking).
- `mobile/test/features/conversation/ai_conversation_screen_test.dart` — new `group` covering all three
  terminal states (`matched`, `unmatched`, `pending_manual_match` → poll → resolve), plus forbidden-word
  assertions.
- `mobile/test/features/conversation/test_helpers.dart` — added `expectNoForbiddenWordsRendered`.

**Deleted:**
- `mobile/lib/features/search/presentation/widgets/provider_search_card.dart` (superseded by
  `shared/widgets/provider_result_card.dart`).
- `mobile/test/features/search/provider_search_card_test.dart` (moved to
  `mobile/test/shared/widgets/provider_result_card_test.dart`).

## What's done

- Full shared-widget extraction achieved (Mobile item 25) — **not** flagged as new debt. Both
  `features/search` and `features/conversation` render provider results through
  `shared/widgets/ranked_provider_results_list.dart`/`provider_result_card.dart`; neither feature imports the
  other's screen/widget file. This does not worsen `13_OPEN_DECISIONS.md` item 12 (unrelated —
  `SavedAddressRepository` cross-feature import — untouched by this story).
- `flutter analyze`: 0 issues.
- `flutter test`: 169/169 passing (baseline 165 + 4 net new: -4 old `provider_search_card_test.dart` cases,
  +5 moved/adapted `provider_result_card_test.dart` cases, +3 new `ai_conversation_screen_test.dart` AI-002
  cases).
- `dart format`: applied to all files touched by this story. One pre-existing, unrelated formatting drift was
  found in `mobile/test/features/conversation/conversation_repository_test.dart` (a file this story never
  touched) — left as-is, not in scope.

## What's next

1. `tester` — verify AC2/AC3/AC4 end-to-end from the mobile side against the real backend (or integration
   fakes): pending → poll → resolved transition; forbidden-word discipline; the shared-widget rendering
   parity between S-08 and the AI-conversation results state.
2. `architect` — review the shared-widget extraction (item 25) for genuine reuse (no residual duplication),
   the new `RankedProviderResult`/`SearchRequestResult` models for cycle-freedom, and the poll-timer lifecycle
   for correctness (paused on background, cancelled on dispose/`startOver`, no leaked `Timer`).
3. Once both report clean, pause and present to the user before `tech-lead` writes the Walkthrough or touches
   `docs/CHANGELOG.md`/tracker.

## Open notes / deviations from the Plan (flagged, not silent)

- The Plan's Decision 6 prose says the completion state "now navigates to a ranked-results view"; item 27
  clarifies this as rendering the shared widget inline within `ai_conversation_screen.dart` itself, not a
  `Navigator`/`GoRouter` push to a separate route. Implemented as a full-body replacement of `_ActiveView`
  (transcript hidden once resolved) rather than squeezing a scrollable results list into the screen's existing
  compact bottom input-area slot — the latter has no bounded height for a `ListView` and was never going to
  render workably. This is a scoped engineering judgment call, not a deviation from any explicit AC.
- Two new, forbidden-word-clean customer-facing strings were added (`aiConversationResultsHeading`,
  `aiConversationNoMatchesMessage`) for the `matched`/`unmatched` states — the Plan's Decision 7 only requires
  the *pending* waiting copy to be reused verbatim; it does not prohibit new copy elsewhere, provided it avoids
  "manual"/"fallback"/"admin". Both were checked against the forbidden-word list by hand and via
  `expectNoForbiddenWordsRendered` in the widget test.
- Poll interval default chosen as 5 seconds (`kConversationResultsPollInterval`) — the Plan says "a short
  interval" without a specific number; not specified elsewhere in `docs/AI/`. Flagging this as a reasonable
  default, not a locked value — a future story/CTO input could tune it.
