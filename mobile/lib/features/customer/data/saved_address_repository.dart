import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/saved_address.dart';
import '../domain/models/saved_address_exception.dart';

/// Wraps `GET`/`POST /customers/me/addresses` and
/// `PATCH`/`DELETE /customers/me/addresses/{address_id}` (CUS-002,
/// `backend/app/modules/customer/api.py`).
///
/// Every failure is mapped to a plain-language [SavedAddressException] —
/// callers (the state controllers/screens) never see a [DioException], an
/// HTTP status code, or a backend error identifier, following the same
/// convention as `customer_repository.dart`.
class SavedAddressRepository {
  SavedAddressRepository(this._dio);

  final Dio _dio;

  /// Lists all of the caller's own active saved addresses (AC6). Never
  /// includes another customer's addresses (AC8) — enforced server-side.
  Future<List<SavedAddress>> list() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/customers/me/addresses',
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const SavedAddressException(type: SavedAddressErrorType.unknown);
      }
      return data
          .cast<Map<String, dynamic>>()
          .map(SavedAddress.fromJson)
          .toList();
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Creates a new saved address (AC1, AC3). Setting [isDefault] to `true`
  /// unsets any previously-default address for this customer, server-side
  /// (AC2).
  Future<SavedAddress> create({
    String? label,
    required String addressLine,
    String? city,
    String? region,
    required String countryCode,
    required double latitude,
    required double longitude,
    bool isDefault = false,
  }) async {
    final payload = <String, dynamic>{
      'label': ?label,
      'address_line': addressLine,
      'city': ?city,
      'region': ?region,
      'country_code': countryCode,
      'latitude': latitude,
      'longitude': longitude,
      'is_default': isDefault,
    };
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/customers/me/addresses',
        data: payload,
      );
      return _parseResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Partially updates one of the caller's own saved addresses (AC6) —
  /// only the fields passed here are sent, matching the backend's
  /// `exclude_unset=True` partial-update semantics. Setting [isDefault] to
  /// `true` unsets any previously-default address for this customer,
  /// server-side (AC2).
  Future<SavedAddress> update(
    String addressId, {
    String? label,
    String? addressLine,
    String? city,
    String? region,
    String? countryCode,
    double? latitude,
    double? longitude,
    bool? isDefault,
  }) async {
    final payload = <String, dynamic>{
      'label': ?label,
      'address_line': ?addressLine,
      'city': ?city,
      'region': ?region,
      'country_code': ?countryCode,
      'latitude': ?latitude,
      'longitude': ?longitude,
      'is_default': ?isDefault,
    };
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/customers/me/addresses/$addressId',
        data: payload,
      );
      return _parseResponse(response);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  /// Soft-deletes one of the caller's own saved addresses (AC6). Never
  /// auto-promotes another address to default if the deleted one was the
  /// default (AC7) — that decision belongs to the customer, driven by the
  /// mobile UI after this call resolves.
  Future<void> delete(String addressId) async {
    try {
      await _dio.delete<Map<String, dynamic>>(
        '/customers/me/addresses/$addressId',
      );
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  SavedAddress _parseResponse(Response<Map<String, dynamic>> response) {
    final data = response.data?['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw const SavedAddressException(type: SavedAddressErrorType.unknown);
    }
    return SavedAddress.fromJson(data);
  }

  SavedAddressException _mapError(DioException error) {
    if (error.response == null) {
      return const SavedAddressException(type: SavedAddressErrorType.network);
    }
    if (error.response!.statusCode == 404) {
      return const SavedAddressException(type: SavedAddressErrorType.notFound);
    }
    return const SavedAddressException(type: SavedAddressErrorType.unknown);
  }
}

final savedAddressRepositoryProvider = Provider<SavedAddressRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SavedAddressRepository(apiClient.dio);
});
