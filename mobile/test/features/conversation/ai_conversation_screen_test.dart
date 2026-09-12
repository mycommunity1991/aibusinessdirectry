import 'dart:async';

import 'package:ai_marketplace_app/features/conversation/data/conversation_repository.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_message.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_session.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/search_request_result.dart';
import 'package:ai_marketplace_app/features/conversation/presentation/screens/ai_conversation_screen.dart';
import 'package:ai_marketplace_app/features/conversation/state/conversation_controller.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:ai_marketplace_app/shared/models/ranked_provider_result.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_conversation_repository.dart';
import 'test_helpers.dart';

/// S-07 -- AI Conversation (AI-001).
void main() {
  Future<void> startSession(
    WidgetTester tester, {
    String message = 'My kitchen sink is leaking',
  }) async {
    await tester.enterText(
      find.byKey(const ValueKey('ai-conversation-compose-field')),
      message,
    );
    await tester.pump();
    await tester.tap(
      find.byKey(const ValueKey('ai-conversation-start-button')),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    'quick-reply chips render only when the current turn offers options; '
    'free text renders otherwise (AC4)',
    (tester) async {
      final chippedSession = ConversationSession(
        id: 'session-1',
        status: ConversationSessionStatus.active,
        messages: const [],
        quickReplyOptions: const ['Plumbing', 'Electrical'],
      );
      final fakeRepository = FakeConversationRepository(
        startResult: chippedSession,
      );

      await pumpConversationScreen(
        tester,
        child: const AiConversationScreen(),
        overrides: [
          conversationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await startSession(tester);

      expect(find.text('Plumbing'), findsOneWidget);
      expect(find.text('Electrical'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('ai-conversation-answer-field')),
        findsNothing,
      );

      // Selecting a chip submits it as `selected_option`, never `content`.
      fakeRepository.submitTurnResult = const ConversationSession(
        id: 'session-1',
        status: ConversationSessionStatus.active,
        messages: [],
      );
      await tester.tap(find.text('Plumbing'));
      await tester.pumpAndSettle();

      expect(fakeRepository.submitTurnCallCount, 1);
      expect(fakeRepository.lastSubmitTurnArgs?.selectedOption, 'Plumbing');
      expect(fakeRepository.lastSubmitTurnArgs?.content, isNull);

      // The next turn has no quick-reply options -- free text renders
      // instead, never both at once.
      expect(find.text('Plumbing'), findsNothing);
      expect(
        find.byKey(const ValueKey('ai-conversation-answer-field')),
        findsOneWidget,
      );
    },
  );

  testWidgets('tapping a past customer bubble opens the revise flow and calls '
      "the repository's reviseAnswer (AC8)", (tester) async {
    final session = ConversationSession(
      id: 'session-1',
      status: ConversationSessionStatus.active,
      messages: [
        ConversationMessage(
          id: 'message-1',
          sender: ConversationMessageSender.customer,
          content: 'My kitchen sink is leaking',
          sequenceNumber: 1,
          createdAt: DateTime(2026, 1, 1),
        ),
        ConversationMessage(
          id: 'message-2',
          sender: ConversationMessageSender.ai,
          content: 'Which category best matches your need?',
          sequenceNumber: 2,
          createdAt: DateTime(2026, 1, 1),
        ),
      ],
    );
    final fakeRepository = FakeConversationRepository(startResult: session);

    await pumpConversationScreen(
      tester,
      child: const AiConversationScreen(),
      overrides: [
        conversationRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );
    await startSession(tester);

    await tester.tap(find.text('My kitchen sink is leaking'));
    await tester.pumpAndSettle();

    final reviseField = find.byKey(
      const ValueKey('ai-conversation-revise-field'),
    );
    expect(reviseField, findsOneWidget);
    final reviseInnerField = find.descendant(
      of: reviseField,
      matching: find.byType(TextField),
    );
    expect(
      tester.widget<TextField>(reviseInnerField).controller?.text,
      'My kitchen sink is leaking',
    );

    await tester.enterText(reviseInnerField, 'My bathroom sink is leaking');
    await tester.pump();
    fakeRepository.reviseAnswerResult = ConversationSession(
      id: 'session-1',
      status: ConversationSessionStatus.active,
      messages: [
        ConversationMessage(
          id: 'message-1',
          sender: ConversationMessageSender.customer,
          content: 'My bathroom sink is leaking',
          sequenceNumber: 1,
          createdAt: DateTime(2026, 1, 1),
        ),
      ],
    );
    await tester.tap(find.byKey(const ValueKey('ai-conversation-revise-save')));
    await tester.pumpAndSettle();

    expect(fakeRepository.reviseAnswerCallCount, 1);
    expect(fakeRepository.lastReviseAnswerArgs?.sessionId, 'session-1');
    expect(fakeRepository.lastReviseAnswerArgs?.messageId, 'message-1');
    expect(
      fakeRepository.lastReviseAnswerArgs?.content,
      'My bathroom sink is leaking',
    );
    expect(find.text('My bathroom sink is leaking'), findsOneWidget);
  });

  testWidgets(
    '"Start over" resets to the compose step and starts a fresh session '
    '(Decision 5)',
    (tester) async {
      final fakeRepository = FakeConversationRepository(
        startResult: const ConversationSession(
          id: 'session-1',
          status: ConversationSessionStatus.active,
          messages: [],
        ),
      );

      await pumpConversationScreen(
        tester,
        child: const AiConversationScreen(),
        overrides: [
          conversationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await startSession(tester);
      expect(fakeRepository.startCallCount, 1);

      await tester.tap(
        find.byKey(const ValueKey('ai-conversation-start-over')),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('ai-conversation-compose-field')),
        findsOneWidget,
      );

      fakeRepository.startResult = const ConversationSession(
        id: 'session-2',
        status: ConversationSessionStatus.active,
        messages: [],
      );
      await startSession(tester, message: 'My AC is broken');

      expect(fakeRepository.startCallCount, 2);
      expect(fakeRepository.lastStartMessage, 'My AC is broken');
    },
  );

  testWidgets('typing indicator tiers fire at the documented thresholds, and a '
      'response taking longer than 8s transitions to the "we\'ll notify '
      'you" state rather than an indefinite spinner (AC6/AC7)', (tester) async {
    final gate = Completer<void>();
    final fakeRepository = FakeConversationRepository(gate: gate.future);

    await pumpConversationScreen(
      tester,
      child: const AiConversationScreen(),
      overrides: [
        conversationRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    await tester.enterText(
      find.byKey(const ValueKey('ai-conversation-compose-field')),
      'My kitchen sink is leaking',
    );
    await tester.pump();
    await tester.tap(
      find.byKey(const ValueKey('ai-conversation-start-button')),
    );

    // 0-500ms-3s: typing indicator only, no text label.
    await tester.pump();
    expect(
      find.byKey(const ValueKey('ai-conversation-typing-indicator')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('ai-conversation-contextual-label')),
      findsNothing,
    );

    await tester.pump(const Duration(milliseconds: 2900));
    expect(
      find.byKey(const ValueKey('ai-conversation-typing-indicator')),
      findsOneWidget,
    );

    // >3s: a contextual label, never a raw percentage/confidence score.
    await tester.pump(const Duration(milliseconds: 200));
    expect(
      find.byKey(const ValueKey('ai-conversation-contextual-label')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('ai-conversation-typing-indicator')),
      findsNothing,
    );

    // >8s: graceful hand-off messaging, never an indefinite spinner.
    await tester.pump(const Duration(seconds: 5));
    expect(
      find.byKey(const ValueKey('ai-conversation-handoff-banner')),
      findsOneWidget,
    );
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(
      find.byKey(const ValueKey('ai-conversation-contextual-label')),
      findsNothing,
    );

    expectNoConfidenceValueRendered(tester);

    // Clean up the still-pending call so the test tears down cleanly.
    gate.complete();
    await tester.pumpAndSettle();
  });

  testWidgets(
    'no widget ever displays a raw numeric confidence value, across the '
    'full compose -> active -> completion lifecycle (AC6)',
    (tester) async {
      final fakeRepository = FakeConversationRepository(
        startResult: const ConversationSession(
          id: 'session-1',
          status: ConversationSessionStatus.completed,
          messages: [],
        ),
      );

      await pumpConversationScreen(
        tester,
        child: const AiConversationScreen(),
        overrides: [
          conversationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      expectNoConfidenceValueRendered(tester);

      await startSession(tester);

      expect(
        find.byKey(const ValueKey('ai-conversation-completion-title')),
        findsOneWidget,
      );
      // Decision 1 -- an honest, plain confirmation, never a fake results
      // list, and (AC6) never a confidence value anywhere.
      expectNoConfidenceValueRendered(tester);
    },
  );

  testWidgets('chat bubbles mirror correctly under RTL (Arabic) -- customer '
      'end-aligned, AI start-aligned, using direction-aware alignment (AC11)', (
    tester,
  ) async {
    final session = ConversationSession(
      id: 'session-1',
      status: ConversationSessionStatus.active,
      messages: [
        ConversationMessage(
          id: 'message-1',
          sender: ConversationMessageSender.customer,
          content: 'رسالة العميل',
          sequenceNumber: 1,
          createdAt: DateTime(2026, 1, 1),
        ),
        ConversationMessage(
          id: 'message-2',
          sender: ConversationMessageSender.ai,
          content: 'رسالة الذكاء الاصطناعي',
          sequenceNumber: 2,
          createdAt: DateTime(2026, 1, 1),
        ),
      ],
    );
    final fakeRepository = FakeConversationRepository(startResult: session);

    await pumpConversationScreen(
      tester,
      child: const AiConversationScreen(),
      overrides: [
        conversationRepositoryProvider.overrideWithValue(fakeRepository),
      ],
      locale: const Locale('ar'),
    );
    await startSession(tester, message: 'وصف الحاجة');

    final customerAlign = tester.widget<Align>(
      find
          .ancestor(of: find.text('رسالة العميل'), matching: find.byType(Align))
          .first,
    );
    final aiAlign = tester.widget<Align>(
      find
          .ancestor(
            of: find.text('رسالة الذكاء الاصطناعي'),
            matching: find.byType(Align),
          )
          .first,
    );

    // Direction-aware alignment, never a literal Alignment.centerLeft/
    // centerRight -- the latter would not mirror under RTL at all.
    expect(customerAlign.alignment, AlignmentDirectional.centerEnd);
    expect(aiAlign.alignment, AlignmentDirectional.centerStart);

    // Under RTL, "end" resolves to the left edge -- the customer bubble
    // must render to the *left* of the AI bubble (the mirror image of
    // LTR), proving the alignment actually takes effect, not merely
    // typed correctly with no visible effect.
    final customerX = tester.getTopLeft(find.text('رسالة العميل')).dx;
    final aiX = tester.getTopLeft(find.text('رسالة الذكاء الاصطناعي')).dx;
    expect(customerX, lessThan(aiX));
  });

  group('AI-002 -- ranked-results completion states (Decision 6/AC3/AC4)', () {
    const matchedProvider = RankedProviderResult(
      id: 'provider-1',
      displayName: 'Al Noor Plumbing Services LLC',
      slug: 'al-noor-plumbing',
      providerType: ProviderType.business,
      categoryLabels: ['Plumbing'],
      reviewCount: 2,
      // Deliberately a whole number of meters under 1km (never a decimal
      // km value like "1.2") -- a decimal would coincidentally match
      // `expectNoConfidenceValueRendered`'s `\b[01]\.\d{1,3}\b` pattern,
      // which is meant to catch a raw confidence score, not a distance.
      distanceMeters: 500,
      isClaimed: true,
    );

    testWidgets(
      'a `matched` search request renders the shared ranked-results widget '
      '(AC4)',
      (tester) async {
        final fakeRepository = FakeConversationRepository(
          startResult: const ConversationSession(
            id: 'session-1',
            status: ConversationSessionStatus.completed,
            messages: [],
            searchRequestId: 'search-request-1',
          ),
          getSearchRequestResultsResult: const SearchRequestResult(
            status: SearchRequestResultStatus.matched,
            matchedProviders: [matchedProvider],
          ),
        );

        await pumpConversationScreen(
          tester,
          child: const AiConversationScreen(),
          overrides: [
            conversationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await startSession(tester);

        expect(
          find.byKey(const ValueKey('ai-conversation-results-heading')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('ranked-provider-results-list')),
          findsOneWidget,
        );
        expect(find.text('Al Noor Plumbing Services LLC'), findsOneWidget);
        expect(
          find.byKey(const ValueKey('ai-conversation-completion-title')),
          findsNothing,
        );
        expectNoConfidenceValueRendered(tester);
        expectNoForbiddenWordsRendered(tester);
      },
    );

    testWidgets(
      'tapping a matched provider card navigates to the Provider Profile '
      "screen with the session's real, already-known searchRequestId "
      '(CON-001, Decision 4)',
      (tester) async {
        final fakeRepository = FakeConversationRepository(
          startResult: const ConversationSession(
            id: 'session-1',
            status: ConversationSessionStatus.completed,
            messages: [],
            searchRequestId: 'search-request-1',
          ),
          getSearchRequestResultsResult: const SearchRequestResult(
            status: SearchRequestResultStatus.matched,
            matchedProviders: [matchedProvider],
          ),
        );

        await pumpConversationScreen(
          tester,
          child: const AiConversationScreen(),
          overrides: [
            conversationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await startSession(tester);

        await tester.tap(find.text('Al Noor Plumbing Services LLC'));
        await tester.pumpAndSettle();

        expect(
          find.text('provider-profile-stub-provider-1-search-request-1'),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'an `unmatched` search request (zero matched providers) shows a '
      'distinct empty state, never the plain completion banner nor a '
      "forbidden term (AC3)",
      (tester) async {
        final fakeRepository = FakeConversationRepository(
          startResult: const ConversationSession(
            id: 'session-1',
            status: ConversationSessionStatus.completed,
            messages: [],
            searchRequestId: 'search-request-1',
          ),
          getSearchRequestResultsResult: const SearchRequestResult(
            status: SearchRequestResultStatus.unmatched,
          ),
        );

        await pumpConversationScreen(
          tester,
          child: const AiConversationScreen(),
          overrides: [
            conversationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await startSession(tester);

        expect(
          find.byKey(const ValueKey('ai-conversation-no-matches-message')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('ai-conversation-completion-title')),
          findsNothing,
        );
        expectNoConfidenceValueRendered(tester);
        expectNoForbiddenWordsRendered(tester);
      },
    );

    testWidgets(
      'a `pending_manual_match` session keeps showing the existing waiting '
      "copy verbatim, polls, and transitions once the result resolves "
      '(AC2/AC3/AC4)',
      (tester) async {
        final fakeRepository = FakeConversationRepository(
          startResult: const ConversationSession(
            id: 'session-1',
            status: ConversationSessionStatus.routedToAdmin,
            messages: [],
            searchRequestId: 'search-request-1',
          ),
          getSearchRequestResultsSequence: const [
            SearchRequestResult(
              status: SearchRequestResultStatus.pendingManualMatch,
            ),
            SearchRequestResult(
              status: SearchRequestResultStatus.matched,
              matchedProviders: [matchedProvider],
            ),
          ],
        );

        await pumpConversationScreen(
          tester,
          child: const AiConversationScreen(),
          overrides: [
            conversationRepositoryProvider.overrideWithValue(fakeRepository),
            conversationResultsPollIntervalProvider.overrideWithValue(
              const Duration(milliseconds: 50),
            ),
          ],
        );

        // Deliberately zero-duration `pump()` calls here, never
        // `pumpAndSettle()` -- with a 50ms poll interval,
        // `pumpAndSettle()`'s own ~100ms-per-step advance would fire the
        // poll timer itself and race straight past the "still pending"
        // state this checkpoint means to observe.
        await tester.enterText(
          find.byKey(const ValueKey('ai-conversation-compose-field')),
          'My kitchen sink is leaking',
        );
        await tester.pump();
        await tester.tap(
          find.byKey(const ValueKey('ai-conversation-start-button')),
        );
        await tester.pump();
        await tester.pump();

        // Still pending -- the exact same honest waiting copy AI-001
        // already ships, never a new "waiting" string.
        expect(
          find.byKey(const ValueKey('ai-conversation-completion-title')),
          findsOneWidget,
        );
        expect(
          find.text("Thanks -- we're finding matches for you"),
          findsOneWidget,
        );
        expect(fakeRepository.getSearchRequestResultsCallCount, 1);
        expectNoForbiddenWordsRendered(tester);

        // The next poll tick resolves to `matched`.
        await tester.pump(const Duration(milliseconds: 60));
        await tester.pumpAndSettle();

        expect(fakeRepository.getSearchRequestResultsCallCount, 2);
        expect(
          find.byKey(const ValueKey('ai-conversation-results-heading')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('ai-conversation-completion-title')),
          findsNothing,
        );
        expectNoConfidenceValueRendered(tester);
        expectNoForbiddenWordsRendered(tester);
      },
    );
  });
}
