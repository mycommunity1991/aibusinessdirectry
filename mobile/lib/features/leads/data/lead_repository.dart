import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/models/lead.dart';
import '../domain/models/lead_exception.dart';

/// One page of `GET /providers/me/leads` results, plus the backend's
/// `PaginationMeta.total_items` -- a plain record (mirrors
/// `SearchProvidersPage`'s own typedef-record pattern,
/// `features/search/data/search_repository.dart`) rather than a new named
/// class, since it carries nothing beyond these two values.
typedef LeadsPage = ({List<Lead> leads, int totalItems});

/// Wraps `GET /providers/me/leads` (LEAD-001,
/// `backend/app/modules/contact/provider_lead_api.py`).
///
/// Every failure is mapped to a plain-language [LeadException] -- callers
/// (`LeadsController`/`LeadsScreen`) never see a [DioException], an HTTP
/// status code, or a backend error identifier, following the same
/// convention as `provider_repository.dart`/`search_repository.dart`.
class LeadRepository {
  LeadRepository(this._dio);

  final Dio _dio;

  /// Lists the caller's own leads (Contact Views + resolved outcome/
  /// category context), most-recent-first (AC2) -- ownership is enforced
  /// entirely server-side (AC4); this method never accepts or sends a
  /// provider id.
  Future<LeadsPage> listMyLeads({int page = 1, int pageSize = 20}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/providers/me/leads',
        queryParameters: {'page': page, 'page_size': pageSize},
      );
      final data = response.data?['data'] as List<dynamic>?;
      if (data == null) {
        throw const LeadException(type: LeadErrorType.unknown);
      }
      final leads = data
          .cast<Map<String, dynamic>>()
          .map(Lead.fromJson)
          .toList();
      final pagination = response.data?['pagination'] as Map<String, dynamic>?;
      final totalItems =
          (pagination?['total_items'] as num?)?.toInt() ?? leads.length;
      return (leads: leads, totalItems: totalItems);
    } on DioException catch (error) {
      throw _mapNotFoundOnlyError(error);
    }
  }

  LeadException _mapNotFoundOnlyError(DioException error) {
    if (error.response == null) {
      return const LeadException(type: LeadErrorType.network);
    }
    if (error.response!.statusCode == 404) {
      return const LeadException(type: LeadErrorType.notFound);
    }
    return const LeadException(type: LeadErrorType.unknown);
  }
}

final leadRepositoryProvider = Provider<LeadRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LeadRepository(apiClient.dio);
});
