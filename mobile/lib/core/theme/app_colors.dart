import 'package:flutter/material.dart';

/// Centralized brand color seeds.
///
/// These are the only hardcoded color values in the app — every screen and
/// widget must read colors from `Theme.of(context).colorScheme` (built from
/// these seeds in [AppTheme]) instead of referencing this class directly.
///
/// Source of truth: `docs/AI/15_SCREEN_INVENTORY.md` — Visual Identity.
class AppColors {
  const AppColors._();

  /// Electric indigo — primary brand chrome (app bar, nav, links).
  static const Color primary = Color(0xFF2F54EB);

  /// Teal — reserved for the single highest-emphasis action per screen.
  static const Color secondary = Color(0xFF14B8A6);

  /// Approved verification / positive outcome states.
  static const Color success = Color(0xFF22C55E);

  /// Pending verification / unclaimed-listing states.
  static const Color warning = Color(0xFFF59E0B);

  /// Text/icon color for content painted directly on top of [warning] --
  /// e.g. the full-width "Unclaimed" banner (CLM-001, Decision 8,
  /// `16_UX_GUIDELINES.md`) -- never a plain white/black literal chosen
  /// ad hoc per widget. Matches `docs/AI/DESIGN.md`'s `on-warning` token.
  static const Color onWarning = Color(0xFF3F2E00);

  /// Rejected verification / failed OTP states.
  static const Color error = Color(0xFFEF4444);

  /// Informational banners only — never used for tappable actions.
  static const Color info = Color(0xFF3B82F6);
}
