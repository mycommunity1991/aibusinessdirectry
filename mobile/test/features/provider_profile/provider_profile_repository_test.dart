import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review_exception.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// Regression coverage for `ProviderProfileRepository.submitReview`'s
/// HTTP-error mapping (REV-002, AC1/AC2/Decision 5) --
/// `POST /contact-views/{contact_view_id}/review`.
void main() {
  Dio dioThatAlwaysReturns({int? statusCode, Object? data}) {
    final dio = Dio(BaseOptions());
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (statusCode == null) {
            handler.reject(
              DioException(
                requestOptions: options,
                type: DioExceptionType.connectionError,
              ),
            );
            return;
          }
          handler.reject(
            DioException(
              requestOptions: options,
              type: DioExceptionType.badResponse,
              response: Response(
                requestOptions: options,
                statusCode: statusCode,
                data: data,
              ),
            ),
          );
        },
      ),
    );
    return dio;
  }

  group('submitReview error mapping', () {
    test('no response at all (connectivity failure) maps to network', () async {
      final repository = ProviderProfileRepository(dioThatAlwaysReturns());

      ReviewException? caught;
      try {
        await repository.submitReview(
          contactViewId: 'contact-view-1',
          rating: 5,
        );
      } on ReviewException catch (error) {
        caught = error;
      }

      expect(caught?.type, ReviewErrorType.network);
    });

    test(
      '404 (contact_view_id not found/not owned) maps to notFound '
      '(Decision 5 -- reuses ContactViewNotFoundError\'s existing shape)',
      () async {
        final repository = ProviderProfileRepository(
          dioThatAlwaysReturns(
            statusCode: 404,
            data: {'success': false, 'message': 'Not found', 'errors': []},
          ),
        );

        ReviewException? caught;
        try {
          await repository.submitReview(
            contactViewId: 'contact-view-1',
            rating: 5,
          );
        } on ReviewException catch (error) {
          caught = error;
        }

        expect(caught?.type, ReviewErrorType.notFound);
      },
    );

    test(
      '409 (either ReviewAnchorNotVerifiedError or ReviewAlreadyExistsError '
      '-- the backend\'s ErrorResponse carries no distinguishing field, '
      'backend/app/shared/schemas/response.py) maps to anchorNotVerified',
      () async {
        final repository = ProviderProfileRepository(
          dioThatAlwaysReturns(
            statusCode: 409,
            data: {
              'success': false,
              'message': 'A review was already submitted.',
              'errors': [],
            },
          ),
        );

        ReviewException? caught;
        try {
          await repository.submitReview(
            contactViewId: 'contact-view-1',
            rating: 5,
          );
        } on ReviewException catch (error) {
          caught = error;
        }

        expect(caught?.type, ReviewErrorType.anchorNotVerified);
      },
    );

    test('an unrecognized status code (e.g. 500) maps to unknown', () async {
      final repository = ProviderProfileRepository(
        dioThatAlwaysReturns(
          statusCode: 500,
          data: {'success': false, 'message': 'Internal error', 'errors': []},
        ),
      );

      ReviewException? caught;
      try {
        await repository.submitReview(
          contactViewId: 'contact-view-1',
          rating: 5,
        );
      } on ReviewException catch (error) {
        caught = error;
      }

      expect(caught?.type, ReviewErrorType.unknown);
    });

    test('comment is omitted from the request body entirely when null, '
        'never sent as a literal JSON null', () async {
      Map<String, dynamic>? capturedData;
      final dio = Dio(BaseOptions());
      dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) {
            capturedData = options.data as Map<String, dynamic>;
            handler.resolve(
              Response(
                requestOptions: options,
                statusCode: 201,
                data: {
                  'success': true,
                  'message': 'Review submitted.',
                  'data': {
                    'id': 'review-1',
                    'contact_view_id': 'contact-view-1',
                    'provider_id': 'provider-1',
                    'rating': 5,
                    'comment': null,
                    'created_at': '2024-01-01T00:00:00Z',
                  },
                },
              ),
            );
          },
        ),
      );
      final repository = ProviderProfileRepository(dio);

      final review = await repository.submitReview(
        contactViewId: 'contact-view-1',
        rating: 5,
      );

      expect(capturedData!.containsKey('comment'), isFalse);
      expect(review, isA<Review>());
      expect(review.rating, 5);
      expect(review.comment, isNull);
    });
  });
}
