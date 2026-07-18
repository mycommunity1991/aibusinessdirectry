import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _languageStorageKey = 'app_language_code';

/// Persists the user's chosen language (S-02) via `shared_preferences` —
/// not sensitive data, so secure storage is unnecessary (Plan Decision,
/// `docs/implementation/plans/Plan_S02_AUTH-001.md`).
///
/// `null` means no language has been chosen yet, which Splash (S-01)
/// interprets as "route to Language Selection."
class LanguageController extends AsyncNotifier<Locale?> {
  @override
  Future<Locale?> build() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_languageStorageKey);
    return code == null ? null : Locale(code);
  }

  Future<void> setLanguage(Locale locale) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_languageStorageKey, locale.languageCode);
    state = AsyncData(locale);
  }
}

final languageControllerProvider =
    AsyncNotifierProvider<LanguageController, Locale?>(LanguageController.new);
