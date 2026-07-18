import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_config.dart';

/// Thin Dio wrapper configured against the project's `/api/v1` prefix.
///
/// Every feature repository should depend on this (via [apiClientProvider])
/// rather than constructing its own [Dio] instance — this is the single
/// place base URL, timeouts, and default headers are configured.
class ApiClient {
  ApiClient({Dio? dio}) : dio = dio ?? _createDio();

  final Dio dio;

  static Dio _createDio() {
    return Dio(
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
  }
}

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
