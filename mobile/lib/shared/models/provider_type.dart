/// Mirrors the backend's `ProviderType` enum
/// (`backend/app/modules/provider/models.py`) — Business or Freelancer,
/// selected exactly once on `ChooseProviderTypeScreen` (S-16) and immutable
/// afterwards (AC3, `Plan_S04_PRO-001.md` Decision 3).
enum ProviderType {
  business,
  freelancer;

  /// The exact wire value the backend expects/returns.
  String get wireValue => switch (this) {
    ProviderType.business => 'business',
    ProviderType.freelancer => 'freelancer',
  };

  static ProviderType fromWire(String value) {
    return switch (value) {
      'business' => ProviderType.business,
      'freelancer' => ProviderType.freelancer,
      _ => throw ArgumentError('Unknown provider_type: $value'),
    };
  }
}
