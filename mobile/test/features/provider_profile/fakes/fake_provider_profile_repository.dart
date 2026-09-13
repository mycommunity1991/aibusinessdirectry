import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_reveal.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag_exception.dart';
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
    this.outcomeTag,
    this.submitOutcomeTagError,
  }) : super(Dio());

  /// The [ProviderProfile] a successful `getProviderProfile` call returns.
  final ProviderProfile? profile;

  /// The failure `getProviderProfile` throws, if any.
  final ProviderProfileException? getProviderProfileError;

  /// The [ContactReveal] a successful `createContactView` call returns.
  final ContactReveal? contactReveal;

  /// The failure `createContactView` throws, if any.
  final ContactException? createContactViewError;

  /// The [OutcomeTag] a successful `submitOutcomeTag` call returns.
  final OutcomeTag? outcomeTag;

  /// The failure `submitOutcomeTag` throws, if any.
  final OutcomeTagException? submitOutcomeTagError;

  int getProviderProfileCallCount = 0;
  int createContactViewCallCount = 0;
  int submitOutcomeTagCallCount = 0;

  String? lastGetProviderProfileId;
  ({String providerId, String? searchRequestId})? lastCreateContactViewArgs;
  ({String contactViewId, bool hired})? lastSubmitOutcomeTagArgs;

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

  @override
  Future<OutcomeTag> submitOutcomeTag({
    required String contactViewId,
    required bool hired,
  }) async {
    submitOutcomeTagCallCount++;
    lastSubmitOutcomeTagArgs = (contactViewId: contactViewId, hired: hired);
    if (submitOutcomeTagError != null) {
      throw submitOutcomeTagError!;
    }
    return outcomeTag!;
  }
}
