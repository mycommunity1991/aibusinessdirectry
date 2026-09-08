import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../models/provider_type.dart';

/// A minimal, shared read of the caller's own `provider_type` from
/// `GET /providers/me` (`backend/app/modules/provider/api.py`) --
/// deliberately independent of `features/provider/`'s full
/// `ProviderRepository`/`Provider` domain model (`docs/AI/
/// 02_ARCHITECTURE.md`: "Features must not depend directly on each
/// other. Shared functionality belongs in shared modules.").
///
/// Any feature that only needs to know "is the caller a Business or a
/// Freelancer" -- not the full storefront listing -- should depend on
/// this instead of importing `features/provider/`.
class CurrentProviderTypeRepository {
  CurrentProviderTypeRepository(this._dio);

  final Dio _dio;

  /// Returns the caller's own `provider_type`, or `null` if they don't
  /// have a provider listing yet (backend 404) or the response couldn't
  /// be parsed (defensive only -- unreachable via the real UI, since
  /// every caller of this repository is only ever reached once a
  /// provider listing already exists).
  Future<ProviderType?> getMyProviderType() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/providers/me');
      final data = response.data?['data'] as Map<String, dynamic>?;
      final wireValue = data?['provider_type'] as String?;
      if (wireValue == null) return null;
      return ProviderType.fromWire(wireValue);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      return null;
    } on ArgumentError {
      return null;
    }
  }
}

final currentProviderTypeRepositoryProvider =
    Provider<CurrentProviderTypeRepository>((ref) {
      final apiClient = ref.watch(apiClientProvider);
      return CurrentProviderTypeRepository(apiClient.dio);
    });
