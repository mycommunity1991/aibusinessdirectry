import 'package:ai_marketplace_app/shared/data/verification_status_summary_repository.dart';
import 'package:ai_marketplace_app/shared/models/verification_status_summary.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [VerificationStatusSummaryRepository] -- no
/// real Dio/network calls are ever made. Mirrors
/// `test/features/provider/fakes/fake_provider_repository.dart`'s pattern,
/// scoped to just returning a [VerificationStatusSummary]?.
class FakeVerificationStatusSummaryRepository
    extends VerificationStatusSummaryRepository {
  FakeVerificationStatusSummaryRepository({this.summary}) : super(Dio());

  /// The value `getMyVerificationStatusSummary` returns -- `null` mirrors
  /// the "never submitted" (backend 404) case.
  final VerificationStatusSummary? summary;

  int getMyVerificationStatusSummaryCallCount = 0;

  @override
  Future<VerificationStatusSummary?> getMyVerificationStatusSummary() async {
    getMyVerificationStatusSummaryCallCount++;
    return summary;
  }
}
