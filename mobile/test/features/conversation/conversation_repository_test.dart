import 'package:ai_marketplace_app/features/conversation/data/conversation_repository.dart';
import 'package:ai_marketplace_app/features/conversation/domain/models/conversation_exception.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// Regression coverage for `ConversationRepository`'s HTTP-error mapping
/// (AI-001) -- specifically, whether every real backend 422 shape is mapped
/// to the *right* [ConversationErrorType], not just *a* recognized one.
///
/// `backend/app/modules/conversation/schemas.py` (`StartConversationRequest`,
/// `SubmitTurnRequest`) enforces plain Pydantic field constraints
/// (`max_length=2000` on the opening message and on free-text answers) that
/// FastAPI reports as a 422 `RequestValidationError` -- a completely
/// different failure from `AnswerNotRevisableError` (also a 422, but only
/// ever raised by `PATCH /conversations/{id}/answers/{message_id}`,
/// `backend/app/core/exceptions/exceptions.py:535`). Both arrive at the
/// mobile client as an HTTP 422, but they mean different things on
/// different endpoints.
void main() {
  group('ConversationRepository 422 mapping', () {
    Dio dioThatAlwaysReturns422() {
      final dio = Dio(BaseOptions());
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            handler.reject(
              DioException(
                requestOptions: options,
                type: DioExceptionType.badResponse,
                response: Response(
                  requestOptions: options,
                  statusCode: 422,
                  data: {
                    'success': false,
                    'message': 'Validation failed',
                    'errors': [
                      {
                        'field': 'message',
                        'message': 'ensure this value has at most 2000 characters',
                      },
                    ],
                  },
                ),
              ),
            );
          },
        ),
      );
      return dio;
    }

    test(
      'a 422 from POST /conversations (a request-validation failure, e.g. '
      'an opening message over the 2000-char limit) must never be reported '
      'as "answer can no longer be edited" -- that endpoint never revises '
      'any answer at all',
      () async {
        final repository = ConversationRepository(dioThatAlwaysReturns422());

        ConversationException? caught;
        try {
          await repository.start('x' * 2001);
        } on ConversationException catch (error) {
          caught = error;
        }

        expect(
          caught,
          isNotNull,
          reason: 'expected the 422 to surface as a ConversationException',
        );
        expect(
          caught!.type,
          isNot(ConversationErrorType.answerNotRevisable),
          reason:
              'BUG: ConversationRepository._mapError maps *every* 422, on '
              'every endpoint, to ConversationErrorType.answerNotRevisable '
              '("That answer can no longer be edited."). A 422 from '
              'POST /conversations is a plain body-validation failure '
              '(StartConversationRequest.message max_length=2000) with no '
              'message_id/revise semantics whatsoever -- the mobile screen '
              'would show a nonsensical "answer can no longer be edited" '
              'message to a customer who was simply starting a brand-new '
              'conversation with a long description.',
        );
      },
    );

    test(
      'a 422 from POST /conversations/{id}/messages (a request-validation '
      'failure, e.g. an over-limit free-text answer) must never be reported '
      'as "answer can no longer be edited" either -- that is not the '
      'revise-answer endpoint',
      () async {
        final repository = ConversationRepository(dioThatAlwaysReturns422());

        ConversationException? caught;
        try {
          await repository.submitTurn(
            sessionId: 'session-1',
            content: 'x' * 2001,
          );
        } on ConversationException catch (error) {
          caught = error;
        }

        expect(caught, isNotNull);
        expect(
          caught!.type,
          isNot(ConversationErrorType.answerNotRevisable),
          reason:
              'Same bug as above, on POST /conversations/{id}/messages: a '
              'plain SubmitTurnRequest.content max_length validation '
              'failure is not the same thing as PATCH .../answers/{id} '
              'rejecting a message_id that cannot be revised.',
        );
      },
    );
  });
}
