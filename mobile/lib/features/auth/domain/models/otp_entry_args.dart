/// Arguments passed from Phone Entry (S-03) to OTP Entry (S-04) via
/// GoRouter's `extra`, and used to key the per-attempt [OtpEntryController].
///
/// [expiresInSeconds] carries the real OTP expiry from the triggering
/// `request-otp` response (`RequestOtpResponse.expires_in_seconds` —
/// `backend/app/modules/identity/schemas.py`), used to size the resend
/// countdown from the actual server value instead of a hardcoded duplicate
/// constant (FU-2, `Walkthrough_S02_AUTH-001.md`). `null` only if that
/// response was somehow missing the field — the countdown then falls back
/// to `otpCountdownDurationProvider`'s defensive default.
typedef OtpEntryArgs = ({
  String countryCode,
  String phoneNumber,
  int? expiresInSeconds,
});
