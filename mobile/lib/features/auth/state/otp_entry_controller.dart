import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/auth_repository.dart';
import '../domain/models/auth_exception.dart';
import '../domain/models/auth_token.dart';
import '../domain/models/otp_entry_args.dart';

/// The OTP's server-side expiry (`OTP_EXPIRY_MINUTES` in
/// `backend/app/core/constants.py`). A single countdown, started when OTP
/// Entry (S-04) opens, both displays this expiry and gates "Resend code" —
/// there is exactly one timer serving both purposes (AC9, Plan Decision 8).
///
/// Overridable via [otpCountdownDurationProvider] for tests.
const kOtpExpiryDuration = Duration(minutes: 5);

/// The countdown's total duration — a [Provider] so widget tests can
/// override it with a short duration instead of waiting out 5 real minutes.
final otpCountdownDurationProvider = Provider<Duration>(
  (ref) => kOtpExpiryDuration,
);

class OtpEntryState {
  const OtpEntryState({
    required this.remainingSeconds,
    this.code = '',
    this.isVerifying = false,
    this.isResending = false,
    this.error,
  });

  final String code;
  final bool isVerifying;
  final bool isResending;
  final int remainingSeconds;
  final AuthException? error;

  bool get isCodeComplete => code.length == 6;

  bool get canResend => remainingSeconds <= 0 && !isResending;

  OtpEntryState copyWith({
    String? code,
    bool? isVerifying,
    bool? isResending,
    int? remainingSeconds,
    AuthException? error,
    bool clearError = false,
  }) {
    return OtpEntryState(
      code: code ?? this.code,
      isVerifying: isVerifying ?? this.isVerifying,
      isResending: isResending ?? this.isResending,
      remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the OTP Entry screen's (S-04) 6-digit code input, the
/// resend countdown, and the `verify-otp`/`request-otp` (resend) calls.
class OtpEntryController extends StateNotifier<OtpEntryState> {
  OtpEntryController(
    this._repository, {
    required this.countryCode,
    required this.phoneNumber,
    required this.countdownDuration,
  }) : super(OtpEntryState(remainingSeconds: countdownDuration.inSeconds)) {
    _startCountdown();
  }

  final AuthRepository _repository;
  final String countryCode;
  final String phoneNumber;
  final Duration countdownDuration;
  Timer? _timer;

  void _startCountdown() {
    _timer?.cancel();
    state = state.copyWith(remainingSeconds: countdownDuration.inSeconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final next = state.remainingSeconds - 1;
      if (next <= 0) {
        timer.cancel();
        state = state.copyWith(remainingSeconds: 0);
      } else {
        state = state.copyWith(remainingSeconds: next);
      }
    });
  }

  void updateCode(String value) {
    state = state.copyWith(code: value, clearError: true);
  }

  /// Verifies the current code. Returns the resulting [AuthToken] on
  /// success, or `null` if the code is incomplete or verification failed
  /// (in which case [OtpEntryState.error] carries the plain-language cause).
  Future<AuthToken?> verify() async {
    if (!state.isCodeComplete || state.isVerifying) {
      return null;
    }

    state = state.copyWith(isVerifying: true, clearError: true);
    try {
      final token = await _repository.verifyOtp(
        phoneCountryCode: countryCode,
        phoneNumber: phoneNumber,
        code: state.code,
      );
      state = state.copyWith(isVerifying: false);
      return token;
    } on AuthException catch (error) {
      state = state.copyWith(isVerifying: false, error: error);
      return null;
    }
  }

  /// Requests a fresh OTP and restarts the countdown on success.
  Future<void> resend() async {
    if (!state.canResend) {
      return;
    }

    state = state.copyWith(isResending: true, clearError: true);
    try {
      await _repository.requestOtp(
        phoneCountryCode: countryCode,
        phoneNumber: phoneNumber,
      );
      state = state.copyWith(isResending: false, code: '');
      _startCountdown();
    } on AuthException catch (error) {
      state = state.copyWith(isResending: false, error: error);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

final otpEntryControllerProvider = StateNotifierProvider.autoDispose
    .family<OtpEntryController, OtpEntryState, OtpEntryArgs>((ref, args) {
      final countdownDuration = ref.watch(otpCountdownDurationProvider);
      return OtpEntryController(
        ref.watch(authRepositoryProvider),
        countryCode: args.countryCode,
        phoneNumber: args.phoneNumber,
        countdownDuration: countdownDuration,
      );
    });
