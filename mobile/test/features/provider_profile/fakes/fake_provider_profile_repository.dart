import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_reveal.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_exception.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [ProviderProfileRepository] -- no real
/// Dio/network calls are ever made. Mirrors `fake_search_repository.dart`/
/// `fake_claim_repository.dart`'s pattern.
class FakeProviderProfileRepository extends ProviderProfileRepository {
  FakeProviderProfileRepository({
    this.profile,
    this.getProviderProfileError,
    this.contactReveal,
    this.createContactViewError,
  }) : super(Dio());

  /// The [ProviderProfile] a successful `getProviderProfile` call returns.
  final ProviderProfile? profile;

  /// The failure `getProviderProfile` throws, if any.
  final ProviderProfileException? getProviderProfileError;

  /// The [ContactReveal] a successful `createContactView` call returns.
  final ContactReveal? contactReveal;

  /// The failure `createContactView` throws, if any.
  final ContactException? createContactViewError;

  int getProviderProfileCallCount = 0;
  int createContactViewCallCount = 0;

  String? lastGetProviderProfileId;
  ({String providerId, String? searchRequestId})? lastCreateContactViewArgs;

  @override
  Future<ProviderProfile> getProviderProfile(String providerId) async {
    getProviderProfileCallCount++;
    lastGetProviderProfileId = providerId;
    if (getProviderProfileError != null) {
      throw getProviderProfileError!;
    }
    return profile!;
  }

  @override
  Future<ContactReveal> createContactView({
    required String providerId,
    String? searchRequestId,
  }) async {
    createContactViewCallCount++;
    lastCreateContactViewArgs = (
      providerId: providerId,
      searchRequestId: searchRequestId,
    );
    if (createContactViewError != null) {
      throw createContactViewError!;
    }
    return contactReveal!;
  }
}
