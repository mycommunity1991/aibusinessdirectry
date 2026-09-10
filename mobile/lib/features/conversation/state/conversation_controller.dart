import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/conversation_repository.dart';
import '../domain/models/conversation_exception.dart';
import '../domain/models/conversation_session.dart';
import '../domain/models/search_request_result.dart';

/// The AI Conversation screen's (S-07) perceived-latency tier for the turn
/// currently in flight -- `16_UX_GUIDELINES.md`'s exact staged-feedback
/// rule (AC6/AC7):
/// - [idle]: no turn in flight.
/// - [indicator] (0-500ms-3s): typing indicator only, no text.
/// - [contextual] (>3s): a contextual label ("Finding matches near you").
/// - [handoff] (>8s or a timeout): "we'll notify you" messaging, never an
///   indefinite spinner.
enum ConversationTurnPhase { idle, indicator, contextual, handoff }

/// Overridable via [conversationContextualLabelDelayProvider] for tests,
/// mirroring `claimOtpCountdownDurationProvider`'s pattern -- the real 3s
/// default per `16_UX_GUIDELINES.md`.
const kConversationContextualLabelDelay = Duration(seconds: 3);

/// Overridable via [conversationHandoffDelayProvider] for tests -- the real
/// 8s default per `16_UX_GUIDELINES.md`/AC7.
const kConversationHandoffDelay = Duration(seconds: 8);

/// Overridable via [conversationResultsPollIntervalProvider] for tests --
/// the real interval a `pending_manual_match` result is re-checked at
/// (AI-002, `Plan_S07_AI-002.md` Mobile item 27/28). No push-notification
/// delivery channel exists yet (Explicitly Out of Scope), so light polling
/// is this story's only mechanism for the customer to ever learn a manual
/// resolution landed.
const kConversationResultsPollInterval = Duration(seconds: 5);

final conversationContextualLabelDelayProvider = Provider<Duration>(
  (ref) => kConversationContextualLabelDelay,
);

final conversationHandoffDelayProvider = Provider<Duration>(
  (ref) => kConversationHandoffDelay,
);

final conversationResultsPollIntervalProvider = Provider<Duration>(
  (ref) => kConversationResultsPollInterval,
);

class ConversationState {
  const ConversationState({
    this.session,
    this.turnPhase = ConversationTurnPhase.idle,
    this.revisingMessageId,
    this.error,
    this.searchResults,
  });

  /// `null` until the first `start()` call succeeds -- the screen renders
  /// its "describe what you need" compose view in this state, and the full
  /// chat transcript once a session exists.
  final ConversationSession? session;

  final ConversationTurnPhase turnPhase;

  /// The id of a past customer message currently being revised (AC8), if
  /// any -- drives the screen's inline revise editor.
  final String? revisingMessageId;

  /// The most recent failure, if any -- always inline/non-fatal once a
  /// session exists (the session itself is left exactly as it was), and
  /// fatal (no session to fall back to) only when the very first `start()`
  /// call fails.
  final ConversationException? error;

  /// The most recent `GET /search-requests/{id}` result once [session]
  /// reaches a terminal state with a non-`null` `searchRequestId` (AI-002,
  /// Decision 6) -- `null` until the first fetch succeeds. While its
  /// `status` is `pending_manual_match`, the screen keeps rendering the
  /// same honest waiting copy `AI-001` already ships and this value is
  /// re-polled (`ConversationController`'s poll timer); once `matched`/
  /// `unmatched`, the screen renders the shared ranked-results widget.
  final SearchRequestResult? searchResults;

  bool get isComposing => session == null;

  bool get isBusy => turnPhase != ConversationTurnPhase.idle;

  ConversationState copyWith({
    ConversationSession? session,
    ConversationTurnPhase? turnPhase,
    String? revisingMessageId,
    bool clearRevisingMessageId = false,
    ConversationException? error,
    bool clearError = false,
    SearchRequestResult? searchResults,
  }) {
    return ConversationState(
      session: session ?? this.session,
      turnPhase: turnPhase ?? this.turnPhase,
      revisingMessageId: clearRevisingMessageId
          ? null
          : (revisingMessageId ?? this.revisingMessageId),
      error: clearError ? null : (error ?? this.error),
      searchResults: searchResults ?? this.searchResults,
    );
  }
}

/// Owns the AI Conversation screen's (S-07) full lifecycle: starting a
/// session, submitting turns (free text or a quick-reply choice), revising
/// a past answer (AC8), starting over (Decision 5), and the >3s/>8s
/// latency-tier timers (AC6/AC7).
///
/// A turn is never dropped and the input is never blocked while one is in
/// flight (`16_UX_GUIDELINES.md`: "never freeze input controls while
/// waiting") -- calling [submitFreeText]/[submitQuickReply]/
/// [submitRevision] while a previous turn is still in flight queues the new
/// input; it is dispatched automatically the moment the in-flight turn
/// completes, in the order it was queued.
class ConversationController extends StateNotifier<ConversationState> {
  // The named constructor parameters below keep a public, readable name
  // distinct from the private field they seed -- an initializing formal
  // (`this._field`) would force the external parameter name itself to
  // start with `_`, which is unresolvable from outside this library, so
  // the assignment happens in the constructor body instead.
  ConversationController(
    this._repository, {
    required Duration contextualLabelDelay,
    required Duration handoffDelay,
    required Duration resultsPollInterval,
  }) : super(const ConversationState()) {
    _contextualLabelDelay = contextualLabelDelay;
    _handoffDelay = handoffDelay;
    _resultsPollInterval = resultsPollInterval;
  }

  final ConversationRepository _repository;
  late final Duration _contextualLabelDelay;
  late final Duration _handoffDelay;
  late final Duration _resultsPollInterval;

  bool _turnInFlight = false;
  final List<Future<ConversationSession> Function()> _queue = [];

  Timer? _contextualTimer;
  Timer? _handoffTimer;

  /// The `search_request_id` currently being polled, if any -- set once a
  /// session reaches a terminal state with a non-`null` id (AI-002), and
  /// cleared on [startOver]/[dispose]. Kept independently of
  /// [ConversationState.searchResults] so [pausePolling]/[resumePolling]
  /// know which id to resume against without re-deriving it from
  /// [ConversationState.session].
  String? _pollingSearchRequestId;
  Timer? _resultsPollTimer;

  /// `POST /conversations` (AC1) -- starts a brand-new session from the
  /// customer's free-text opening message. Only meaningful while
  /// [ConversationState.isComposing].
  Future<void> start(String message) {
    final trimmed = message.trim();
    if (trimmed.isEmpty) return Future.value();
    return _enqueueOrRun(() => _repository.start(trimmed));
  }

  /// `POST /conversations/{sessionId}/messages` with free-text `content`
  /// (AC4/AC6/AC7).
  Future<void> submitFreeText(String content) {
    final trimmed = content.trim();
    final sessionId = state.session?.id;
    if (trimmed.isEmpty || sessionId == null) return Future.value();
    return _enqueueOrRun(
      () => _repository.submitTurn(sessionId: sessionId, content: trimmed),
    );
  }

  /// `POST /conversations/{sessionId}/messages` with a quick-reply
  /// `selected_option` (AC4/AC6/AC7).
  Future<void> submitQuickReply(String option) {
    final sessionId = state.session?.id;
    if (sessionId == null) return Future.value();
    return _enqueueOrRun(
      () =>
          _repository.submitTurn(sessionId: sessionId, selectedOption: option),
    );
  }

  /// Opens the inline revise editor for [messageId] (AC8) -- only
  /// meaningful for a past `sender=customer` message while the session is
  /// still active; the screen itself only wires this to tappable customer
  /// bubbles when [ConversationSession.isActive] is true.
  void beginRevise(String messageId) {
    state = state.copyWith(revisingMessageId: messageId);
  }

  void cancelRevise() {
    state = state.copyWith(clearRevisingMessageId: true);
  }

  /// `PATCH /conversations/{sessionId}/answers/{messageId}` (AC8, Decision
  /// 5) -- the chat continues from the edited point, never a restart.
  Future<void> submitRevision(String content) {
    final trimmed = content.trim();
    final sessionId = state.session?.id;
    final messageId = state.revisingMessageId;
    if (trimmed.isEmpty || sessionId == null || messageId == null) {
      return Future.value();
    }
    state = state.copyWith(clearRevisingMessageId: true);
    return _enqueueOrRun(
      () => _repository.reviseAnswer(
        sessionId: sessionId,
        messageId: messageId,
        content: trimmed,
      ),
    );
  }

  /// Decision 5's "Start over" -- deliberately simple: resets this
  /// controller back to its initial compose state. The previous session is
  /// left exactly as it was on the backend (marked `abandoned` the next
  /// time `POST /conversations` is called, per the backend's own
  /// contract) -- this client never deletes or otherwise touches it.
  void startOver() {
    _cancelTimers();
    _stopResultsPolling();
    _turnInFlight = false;
    _queue.clear();
    state = const ConversationState();
  }

  Future<void> _enqueueOrRun(
    Future<ConversationSession> Function() action,
  ) async {
    if (_turnInFlight) {
      _queue.add(action);
      return;
    }
    await _run(action);
  }

  Future<void> _run(Future<ConversationSession> Function() action) async {
    _turnInFlight = true;
    state = state.copyWith(
      turnPhase: ConversationTurnPhase.indicator,
      clearError: true,
    );
    _scheduleLatencyTiers();
    try {
      final session = await action();
      _cancelTimers();
      state = state.copyWith(
        session: session,
        turnPhase: ConversationTurnPhase.idle,
      );
      _syncResultsPolling(session);
    } on ConversationException catch (error) {
      _cancelTimers();
      state = state.copyWith(
        turnPhase: ConversationTurnPhase.idle,
        error: error,
      );
    } finally {
      _turnInFlight = false;
      unawaited(_drainQueue());
    }
  }

  Future<void> _drainQueue() async {
    if (_queue.isEmpty || _turnInFlight) return;
    final next = _queue.removeAt(0);
    await _run(next);
  }

  void _scheduleLatencyTiers() {
    _contextualTimer = Timer(_contextualLabelDelay, () {
      if (state.turnPhase == ConversationTurnPhase.indicator) {
        state = state.copyWith(turnPhase: ConversationTurnPhase.contextual);
      }
    });
    _handoffTimer = Timer(_handoffDelay, () {
      if (state.turnPhase != ConversationTurnPhase.idle) {
        state = state.copyWith(turnPhase: ConversationTurnPhase.handoff);
      }
    });
  }

  void _cancelTimers() {
    _contextualTimer?.cancel();
    _contextualTimer = null;
    _handoffTimer?.cancel();
    _handoffTimer = null;
  }

  /// Starts or stops the `pending_manual_match` poll loop (AI-002, Mobile
  /// item 27/28) to match [session]'s freshly-received state -- called
  /// after every successful turn/session fetch, since a session can reach
  /// its terminal state (and gain a non-`null` `searchRequestId`) on any
  /// turn, not just a specific one.
  void _syncResultsPolling(ConversationSession session) {
    final searchRequestId = session.searchRequestId;
    if (!session.isTerminal || searchRequestId == null) {
      _stopResultsPolling();
      return;
    }
    if (_pollingSearchRequestId == searchRequestId &&
        _resultsPollTimer != null) {
      return;
    }
    _pollingSearchRequestId = searchRequestId;
    unawaited(_pollResultsOnce());
    _resultsPollTimer?.cancel();
    _resultsPollTimer = Timer.periodic(
      _resultsPollInterval,
      (_) => unawaited(_pollResultsOnce()),
    );
  }

  Future<void> _pollResultsOnce() async {
    final searchRequestId = _pollingSearchRequestId;
    if (searchRequestId == null) return;
    try {
      final result = await _repository.getSearchRequestResults(searchRequestId);
      // A stale in-flight fetch (e.g. `startOver` ran while this call was
      // pending) must never resurrect polling for an abandoned session.
      if (_pollingSearchRequestId != searchRequestId) return;
      state = state.copyWith(searchResults: result);
      if (result.isResolved) {
        _stopResultsPolling();
      }
    } on ConversationException {
      // Transient (network blip, momentary 5xx) -- the screen keeps
      // showing whatever it was already showing (AI-001's existing waiting
      // copy), and the next scheduled tick simply retries. Never surfaces
      // a new customer-facing error state for a background poll.
    }
  }

  void _stopResultsPolling() {
    _resultsPollTimer?.cancel();
    _resultsPollTimer = null;
    _pollingSearchRequestId = null;
  }

  /// Pauses the poll loop while the app is backgrounded (screen-lifecycle-
  /// aware, `Plan_S07_AI-002.md` Mobile item 27) -- keeps
  /// [_pollingSearchRequestId] intact so [resumePolling] can restart
  /// cleanly, rather than fully tearing down polling state.
  void pausePolling() {
    _resultsPollTimer?.cancel();
    _resultsPollTimer = null;
  }

  /// Resumes the poll loop after the app returns to the foreground, if a
  /// session is still waiting on a result. A no-op if no session is
  /// currently pending, or if the result already resolved while paused.
  void resumePolling() {
    final searchRequestId = _pollingSearchRequestId;
    if (searchRequestId == null) return;
    if (state.searchResults?.isResolved ?? false) return;
    if (_resultsPollTimer != null) return;
    unawaited(_pollResultsOnce());
    _resultsPollTimer = Timer.periodic(
      _resultsPollInterval,
      (_) => unawaited(_pollResultsOnce()),
    );
  }

  @override
  void dispose() {
    _cancelTimers();
    _stopResultsPolling();
    super.dispose();
  }
}

final conversationControllerProvider =
    StateNotifierProvider.autoDispose<
      ConversationController,
      ConversationState
    >(
      (ref) => ConversationController(
        ref.watch(conversationRepositoryProvider),
        contextualLabelDelay: ref.watch(
          conversationContextualLabelDelayProvider,
        ),
        handoffDelay: ref.watch(conversationHandoffDelayProvider),
        resultsPollInterval: ref.watch(conversationResultsPollIntervalProvider),
      ),
    );
