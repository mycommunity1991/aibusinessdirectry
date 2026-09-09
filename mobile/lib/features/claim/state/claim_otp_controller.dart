import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/claim_repository.dart';
import '../domain/models/claim_exception.dart';
import '../domain/models/claim_result.dart';
import '../domain/models/claim_review_reason.dart';

/// A defensive fallback for the OTP countdown's duration -- mirrors
/// `otp_entry_controller.dart`'s `kOtpExpiryFallbackDuration`, used only if
/// a `request-otp` response is somehow missing `expires_in_seconds`.
const kClaimOtpExpiryFallbackDuration = Duration(minutes: 5);

/// Overridable via [claimOtpCountdownDurationProvider] for tests, mirroring
/// `otpCountdownDurationProvider`'s pattern.
final claimOtpCountdownDurationProvider = Provider<Duration>(
  (ref) => kClaimOtpExpiryFallbackDuration,
);

/// The Claim OTP screen's (S-22, CLM-001, AC4/AC5/AC6) status.
enum ClaimOtpStatus {
  /// Initial state: the OTP for this listing's own public number is being
  /// requested. No code-entry UI is shown yet.
  requestingOtp,

  /// The OTP was sent; the code-entry UI (and its resend countdown) is
  /// active. The "This isn't working" link is always visible in this
  /// state (AC6) -- never gated behind a failure count.
  codeEntry,

  /// A `request-admin-review` call is in flight -- either the user tapped
  /// a reason on the "This isn't working" sheet, or (AC6's no-public-
  /// number case) the initial `request-otp` call itself failed with
  /// [ClaimErrorType.publicNumberUnavailable] and this was triggered
  /// automatically, skipping [codeEntry] entirely.
  submittingReview,

  /// `request-admin-review` succeeded -- a terminal, plain-language
  /// confirmation state (AC6).
  reviewConfirmed,

  /// `verify-otp` succeeded -- a terminal success state (AC5) pointing the
  /// claimant toward submitting verification documents next.
  claimed,

  /// The initial `request-otp` call failed for a reason other than
  /// [ClaimErrorType.publicNumberUnavailable] (e.g. the listing was no
  /// longer a valid claim target, or a network failure) -- offers a retry,
  /// mirroring `SearchResultsScreen`'s own load-error/retry pattern.
  error,
}

class ClaimOtpState {
  const ClaimOtpState({
    this.status = ClaimOtpStatus.requestingOtp,
    this.code = '',
    this.remainingSeconds = 0,
    this.isVerifying = false,
    this.isResending = false,
    this.claimResult,
    this.error,
  });

  final ClaimOtpStatus status;
  final String code;
  final int remainingSeconds;
  final bool isVerifying;
  final bool isResending;
  final ClaimResult? claimResult;
  final ClaimException? error;

  bool get isCodeComplete => code.length == 6;

  bool get canResend => remainingSeconds <= 0 && !isResending;

  ClaimOtpState copyWith({
    ClaimOtpStatus? status,
    String? code,
    int? remainingSeconds,
    bool? isVerifying,
    bool? isResending,
    ClaimResult? claimResult,
    ClaimException? error,
    bool clearError = false,
  }) {
    return ClaimOtpState(
      status: status ?? this.status,
      code: code ?? this.code,
      remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      isVerifying: isVerifying ?? this.isVerifying,
      isResending: isResending ?? this.isResending,
      claimResult: claimResult ?? this.claimResult,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Manages the Claim OTP screen's (S-22) full lifecycle: requesting the
/// initial OTP against the target listing's own public number (AC4), the
/// 6-digit code entry + resend countdown, `verify-otp` (AC5), and the
/// "this isn't working" admin-review fallback (AC6) -- including the
/// no-public-number edge case, where [requestOtp] never even sends a code.
class ClaimOtpController extends StateNotifier<ClaimOtpState> {
  ClaimOtpController(
    this._repository, {
    required this.providerId,
    required Duration initialCountdownDuration,
  }) : _countdownDuration = initialCountdownDuration,
       super(const ClaimOtpState()) {
    _requestInitialOtp();
  }

  final ClaimRepository _repository;
  final String providerId;

  Duration _countdownDuration;
  Timer? _timer;

  Future<void> _requestInitialOtp() async {
    state = state.copyWith(
      status: ClaimOtpStatus.requestingOtp,
      clearError: true,
    );
    try {
      final expiresInSeconds = await _repository.requestOtp(providerId);
      if (expiresInSeconds != null) {
        _countdownDuration = Duration(seconds: expiresInSeconds);
      }
      state = state.copyWith(
        status: ClaimOtpStatus.codeEntry,
        remainingSeconds: _countdownDuration.inSeconds,
      );
      _startCountdown();
    } on ClaimException catch (error) {
      if (error.type == ClaimErrorType.publicNumberUnavailable) {
        // AC6's no-public-number case: `request_otp` never sent a code
        // (the backend raises this *before* calling `OtpService` at all)
        // -- there is nothing to wait for, so skip the code-entry UI
        // entirely and go straight to the admin-review fallback,
        // auto-submitting the one reason that structurally applies.
        await _submitReview(ClaimReviewReason.noPublicNumber, auto: true);
        return;
      }
      state = state.copyWith(status: ClaimOtpStatus.error, error: error);
    }
  }

  /// Retries the initial `request-otp` call -- offered from
  /// [ClaimOtpStatus.error]'s retry action.
  Future<void> retryInitialRequest() => _requestInitialOtp();

  void updateCode(String value) {
    state = state.copyWith(code: value, clearError: true);
  }

  /// Verifies the current code. Returns the resulting [ClaimResult] on
  /// success (AC5) -- `null` if the code is incomplete or verification
  /// failed, in which case [ClaimOtpState.error] carries the plain-
  /// language cause and the screen stays on [ClaimOtpStatus.codeEntry].
  Future<ClaimResult?> verify() async {
    if (!state.isCodeComplete || state.isVerifying) {
      return null;
    }
    state = state.copyWith(isVerifying: true, clearError: true);
    try {
      final result = await _repository.verifyOtp(
        providerId: providerId,
        code: state.code,
      );
      _timer?.cancel();
      state = state.copyWith(
        status: ClaimOtpStatus.claimed,
        isVerifying: false,
        claimResult: result,
      );
      return result;
    } on ClaimException catch (error) {
      state = state.copyWith(isVerifying: false, error: error);
      return null;
    }
  }

  /// Requests a fresh OTP and restarts the countdown on success, mirroring
  /// `OtpEntryController.resend`'s pattern.
  Future<void> resend() async {
    if (!state.canResend) {
      return;
    }
    state = state.copyWith(isResending: true, clearError: true);
    try {
      final expiresInSeconds = await _repository.requestOtp(providerId);
      if (expiresInSeconds != null) {
        _countdownDuration = Duration(seconds: expiresInSeconds);
      }
      state = state.copyWith(isResending: false, code: '');
      _startCountdown();
    } on ClaimException catch (error) {
      state = state.copyWith(isResending: false, error: error);
    }
  }

  /// Submits AC6's explicit "this isn't working" fallback for a manually
  /// chosen [reason] -- called from the reason-selection sheet. Both
  /// sheet options submit [ClaimReviewReason.otpFailed]
  /// (`claim_review_reason.dart`'s own doc explains why).
  Future<void> submitReviewReason(ClaimReviewReason reason) =>
      _submitReview(reason, auto: false);

  Future<void> _submitReview(
    ClaimReviewReason reason, {
    required bool auto,
  }) async {
    _timer?.cancel();
    state = state.copyWith(
      status: ClaimOtpStatus.submittingReview,
      clearError: true,
    );
    try {
      await _repository.requestAdminReview(
        providerId: providerId,
        reason: reason,
      );
      state = state.copyWith(status: ClaimOtpStatus.reviewConfirmed);
    } on ClaimException catch (error) {
      // The no-public-number auto-submit failing is a genuine load error
      // (there was never a code-entry UI to fall back to); a manually
      // triggered submission failing returns the user to the code-entry
      // screen they were already on, with the error shown inline.
      state = state.copyWith(
        status: auto ? ClaimOtpStatus.error : ClaimOtpStatus.codeEntry,
        error: error,
      );
    }
  }

  void _startCountdown() {
    _timer?.cancel();
    state = state.copyWith(remainingSeconds: _countdownDuration.inSeconds);
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

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

final claimOtpControllerProvider = StateNotifierProvider.autoDispose
    .family<ClaimOtpController, ClaimOtpState, String>((ref, providerId) {
      final initialCountdownDuration = ref.watch(
        claimOtpCountdownDurationProvider,
      );
      return ClaimOtpController(
        ref.watch(claimRepositoryProvider),
        providerId: providerId,
        initialCountdownDuration: initialCountdownDuration,
      );
    });
