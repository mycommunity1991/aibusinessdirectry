import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/create_provider_request.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider.dart'
    as domain;
import 'package:ai_marketplace_app/features/provider/domain/models/provider_exception.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider_type.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [ProviderRepository] — no real Dio/network
/// calls are ever made. Mirrors `fake_saved_address_repository.dart`'s
/// pattern.
class FakeProviderRepository extends ProviderRepository {
  FakeProviderRepository({
    domain.Provider? existingProvider,
    this.getMyProviderError,
    this.createProviderError,
  }) : _provider = existingProvider,
       super(Dio());

  domain.Provider? _provider;

  /// The failure `getMyProvider` throws, if any (never used for the plain
  /// "no provider yet" case -- that's represented by `_provider == null`
  /// returning `null`, not an exception, per Decision 9).
  final ProviderException? getMyProviderError;

  /// The failure `createProvider` throws, if any.
  final ProviderException? createProviderError;

  int getMyProviderCallCount = 0;
  int createProviderCallCount = 0;

  /// The exact request passed to the most recent `createProvider` call —
  /// lets a test assert precisely what was submitted without inspecting a
  /// raw JSON payload.
  CreateProviderRequest? lastCreateRequest;

  @override
  Future<domain.Provider?> getMyProvider() async {
    getMyProviderCallCount++;
    if (getMyProviderError != null) {
      throw getMyProviderError!;
    }
    return _provider;
  }

  @override
  Future<domain.Provider> createProvider(CreateProviderRequest request) async {
    createProviderCallCount++;
    lastCreateRequest = request;
    if (createProviderError != null) {
      throw createProviderError!;
    }
    if (_provider != null) {
      // Mirrors the real backend's one-provider-per-account enforcement
      // (AC8/AC10) so the flow test can exercise it without a separate
      // constructor flag.
      throw const ProviderException(type: ProviderErrorType.alreadyExists);
    }
    final created = domain.Provider(
      id: 'provider-1',
      providerType: request.providerType,
      displayName: request.displayName,
      phoneCountryCode: request.phoneCountryCode,
      phoneNumber: request.phoneNumber,
      whatsappNumber: request.whatsappNumber,
      categoryLabel: request.categoryLabel,
      description: request.description,
      slug: 'test-provider-slug',
      verificationStatus: 'pending',
      isDiscoverable: false,
      countryCode:
          request.businessDetails?.countryCode ??
          request.freelancerDetails?.countryCode ??
          'AE',
      businessProfile: request.businessDetails == null
          ? null
          : domain.BusinessProfile(
              addressLine: request.businessDetails!.addressLine,
              city: request.businessDetails!.city,
              region: request.businessDetails!.region,
              latitude: request.businessDetails!.latitude,
              longitude: request.businessDetails!.longitude,
              operatingHours: request.businessDetails!.operatingHours,
              deliveryRadiusMeters:
                  request.businessDetails!.deliveryRadiusMeters,
              tradeLicenseNumber: request.businessDetails!.tradeLicenseNumber,
            ),
      freelancerProfile: request.freelancerDetails == null
          ? null
          : domain.FreelancerProfile(
              baseLatitude: request.freelancerDetails!.baseLatitude,
              baseLongitude: request.freelancerDetails!.baseLongitude,
              serviceRadiusMeters:
                  request.freelancerDetails!.serviceRadiusMeters,
              skills: request.freelancerDetails!.skills,
              yearsExperience: request.freelancerDetails!.yearsExperience,
            ),
    );
    _provider = created;
    return created;
  }
}

/// A representative Business provider, for tests that need an
/// [FakeProviderRepository] pre-seeded with an existing listing.
final fakeExistingBusinessProvider = domain.Provider(
  id: 'provider-existing',
  providerType: ProviderType.business,
  displayName: 'Existing Business',
  phoneCountryCode: '+971',
  phoneNumber: '501234567',
  categoryLabel: 'Plumbing',
  slug: 'existing-business',
  verificationStatus: 'pending',
  isDiscoverable: false,
  countryCode: 'AE',
  businessProfile: const domain.BusinessProfile(
    addressLine: 'Villa 1, Al Wasl Road',
    latitude: 25.2048,
    longitude: 55.2708,
  ),
);
