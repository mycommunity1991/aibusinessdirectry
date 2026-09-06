import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/state/language_controller.dart';

/// Attaches `Accept-Language` to every outgoing request from the user's
/// explicit in-app language choice ([languageControllerProvider], S-02).
///
/// The backend derives a new customer's default `customer_preferences.language`
/// from this header at registration time (AC3, `Plan_S03_CUS-001.md`
/// Decision 3), and every endpoint benefits from it being sent consistently
/// rather than one-off per repository. Deliberately sends **no** header at
/// all until the user has made an explicit choice — the backend's own
/// fallback (English) then matches "no signal yet" rather than this client
/// asserting a language the user never actually picked.
///
/// This is the same kind of deliberate, documented exception to
/// "`core/` never depends on a `features/` module" that
/// `auth_interceptor.dart` already is — every authenticated/localized
/// request needs to read shared app state, and reimplementing this per
/// repository would violate "no duplicate code."
class AcceptLanguageInterceptor extends Interceptor {
  AcceptLanguageInterceptor(this._ref);

  final Ref _ref;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final locale = _ref.read(languageControllerProvider).valueOrNull;
    if (locale != null) {
      options.headers['Accept-Language'] = locale.languageCode;
    }
    handler.next(options);
  }
}
