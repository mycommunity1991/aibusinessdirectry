import 'dart:io';

import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/create_provider_request.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/portfolio_photo.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/provider.dart'
    as domain;
import 'package:ai_marketplace_app/features/provider/domain/models/provider_exception.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/update_provider_request.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/weekday_availability.dart';
import 'package:dio/dio.dart';

/// Lowercase weekday keys, Monday-first — matches the backend's `Weekday`
/// wire values and `shared/widgets/weekly_hours_editor.dart`'s
/// `weeklyHoursOrderedDays` (duplicated here, not imported, so this test
/// fake stays independent of a `shared/widgets` import).
const _weekdayOrder = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
];

/// A hermetic test double for [ProviderRepository] — no real Dio/network
/// calls are ever made. Mirrors `fake_saved_address_repository.dart`'s
/// pattern. Extended for PRO-002 with the Storefront's `updateProvider`,
/// portfolio, and availability methods -- each records its own call count
/// and last-request payload so a test can assert precisely which section
/// was touched without inspecting raw JSON.
class FakeProviderRepository extends ProviderRepository {
  FakeProviderRepository({
    domain.Provider? existingProvider,
    List<PortfolioPhoto>? portfolio,
    List<WeekdayAvailability>? availability,
    this.getMyProviderError,
    this.createProviderError,
    this.updateProviderError,
    this.listPortfolioError,
    this.uploadPortfolioPhotoError,
    this.deletePortfolioPhotoError,
    this.reorderPortfolioError,
    this.getAvailabilityError,
    this.updateAvailabilityError,
  }) : _provider = existingProvider,
       _portfolio = portfolio ?? [],
       _availability =
           availability ??
           [
             for (final day in _weekdayOrder)
               WeekdayAvailability(weekday: day, isOpen: false),
           ],
       super(Dio());

  domain.Provider? _provider;
  List<PortfolioPhoto> _portfolio;
  List<WeekdayAvailability> _availability;

  /// The failure `getMyProvider` throws, if any (never used for the plain
  /// "no provider yet" case -- that's represented by `_provider == null`
  /// returning `null`, not an exception, per Decision 9).
  final ProviderException? getMyProviderError;

  /// The failure `createProvider` throws, if any.
  final ProviderException? createProviderError;

  /// The failure `updateProvider` throws, if any.
  final ProviderException? updateProviderError;

  /// The failure `listPortfolio` throws, if any.
  final ProviderException? listPortfolioError;

  /// The failure `uploadPortfolioPhoto` throws, if any.
  final ProviderException? uploadPortfolioPhotoError;

  /// The failure `deletePortfolioPhoto` throws, if any.
  final ProviderException? deletePortfolioPhotoError;

  /// The failure `reorderPortfolio` throws, if any.
  final ProviderException? reorderPortfolioError;

  /// The failure `getAvailability` throws, if any.
  final ProviderException? getAvailabilityError;

  /// The failure `updateAvailability` throws, if any.
  final ProviderException? updateAvailabilityError;

  int getMyProviderCallCount = 0;
  int createProviderCallCount = 0;
  int updateProviderCallCount = 0;
  int listPortfolioCallCount = 0;
  int uploadPortfolioPhotoCallCount = 0;
  int deletePortfolioPhotoCallCount = 0;
  int reorderPortfolioCallCount = 0;
  int getAvailabilityCallCount = 0;
  int updateAvailabilityCallCount = 0;

  /// The exact request passed to the most recent `createProvider` call —
  /// lets a test assert precisely what was submitted without inspecting a
  /// raw JSON payload.
  CreateProviderRequest? lastCreateRequest;

  /// The exact request passed to the most recent `updateProvider` call —
  /// lets a test assert that a section's Save action sent only that
  /// section's own fields (AC5).
  UpdateProviderRequest? lastUpdateProviderRequest;

  String? lastUploadedCaption;
  String? lastDeletedPhotoId;
  List<String>? lastReorderedIds;
  List<WeekdayAvailability>? lastAvailabilityUpdate;

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
      categoryLabels: [
        domain.CategoryLabel(label: request.categoryLabel, isPrimary: true),
      ],
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

  @override
  Future<domain.Provider> updateProvider(UpdateProviderRequest request) async {
    updateProviderCallCount++;
    lastUpdateProviderRequest = request;
    if (updateProviderError != null) {
      throw updateProviderError!;
    }
    final current = _provider;
    if (current == null) {
      throw const ProviderException(type: ProviderErrorType.notFound);
    }
    final updatedBusiness = request.businessDetails == null
        ? current.businessProfile
        : domain.BusinessProfile(
            addressLine:
                request.businessDetails!.addressLine ??
                current.businessProfile?.addressLine ??
                '',
            city:
                request.businessDetails!.city ?? current.businessProfile?.city,
            region:
                request.businessDetails!.region ??
                current.businessProfile?.region,
            latitude:
                request.businessDetails!.latitude ??
                current.businessProfile?.latitude ??
                0,
            longitude:
                request.businessDetails!.longitude ??
                current.businessProfile?.longitude ??
                0,
            operatingHours:
                request.businessDetails!.operatingHours ??
                current.businessProfile?.operatingHours,
            deliveryRadiusMeters:
                request.businessDetails!.deliveryRadiusMeters ??
                current.businessProfile?.deliveryRadiusMeters,
            tradeLicenseNumber:
                request.businessDetails!.tradeLicenseNumber ??
                current.businessProfile?.tradeLicenseNumber,
          );
    final updatedFreelancer = request.freelancerDetails == null
        ? current.freelancerProfile
        : domain.FreelancerProfile(
            baseLatitude:
                request.freelancerDetails!.baseLatitude ??
                current.freelancerProfile?.baseLatitude ??
                0,
            baseLongitude:
                request.freelancerDetails!.baseLongitude ??
                current.freelancerProfile?.baseLongitude ??
                0,
            serviceRadiusMeters:
                request.freelancerDetails!.serviceRadiusMeters ??
                current.freelancerProfile?.serviceRadiusMeters ??
                0,
            skills:
                request.freelancerDetails!.skills ??
                current.freelancerProfile?.skills,
            yearsExperience:
                request.freelancerDetails!.yearsExperience ??
                current.freelancerProfile?.yearsExperience,
          );
    final updated = domain.Provider(
      id: current.id,
      providerType: current.providerType,
      displayName: request.displayName ?? current.displayName,
      phoneCountryCode: request.phoneCountryCode ?? current.phoneCountryCode,
      phoneNumber: request.phoneNumber ?? current.phoneNumber,
      whatsappNumber: request.whatsappNumber ?? current.whatsappNumber,
      categoryLabels: request.categoryLabels ?? current.categoryLabels,
      description: request.description ?? current.description,
      slug: current.slug,
      verificationStatus: current.verificationStatus,
      isDiscoverable: current.isDiscoverable,
      countryCode: current.countryCode,
      businessProfile: updatedBusiness,
      freelancerProfile: updatedFreelancer,
    );
    _provider = updated;
    return updated;
  }

  @override
  Future<List<PortfolioPhoto>> listPortfolio() async {
    listPortfolioCallCount++;
    if (listPortfolioError != null) {
      throw listPortfolioError!;
    }
    return List.of(_portfolio);
  }

  @override
  Future<PortfolioPhoto> uploadPortfolioPhoto(
    File imageFile, {
    String? caption,
  }) async {
    uploadPortfolioPhotoCallCount++;
    lastUploadedCaption = caption;
    if (uploadPortfolioPhotoError != null) {
      throw uploadPortfolioPhotoError!;
    }
    final photo = PortfolioPhoto(
      id: 'photo-${_portfolio.length + 1}',
      mediaUrl: '/media/portfolios/test/photo-${_portfolio.length + 1}.jpg',
      caption: caption,
      sortOrder: _portfolio.length,
    );
    _portfolio = [..._portfolio, photo];
    return photo;
  }

  @override
  Future<void> deletePortfolioPhoto(String id) async {
    deletePortfolioPhotoCallCount++;
    lastDeletedPhotoId = id;
    if (deletePortfolioPhotoError != null) {
      throw deletePortfolioPhotoError!;
    }
    _portfolio = _portfolio.where((photo) => photo.id != id).toList();
  }

  @override
  Future<List<PortfolioPhoto>> reorderPortfolio(List<String> orderedIds) async {
    reorderPortfolioCallCount++;
    lastReorderedIds = orderedIds;
    if (reorderPortfolioError != null) {
      throw reorderPortfolioError!;
    }
    final byId = {for (final photo in _portfolio) photo.id: photo};
    final reordered = <PortfolioPhoto>[
      for (var index = 0; index < orderedIds.length; index++)
        if (byId[orderedIds[index]] != null)
          PortfolioPhoto(
            id: byId[orderedIds[index]]!.id,
            mediaUrl: byId[orderedIds[index]]!.mediaUrl,
            caption: byId[orderedIds[index]]!.caption,
            sortOrder: index,
          ),
    ];
    _portfolio = reordered;
    return reordered;
  }

  @override
  Future<List<WeekdayAvailability>> getAvailability() async {
    getAvailabilityCallCount++;
    if (getAvailabilityError != null) {
      throw getAvailabilityError!;
    }
    return List.of(_availability);
  }

  @override
  Future<List<WeekdayAvailability>> updateAvailability(
    List<WeekdayAvailability> entries,
  ) async {
    updateAvailabilityCallCount++;
    lastAvailabilityUpdate = entries;
    if (updateAvailabilityError != null) {
      throw updateAvailabilityError!;
    }
    _availability = List.of(entries);
    return _availability;
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
  categoryLabels: [domain.CategoryLabel(label: 'Plumbing', isPrimary: true)],
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

/// A representative Freelancer provider, for tests that need an
/// [FakeProviderRepository] pre-seeded with an existing Freelancer listing
/// (PRO-002 -- the Storefront's Freelancer subtype-details section).
final fakeExistingFreelancerProvider = domain.Provider(
  id: 'provider-existing-freelancer',
  providerType: ProviderType.freelancer,
  displayName: 'Existing Freelancer',
  phoneCountryCode: '+971',
  phoneNumber: '501234568',
  categoryLabels: [domain.CategoryLabel(label: 'Plumbing', isPrimary: true)],
  slug: 'existing-freelancer',
  verificationStatus: 'pending',
  isDiscoverable: false,
  countryCode: 'AE',
  freelancerProfile: const domain.FreelancerProfile(
    baseLatitude: 25.2048,
    baseLongitude: 55.2708,
    serviceRadiusMeters: 5000,
  ),
);
