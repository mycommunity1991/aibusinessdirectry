import 'package:ai_marketplace_app/features/conversation/data/conversation_repository.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_exception.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_message.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_session.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [ConversationRepository] -- no real
/// Dio/network calls are ever made. Mirrors `fake_claim_repository.dart`'s
/// pattern.
class FakeConversationRepository extends ConversationRepository {
  FakeConversationRepository({
    this.startResult,
    this.startError,
    this.submitTurnResult,
    this.submitTurnError,
    this.reviseAnswerResult,
    this.reviseAnswerError,
    this.getSessionResult,
    this.getSessionError,
    this.gate,
  }) : super(Dio());

  /// The [ConversationSession] a successful `start` call returns.
  ConversationSession? startResult;

  /// The failure `start` throws, if any.
  ConversationException? startError;

  /// The [ConversationSession] a successful `submitTurn` call returns.
  ConversationSession? submitTurnResult;

  /// The failure `submitTurn` throws, if any.
  ConversationException? submitTurnError;

  /// The [ConversationSession] a successful `reviseAnswer` call returns.
  ConversationSession? reviseAnswerResult;

  /// The failure `reviseAnswer` throws, if any.
  ConversationException? reviseAnswerError;

  /// The [ConversationSession] a successful `getSession` call returns.
  ConversationSession? getSessionResult;

  /// The failure `getSession` throws, if any.
  ConversationException? getSessionError;

  /// If set, every call awaits this future before resolving -- lets tests
  /// hold a turn "in flight" indefinitely to exercise the >3s/>8s latency
  /// tiers deterministically (AC6/AC7), independent of the interim
  /// rule-based client's real (near-instant) response time.
  Future<void>? gate;

  int startCallCount = 0;
  int submitTurnCallCount = 0;
  int reviseAnswerCallCount = 0;
  int getSessionCallCount = 0;

  String? lastStartMessage;
  ({String sessionId, String? content, String? selectedOption})?
  lastSubmitTurnArgs;
  ({String sessionId, String messageId, String content})? lastReviseAnswerArgs;
  String? lastGetSessionId;

  static final _defaultSession = ConversationSession(
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
    ],
  );

  @override
  Future<ConversationSession> start(String message) async {
    startCallCount++;
    lastStartMessage = message;
    if (gate != null) await gate;
    if (startError != null) throw startError!;
    return startResult ?? _defaultSession;
  }

  @override
  Future<ConversationSession> submitTurn({
    required String sessionId,
    String? content,
    String? selectedOption,
  }) async {
    submitTurnCallCount++;
    lastSubmitTurnArgs = (
      sessionId: sessionId,
      content: content,
      selectedOption: selectedOption,
    );
    if (gate != null) await gate;
    if (submitTurnError != null) throw submitTurnError!;
    return submitTurnResult ?? _defaultSession;
  }

  @override
  Future<ConversationSession> reviseAnswer({
    required String sessionId,
    required String messageId,
    required String content,
  }) async {
    reviseAnswerCallCount++;
    lastReviseAnswerArgs = (
      sessionId: sessionId,
      messageId: messageId,
      content: content,
    );
    if (gate != null) await gate;
    if (reviseAnswerError != null) throw reviseAnswerError!;
    return reviseAnswerResult ?? _defaultSession;
  }

  @override
  Future<ConversationSession> getSession(String sessionId) async {
    getSessionCallCount++;
    lastGetSessionId = sessionId;
    if (gate != null) await gate;
    if (getSessionError != null) throw getSessionError!;
    return getSessionResult ?? _defaultSession;
  }
}
