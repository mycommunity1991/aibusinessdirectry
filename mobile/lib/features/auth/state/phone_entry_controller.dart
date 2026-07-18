import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/auth_repository.dart';
import '../domain/models/auth_exception.dart';

/// Matches the backend's `RequestOtpRequest.phone_country_code` pattern
/// (`backend/app/schemas/auth.py`).
final _countryCodePattern = RegExp(r'^\+[1-9]\d{0,3}$');

/// Matches the backend's `RequestOtpRequest.phone_number` pattern.
final _phoneNumberPattern = RegExp(r'^\d{4,20}$');

class PhoneEntryState {
  const PhoneEntryState({
    // UAE-first by design (docs/AI/00_PROJECT_CONTEXT.md).
    this.countryCode = '+971',
    this.phoneNumber = '',
    this.isSubmitting = false,
    this.error,
  });

  final String countryCode;
  final String phoneNumber;
  final bool isSubmitting;
  final AuthException? error;

  bool get isCountryCodeValid => _countryCodePattern.hasMatch(countryCode);

  bool get isPhoneNumberValid => _phoneNumberPattern.hasMatch(phoneNumber);

  bool get isValid => isCountryCodeValid && isPhoneNumberValid;

  PhoneEntryState copyWith({
    String? countryCode,
    String? phoneNumber,
    bool? isSubmitting,
    AuthException? error,
    bool clearError = false,
  }) {
    return PhoneEntryState(
      countryCode: countryCode ?? this.countryCode,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the Sign In / Sign Up screen's (S-03) mobile-number form and
/// drives the `request-otp` call.
class PhoneEntryController extends StateNotifier<PhoneEntryState> {
  PhoneEntryController(this._repository) : super(const PhoneEntryState());

  final AuthRepository _repository;

  void updateCountryCode(String value) {
    state = state.copyWith(countryCode: value, clearError: true);
  }

  void updatePhoneNumber(String value) {
    state = state.copyWith(phoneNumber: value, clearError: true);
  }

  /// Requests an OTP for the current form state. Returns `true` once the
  /// request succeeds so the screen can navigate to OTP Entry (S-04).
  Future<bool> submit() async {
    if (!state.isValid || state.isSubmitting) {
      return false;
    }

    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _repository.requestOtp(
        phoneCountryCode: state.countryCode,
        phoneNumber: state.phoneNumber,
      );
      state = state.copyWith(isSubmitting: false);
      return true;
    } on AuthException catch (error) {
      state = state.copyWith(isSubmitting: false, error: error);
      return false;
    }
  }
}

final phoneEntryControllerProvider =
    StateNotifierProvider.autoDispose<PhoneEntryController, PhoneEntryState>((
      ref,
    ) {
      return PhoneEntryController(ref.watch(authRepositoryProvider));
    });
