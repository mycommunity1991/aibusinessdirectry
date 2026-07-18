/// Networking configuration for the backend API.
///
/// Source of truth: `docs/AI/05_API_GUIDELINES.md` — Base URL / API Architecture.
class ApiConfig {
  const ApiConfig._();

  static const String _defaultBaseUrl = 'http://localhost:8000/api/v1';

  /// The API base URL, configurable at build/run time via:
  /// `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1`
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: _defaultBaseUrl,
  );

  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 15);
}
