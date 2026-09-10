import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/conversation_exception.dart';
import '../domain/models/conversation_session.dart';

/// Wraps the customer-facing AI-conversation endpoints (AI-001,
/// `backend/app/modules/conversation/api.py`, mounted at `/conversations`).
///
/// Every failure is mapped to a plain-language [ConversationException] --
/// callers (the state controller/screen) never see a [DioException], an
/// HTTP status code, or a backend error identifier, following the same
/// convention as `claim_repository.dart`/`auth_repository.dart`.
class ConversationRepository {
  ConversationRepository(this._dio);

  final Dio _dio;

  /// `POST /conversations` (AC1) -- creates the session, its first
  /// customer message, and the first AI turn, in one call. A still-active
  /// prior session belonging to the caller is marked `abandoned` first by
  /// the backend (Decision 5) -- the mobile client never manages that
  /// itself.
  Future<ConversationSession> start(String message) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/conversations',
        data: {'message': message},
      );
      return _sessionFromResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// `POST /conversations/{sessionId}/messages` (AC4/AC6/AC7). Exactly one
  /// of [content] (free text) or [selectedOption] (a quick-reply chip
  /// choice) must be provided, mirroring `SubmitTurnRequest`'s own
  /// contract.
  Future<ConversationSession> submitTurn({
    required String sessionId,
    String? content,
    String? selectedOption,
  }) async {
    assert(
      (content == null) != (selectedOption == null),
      'Provide exactly one of content or selectedOption.',
    );
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/conversations/$sessionId/messages',
        data: {'content': ?content, 'selected_option': ?selectedOption},
      );
      return _sessionFromResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// `PATCH /conversations/{sessionId}/answers/{messageId}` (AC8, Decision
  /// 5) -- updates a prior customer answer; the backend truncates every
  /// later message in the session and regenerates the next turn fresh from
  /// the now-shorter history. From this client's perspective the chat
  /// simply continues from the edited point, never a restart.
  Future<ConversationSession> reviseAnswer({
    required String sessionId,
    required String messageId,
    required String content,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/conversations/$sessionId/answers/$messageId',
        data: {'content': content},
      );
      return _sessionFromResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// `GET /conversations/{sessionId}` -- resumes a session after an app
  /// restart, or reviews its transcript.
  Future<ConversationSession> getSession(String sessionId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/conversations/$sessionId',
      );
      return _sessionFromResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  ConversationSession _sessionFromResponse(
    Response<Map<String, dynamic>> response,
  ) {
    final data = response.data?['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw const ConversationException(type: ConversationErrorType.unknown);
    }
    return ConversationSession.fromJson(data);
  }

  ConversationException _mapError(DioException error) {
    if (error.response == null) {
      return const ConversationException(type: ConversationErrorType.network);
    }
    return switch (error.response!.statusCode) {
      404 => const ConversationException(
        type: ConversationErrorType.sessionNotFound,
      ),
      409 => const ConversationException(
        type: ConversationErrorType.sessionNotActive,
      ),
      422 => const ConversationException(
        type: ConversationErrorType.answerNotRevisable,
      ),
      _ => const ConversationException(type: ConversationErrorType.unknown),
    };
  }
}

final conversationRepositoryProvider = Provider<ConversationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ConversationRepository(apiClient.dio);
});
