/// A thin client-side model matching the backend's
/// `UserSummaryResponse` (`backend/app/schemas/auth.py`).
class AuthUser {
  const AuthUser({
    required this.id,
    required this.phoneCountryCode,
    required this.phoneNumber,
    required this.status,
    required this.preferredLanguage,
    required this.roles,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as String,
      phoneCountryCode: json['phone_country_code'] as String?,
      phoneNumber: json['phone_number'] as String?,
      status: json['status'] as String,
      preferredLanguage: json['preferred_language'] as String,
      roles: (json['roles'] as List<dynamic>? ?? const <dynamic>[])
          .map((role) => role as String)
          .toList(growable: false),
    );
  }

  final String id;
  final String? phoneCountryCode;
  final String? phoneNumber;
  final String status;
  final String preferredLanguage;
  final List<String> roles;

  /// Mirrors [fromJson]'s field names — used by [AuthToken.toJson] so a
  /// session persisted to secure storage (AUTH-003) round-trips through
  /// the exact same shape the backend sends, rather than a second,
  /// hand-maintained serialization format.
  Map<String, dynamic> toJson() => {
    'id': id,
    'phone_country_code': phoneCountryCode,
    'phone_number': phoneNumber,
    'status': status,
    'preferred_language': preferredLanguage,
    'roles': roles,
  };
}
