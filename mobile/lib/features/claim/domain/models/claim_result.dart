/// Mirrors the backend's `ClaimResultResponse`
/// (`backend/app/modules/provider/schemas.py`, CLM-001, AC5) -- the
/// response payload for a successful `POST /claims/{provider_id}/verify-otp`.
///
/// [verificationStatus] is carried through as the backend's raw wire string
/// (`pending` immediately after a successful claim, per Decision 2/6) --
/// mirrors `features/provider/domain/models/provider.dart`'s own
/// `verificationStatus: String` convention rather than a duplicate local
/// enum; nothing in this screen renders it directly today (the success
/// state's copy is fixed, not switched on this value).
class ClaimResult {
  const ClaimResult({
    required this.providerId,
    required this.isClaimed,
    required this.verificationStatus,
  });

  factory ClaimResult.fromJson(Map<String, dynamic> json) {
    return ClaimResult(
      providerId: json['provider_id'] as String,
      isClaimed: json['is_claimed'] as bool,
      verificationStatus: json['verification_status'] as String,
    );
  }

  final String providerId;
  final bool isClaimed;
  final String verificationStatus;
}
