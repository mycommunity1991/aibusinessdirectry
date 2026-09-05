import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/domain/models/auth_token.dart';
import '../../features/auth/state/auth_session_controller.dart';
import 'api_config.dart';

/// Attaches `Authorization: Bearer <access_token>` (from the current
/// in-memory session) to every outgoing request, and performs one silent
/// refresh-and-retry (`POST /auth/refresh`) on a `401` before giving up
/// (AUTH-003, Plan Decision 12) — so a short-lived access token expiring
/// mid-session never forces the user back to the auth flow.
///
/// This is the one deliberate exception to "`core/` never depends on a
/// `features/` module": every authenticated request needs to read the
/// current session, and every future authenticated feature reuses this
/// same interceptor, so it lives once here rather than being reimplemented
/// per repository.
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._ref)
    : _refreshDio = Dio(
        BaseOptions(
          baseUrl: ApiConfig.baseUrl,
          connectTimeout: ApiConfig.connectTimeout,
          receiveTimeout: ApiConfig.receiveTimeout,
          headers: const {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        ),
      );

  final Ref _ref;

  /// A separate, interceptor-free [Dio] instance used only for the
  /// refresh-and-retry call itself — reusing the intercepted client here
  /// would recurse back into this same interceptor.
  final Dio _refreshDio;

  static const _retriedFlagKey = 'auth_interceptor_retried';

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final accessToken = _ref.read(authSessionProvider)?.accessToken;
    if (accessToken != null) {
      options.headers['Authorization'] = 'Bearer $accessToken';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final requestOptions = err.requestOptions;
    final alreadyRetried = requestOptions.extra[_retriedFlagKey] == true;
    final refreshToken = _ref.read(authSessionProvider)?.refreshToken;

    if (err.response?.statusCode != 401 ||
        alreadyRetried ||
        refreshToken == null) {
      handler.next(err);
      return;
    }

    try {
      final refreshResponse = await _refreshDio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final data = refreshResponse.data?['data'] as Map<String, dynamic>?;
      if (data == null) {
        handler.next(err);
        return;
      }

      final newSession = AuthToken.fromJson(data);
      await _ref.read(authSessionControllerProvider).setSession(newSession);

      requestOptions.extra[_retriedFlagKey] = true;
      requestOptions.headers['Authorization'] =
          'Bearer ${newSession.accessToken}';
      final retryResponse = await _refreshDio.fetch<dynamic>(requestOptions);
      handler.resolve(retryResponse);
    } on DioException {
      // The refresh token itself is no longer valid (expired/revoked) —
      // clear the dead session locally rather than leaving the app stuck
      // silently retrying it on every subsequent request.
      await _ref.read(authSessionControllerProvider).clear();
      handler.next(err);
    }
  }
}
