/// Arguments passed from Phone Entry (S-03) to OTP Entry (S-04) via
/// GoRouter's `extra`, and used to key the per-attempt [OtpEntryController].
typedef OtpEntryArgs = ({String countryCode, String phoneNumber});
