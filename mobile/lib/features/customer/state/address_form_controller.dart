import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/saved_address_repository.dart';
import '../domain/models/saved_address.dart';
import '../domain/models/saved_address_exception.dart';

class AddressFormState {
  const AddressFormState({this.isSaving = false, this.error});

  final bool isSaving;
  final SavedAddressException? error;

  AddressFormState copyWith({
    bool? isSaving,
    SavedAddressException? error,
    bool clearError = false,
  }) {
    return AddressFormState(
      isSaving: isSaving ?? this.isSaving,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages `AddressFormScreen`'s save/create/update calls (CUS-002, item
/// 17) — mirrors `CustomerProfileController`'s split: the screen owns its
/// own field state via plain `TextEditingController`s (matching
/// `profile_settings_screen.dart`'s established convention), while this
/// controller owns only the async save operation and its loading/error
/// state.
class AddressFormController extends StateNotifier<AddressFormState> {
  AddressFormController(this._repository) : super(const AddressFormState());

  final SavedAddressRepository _repository;

  /// Creates a new address (S-05's first-address prompt, S-12's "add", and
  /// the AC5 re-prompt all go through this same path). Returns the created
  /// [SavedAddress] on success, `null` on failure (in which case
  /// [AddressFormState.error] carries the plain-language cause).
  Future<SavedAddress?> create({
    String? label,
    required String addressLine,
    String? city,
    String? region,
    required String countryCode,
    required double latitude,
    required double longitude,
    required bool isDefault,
  }) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final address = await _repository.create(
        label: label,
        addressLine: addressLine,
        city: city,
        region: region,
        countryCode: countryCode,
        latitude: latitude,
        longitude: longitude,
        isDefault: isDefault,
      );
      state = state.copyWith(isSaving: false);
      return address;
    } on SavedAddressException catch (error) {
      state = state.copyWith(isSaving: false, error: error);
      return null;
    }
  }

  /// Updates an existing address (S-12's "edit"). Returns the updated
  /// [SavedAddress] on success, `null` on failure.
  Future<SavedAddress?> update(
    String addressId, {
    String? label,
    required String addressLine,
    String? city,
    String? region,
    required String countryCode,
    required double latitude,
    required double longitude,
    required bool isDefault,
  }) async {
    state = state.copyWith(isSaving: true, clearError: true);
    try {
      final address = await _repository.update(
        addressId,
        label: label,
        addressLine: addressLine,
        city: city,
        region: region,
        countryCode: countryCode,
        latitude: latitude,
        longitude: longitude,
        isDefault: isDefault,
      );
      state = state.copyWith(isSaving: false);
      return address;
    } on SavedAddressException catch (error) {
      state = state.copyWith(isSaving: false, error: error);
      return null;
    }
  }
}

final addressFormControllerProvider =
    StateNotifierProvider.autoDispose<AddressFormController, AddressFormState>(
      (ref) => AddressFormController(ref.watch(savedAddressRepositoryProvider)),
    );
