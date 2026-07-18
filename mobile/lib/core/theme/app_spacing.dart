/// Centralized 8-point spacing scale.
///
/// Source of truth: `docs/AI/07_UI_GUIDELINES.md` — Spacing.
/// No screen or widget should use an arbitrary `SizedBox`/`EdgeInsets`
/// value outside this scale.
class AppSpacing {
  const AppSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 40;
  static const double xxxl = 48;
  static const double huge = 64;
}

/// Centralized border-radius scale.
///
/// Source of truth: `docs/AI/07_UI_GUIDELINES.md` — Border Radius.
class AppRadius {
  const AppRadius._();

  static const double small = 8;
  static const double standard = 12;
  static const double largeCard = 16;
  static const double bottomSheet = 24;
}
