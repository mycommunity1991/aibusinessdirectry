import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_repository.dart';
import '../domain/models/portfolio_photo.dart';
import '../domain/models/provider.dart' as domain;
import '../domain/models/provider_exception.dart';
import '../domain/models/update_provider_request.dart';
import '../domain/models/weekday_availability.dart';

/// The Storefront screen's (S-25, PRO-002) load + per-section save state.
/// Each of the four sections (basic info, subtype details, portfolio,
/// availability) has its own `isSaving`/`error`/`justSaved` triple so one
/// section's in-flight save, failure, or success is never conflated with
/// another's (AC5: "each independently saveable").
class StorefrontState {
  const StorefrontState({
    this.provider,
    this.portfolio = const [],
    this.availability = const [],
    this.isLoading = true,
    this.loadError,
    this.basicInfoSaving = false,
    this.basicInfoError,
    this.basicInfoJustSaved = false,
    this.detailsSaving = false,
    this.detailsError,
    this.detailsJustSaved = false,
    this.availabilitySaving = false,
    this.availabilityError,
    this.availabilityJustSaved = false,
  });

  final domain.Provider? provider;
  final List<PortfolioPhoto> portfolio;
  final List<WeekdayAvailability> availability;

  final bool isLoading;
  final ProviderException? loadError;

  final bool basicInfoSaving;
  final ProviderException? basicInfoError;
  final bool basicInfoJustSaved;

  final bool detailsSaving;
  final ProviderException? detailsError;
  final bool detailsJustSaved;

  final bool availabilitySaving;
  final ProviderException? availabilityError;
  final bool availabilityJustSaved;

  StorefrontState copyWith({
    domain.Provider? provider,
    List<PortfolioPhoto>? portfolio,
    List<WeekdayAvailability>? availability,
    bool? isLoading,
    ProviderException? loadError,
    bool clearLoadError = false,
    bool? basicInfoSaving,
    ProviderException? basicInfoError,
    bool clearBasicInfoError = false,
    bool? basicInfoJustSaved,
    bool? detailsSaving,
    ProviderException? detailsError,
    bool clearDetailsError = false,
    bool? detailsJustSaved,
    bool? availabilitySaving,
    ProviderException? availabilityError,
    bool clearAvailabilityError = false,
    bool? availabilityJustSaved,
  }) {
    return StorefrontState(
      provider: provider ?? this.provider,
      portfolio: portfolio ?? this.portfolio,
      availability: availability ?? this.availability,
      isLoading: isLoading ?? this.isLoading,
      loadError: clearLoadError ? null : (loadError ?? this.loadError),
      basicInfoSaving: basicInfoSaving ?? this.basicInfoSaving,
      basicInfoError: clearBasicInfoError
          ? null
          : (basicInfoError ?? this.basicInfoError),
      basicInfoJustSaved: basicInfoJustSaved ?? false,
      detailsSaving: detailsSaving ?? this.detailsSaving,
      detailsError: clearDetailsError
          ? null
          : (detailsError ?? this.detailsError),
      detailsJustSaved: detailsJustSaved ?? false,
      availabilitySaving: availabilitySaving ?? this.availabilitySaving,
      availabilityError: clearAvailabilityError
          ? null
          : (availabilityError ?? this.availabilityError),
      availabilityJustSaved: availabilityJustSaved ?? false,
    );
  }
}

/// Loads and independently saves the four Storefront sections (PRO-002,
/// item 28, `Plan_S04_PRO-002.md`). Each `save*` method calls exactly one
/// [ProviderRepository] method with a request built from only that
/// section's own fields -- never another section's (AC5).
class StorefrontController extends StateNotifier<StorefrontState> {
  StorefrontController(this._repository) : super(const StorefrontState()) {
    load();
  }

  final ProviderRepository _repository;

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearLoadError: true);
    try {
      final provider = await _repository.getMyProvider();
      if (provider == null) {
        state = state.copyWith(
          isLoading: false,
          loadError: const ProviderException(type: ProviderErrorType.notFound),
        );
        return;
      }
      final portfolio = await _repository.listPortfolio();
      final availability = await _repository.getAvailability();
      state = state.copyWith(
        provider: provider,
        portfolio: portfolio,
        availability: availability,
        isLoading: false,
      );
    } on ProviderException catch (error) {
      state = state.copyWith(isLoading: false, loadError: error);
    }
  }

  /// Saves the "basic info" section (display name, phone, WhatsApp,
  /// description, category labels) -- never touches subtype details,
  /// portfolio, or availability.
  Future<bool> saveBasicInfo({
    required String displayName,
    required String phoneCountryCode,
    required String phoneNumber,
    String? whatsappNumber,
    String? description,
    required List<domain.CategoryLabel> categoryLabels,
  }) async {
    state = state.copyWith(basicInfoSaving: true, clearBasicInfoError: true);
    try {
      final updated = await _repository.updateProvider(
        UpdateProviderRequest(
          displayName: displayName,
          phoneCountryCode: phoneCountryCode,
          phoneNumber: phoneNumber,
          whatsappNumber: whatsappNumber,
          description: description,
          categoryLabels: categoryLabels,
        ),
      );
      state = state.copyWith(
        provider: updated,
        basicInfoSaving: false,
        basicInfoJustSaved: true,
      );
      return true;
    } on ProviderException catch (error) {
      state = state.copyWith(basicInfoSaving: false, basicInfoError: error);
      return false;
    }
  }

  /// Saves the Business subtype-details section -- never touches basic
  /// info, portfolio, or availability.
  Future<bool> saveBusinessDetails(UpdateBusinessDetails details) async {
    return _saveDetails(
      () => _repository.updateProvider(
        UpdateProviderRequest(businessDetails: details),
      ),
    );
  }

  /// Saves the Freelancer subtype-details section -- never touches basic
  /// info, portfolio, or availability.
  Future<bool> saveFreelancerDetails(UpdateFreelancerDetails details) async {
    return _saveDetails(
      () => _repository.updateProvider(
        UpdateProviderRequest(freelancerDetails: details),
      ),
    );
  }

  Future<bool> _saveDetails(Future<domain.Provider> Function() update) async {
    state = state.copyWith(detailsSaving: true, clearDetailsError: true);
    try {
      final updated = await update();
      state = state.copyWith(
        provider: updated,
        detailsSaving: false,
        detailsJustSaved: true,
      );
      return true;
    } on ProviderException catch (error) {
      state = state.copyWith(detailsSaving: false, detailsError: error);
      return false;
    }
  }

  /// Keeps the portfolio list in sync after a [PortfolioManager] action
  /// (add/remove/reorder) -- those calls persist immediately against their
  /// own endpoints, so this never itself calls the repository.
  void setPortfolio(List<PortfolioPhoto> photos) {
    state = state.copyWith(portfolio: photos);
  }

  /// Saves the weekly availability section -- never touches basic info,
  /// subtype details, or portfolio.
  Future<bool> saveAvailability(List<WeekdayAvailability> entries) async {
    state = state.copyWith(
      availabilitySaving: true,
      clearAvailabilityError: true,
    );
    try {
      final updated = await _repository.updateAvailability(entries);
      state = state.copyWith(
        availability: updated,
        availabilitySaving: false,
        availabilityJustSaved: true,
      );
      return true;
    } on ProviderException catch (error) {
      state = state.copyWith(
        availabilitySaving: false,
        availabilityError: error,
      );
      return false;
    }
  }
}

final storefrontControllerProvider =
    StateNotifierProvider.autoDispose<StorefrontController, StorefrontState>(
      (ref) => StorefrontController(ref.watch(providerRepositoryProvider)),
    );
