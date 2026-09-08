import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/provider_repository.dart';
import '../domain/models/create_provider_request.dart';
import '../domain/models/provider.dart' as domain;
import '../domain/models/provider_exception.dart';
import '../../../shared/models/provider_type.dart';

/// The wizard's total step count -- Type (S-16), Basic Info (S-17), and
/// Details (S-18a/b) -- shared across every provider onboarding screen so
/// the `StepIndicator` is always consistent (AC9, `Plan_S04_PRO-001.md`).
const int providerWizardTotalSteps = 3;

/// The in-memory wizard draft collected across S-16 -> S-17 -> S-18a/b
/// (`Plan_S04_PRO-001.md` Decision 8) — no cross-session persistence, no
/// server-side partial state. Only [ProviderOnboardingController.submit]
/// ever calls the repository, exactly once, at the very end of the wizard
/// (Decision 2).
class ProviderOnboardingState {
  const ProviderOnboardingState({
    this.providerType,
    this.displayName,
    this.phoneCountryCode,
    this.phoneNumber,
    this.whatsappNumber,
    this.categoryLabel,
    this.description,
    this.businessDetails,
    this.freelancerDetails,
    this.isSubmitting = false,
    this.error,
  });

  /// Set exactly once, by [ProviderOnboardingController.setProviderType] —
  /// `ChooseProviderTypeScreen` (S-16) is the only call site (AC3).
  final ProviderType? providerType;

  final String? displayName;
  final String? phoneCountryCode;
  final String? phoneNumber;
  final String? whatsappNumber;
  final String? categoryLabel;
  final String? description;

  final CreateBusinessDetails? businessDetails;
  final CreateFreelancerDetails? freelancerDetails;

  final bool isSubmitting;
  final ProviderException? error;

  ProviderOnboardingState copyWith({
    ProviderType? providerType,
    String? displayName,
    String? phoneCountryCode,
    String? phoneNumber,
    String? whatsappNumber,
    bool clearWhatsappNumber = false,
    String? categoryLabel,
    String? description,
    bool clearDescription = false,
    CreateBusinessDetails? businessDetails,
    CreateFreelancerDetails? freelancerDetails,
    bool? isSubmitting,
    ProviderException? error,
    bool clearError = false,
  }) {
    return ProviderOnboardingState(
      providerType: providerType ?? this.providerType,
      displayName: displayName ?? this.displayName,
      phoneCountryCode: phoneCountryCode ?? this.phoneCountryCode,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      whatsappNumber: clearWhatsappNumber
          ? null
          : (whatsappNumber ?? this.whatsappNumber),
      categoryLabel: categoryLabel ?? this.categoryLabel,
      description: clearDescription ? null : (description ?? this.description),
      businessDetails: businessDetails ?? this.businessDetails,
      freelancerDetails: freelancerDetails ?? this.freelancerDetails,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the Provider onboarding wizard's draft state and its single,
/// end-of-flow submission (`Plan_S04_PRO-001.md` items 25/26-30).
class ProviderOnboardingController
    extends StateNotifier<ProviderOnboardingState> {
  ProviderOnboardingController(this._repository)
    : super(const ProviderOnboardingState());

  final ProviderRepository _repository;

  /// Sets the wizard's provider type — called exactly once, from
  /// `ChooseProviderTypeScreen` (S-16, AC3). No other screen in this
  /// feature ever calls this.
  void setProviderType(ProviderType providerType) {
    state = state.copyWith(providerType: providerType);
  }

  /// Records S-17's basic-info fields into the draft.
  void setBasicInfo({
    required String displayName,
    required String phoneCountryCode,
    required String phoneNumber,
    String? whatsappNumber,
    required String categoryLabel,
    String? description,
  }) {
    state = state.copyWith(
      displayName: displayName,
      phoneCountryCode: phoneCountryCode,
      phoneNumber: phoneNumber,
      whatsappNumber: whatsappNumber,
      clearWhatsappNumber: whatsappNumber == null,
      categoryLabel: categoryLabel,
      description: description,
      clearDescription: description == null,
    );
  }

  /// Records S-18a's business-subtype details into the draft.
  void setBusinessDetails(CreateBusinessDetails details) {
    state = state.copyWith(businessDetails: details);
  }

  /// Records S-18b's freelancer-subtype details into the draft.
  void setFreelancerDetails(CreateFreelancerDetails details) {
    state = state.copyWith(freelancerDetails: details);
  }

  /// Submits the entire draft in a single `POST /providers/me` call
  /// (Decision 2) — the wizard's only repository call. Returns the created
  /// [domain.Provider] on success, `null` on failure (in which case
  /// [ProviderOnboardingState.error] carries the plain-language cause).
  Future<domain.Provider?> submit() async {
    final draft = state;
    final providerType = draft.providerType;
    if (providerType == null ||
        draft.displayName == null ||
        draft.phoneCountryCode == null ||
        draft.phoneNumber == null ||
        draft.categoryLabel == null) {
      // Defensive only -- every wizard screen gates its own navigation, so
      // this should be unreachable in practice.
      state = state.copyWith(
        error: const ProviderException(type: ProviderErrorType.unknown),
      );
      return null;
    }

    state = state.copyWith(isSubmitting: true, clearError: true);
    final request = CreateProviderRequest(
      providerType: providerType,
      displayName: draft.displayName!,
      phoneCountryCode: draft.phoneCountryCode!,
      phoneNumber: draft.phoneNumber!,
      whatsappNumber: draft.whatsappNumber,
      categoryLabel: draft.categoryLabel!,
      description: draft.description,
      businessDetails: draft.businessDetails,
      freelancerDetails: draft.freelancerDetails,
    );
    try {
      final provider = await _repository.createProvider(request);
      state = state.copyWith(isSubmitting: false);
      return provider;
    } on ProviderException catch (error) {
      state = state.copyWith(isSubmitting: false, error: error);
      return null;
    }
  }
}

final providerOnboardingControllerProvider =
    StateNotifierProvider.autoDispose<
      ProviderOnboardingController,
      ProviderOnboardingState
    >(
      (ref) =>
          ProviderOnboardingController(ref.watch(providerRepositoryProvider)),
    );
