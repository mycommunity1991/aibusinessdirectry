import 'package:ai_marketplace_app/shared/data/current_provider_type_repository.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [CurrentProviderTypeRepository] -- no real
/// Dio/network calls are ever made. Mirrors
/// `test/features/provider/fakes/fake_provider_repository.dart`'s pattern,
/// scoped to just returning a [ProviderType]?.
class FakeCurrentProviderTypeRepository extends CurrentProviderTypeRepository {
  FakeCurrentProviderTypeRepository({this.providerType}) : super(Dio());

  /// The value `getMyProviderType` returns -- `null` mirrors the "no
  /// provider yet" / unparseable-response case.
  final ProviderType? providerType;

  int getMyProviderTypeCallCount = 0;

  @override
  Future<ProviderType?> getMyProviderType() async {
    getMyProviderTypeCallCount++;
    return providerType;
  }
}
