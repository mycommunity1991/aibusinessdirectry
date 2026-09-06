/// The customer's preferred notification channel (mirrors the backend's
/// `customer.NotificationChannel` StrEnum,
/// `backend/app/modules/customer/models.py`).
enum NotificationChannel {
  whatsapp,
  sms,
  email;

  /// The exact wire value expected/returned by the backend — identical to
  /// [name] today, but spelled out explicitly so a future rename of the
  /// Dart enum member never silently changes the API contract.
  String get wireValue => switch (this) {
    NotificationChannel.whatsapp => 'whatsapp',
    NotificationChannel.sms => 'sms',
    NotificationChannel.email => 'email',
  };

  static NotificationChannel fromWireValue(String value) {
    return NotificationChannel.values.firstWhere(
      (channel) => channel.wireValue == value,
      orElse: () => NotificationChannel.whatsapp,
    );
  }
}

/// A thin client-side model matching the backend's
/// `CustomerProfileResponse` (`backend/app/modules/customer/schemas.py`,
/// CUS-001) — the combined 1:1 `customer_profiles` + `customer_preferences`
/// resource returned/accepted by `GET`/`PATCH /customers/me`.
class CustomerProfile {
  const CustomerProfile({
    required this.id,
    required this.displayName,
    this.avatarUrl,
    required this.language,
    required this.notificationChannel,
  });

  factory CustomerProfile.fromJson(Map<String, dynamic> json) {
    return CustomerProfile(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
      language: json['language'] as String,
      notificationChannel: NotificationChannel.fromWireValue(
        json['notification_channel'] as String,
      ),
    );
  }

  final String id;
  final String displayName;
  final String? avatarUrl;

  /// The backend's `identity.language_code` value — `"en"` or `"ar"`
  /// (`backend/app/modules/identity/models.py`'s `LanguageCode`, reused by
  /// the Customer domain per `Plan_S03_CUS-001.md` Decision 2). Kept as a
  /// plain string here (not a [Locale]) since this is the raw wire value;
  /// screens construct a `Locale(language)` where needed.
  final String language;
  final NotificationChannel notificationChannel;
}
