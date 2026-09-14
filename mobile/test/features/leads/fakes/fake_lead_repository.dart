import 'package:ai_marketplace_app/features/leads/data/lead_repository.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead_exception.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [LeadRepository] -- no real Dio/network calls
/// are ever made. Mirrors `fake_search_repository.dart`/
/// `fake_provider_repository.dart`'s pattern.
///
/// [pages] lets a test pre-seed more than one page of leads -- page `n`
/// (1-indexed) is served from `pages[n - 1]`, and [totalItems] defaults to
/// the flattened total across every page supplied so `hasMore` derives
/// correctly without a test having to compute it by hand.
class FakeLeadRepository extends LeadRepository {
  FakeLeadRepository({
    List<List<Lead>>? pages,
    int? totalItems,
    this.listMyLeadsError,
  }) : _pages = pages ?? const [[]],
       _totalItems =
           totalItems ??
           (pages ?? const [[]]).fold(0, (sum, page) => sum + page.length),
       super(Dio());

  final List<List<Lead>> _pages;
  final int _totalItems;

  /// The failure `listMyLeads` throws, if any.
  final LeadException? listMyLeadsError;

  int listMyLeadsCallCount = 0;

  /// The exact arguments passed to the most recent `listMyLeads` call.
  ({int page, int pageSize})? lastArgs;

  @override
  Future<LeadsPage> listMyLeads({int page = 1, int pageSize = 20}) async {
    listMyLeadsCallCount++;
    lastArgs = (page: page, pageSize: pageSize);
    if (listMyLeadsError != null) {
      throw listMyLeadsError!;
    }
    final leads = page >= 1 && page <= _pages.length
        ? _pages[page - 1]
        : <Lead>[];
    return (leads: List.of(leads), totalItems: _totalItems);
  }
}
