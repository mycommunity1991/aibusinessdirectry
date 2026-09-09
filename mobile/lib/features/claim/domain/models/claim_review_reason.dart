/// Mirrors the backend's `RequestClaimAdminReviewRequest.reason`
/// (`backend/app/modules/provider/schemas.py`, CLM-001, AC6) --
/// `Literal["otp_failed", "no_public_number"]`.
///
/// [noPublicNumber] is only ever submitted automatically by
/// `ClaimOtpController` itself -- when `request-otp` fails with
/// `ClaimErrorType.publicNumberUnavailable` (the backend's
/// `ClaimPublicNumberUnavailableError`, raised *before* any OTP is ever
/// sent) -- never offered as a manually-tappable option on the "This
/// isn't working" reason sheet. Both manually-tappable sheet options ("I
/// didn't receive a code" / "This isn't my business's number") submit
/// [otpFailed]: by construction, a listing that has no public number at
/// all never reaches the OTP-entry UI in the first place (the auto-submit
/// path above handles it), so from this screen's reachable state, *any*
/// manually-reported "this isn't working" reason -- including "wrong
/// number" -- means the backend's only remaining bucket, `otp_failed`
/// ("verification was attempted and failed"), applies; the sheet still
/// offers two distinct, plain-language options because they read
/// differently to the user (`16_UX_GUIDELINES.md` -- "speak the user's
/// language"), even though both map to the same backend reason value.
enum ClaimReviewReason {
  otpFailed,
  noPublicNumber;

  /// The exact wire value the backend expects.
  String get wireValue => switch (this) {
    ClaimReviewReason.otpFailed => 'otp_failed',
    ClaimReviewReason.noPublicNumber => 'no_public_number',
  };
}
