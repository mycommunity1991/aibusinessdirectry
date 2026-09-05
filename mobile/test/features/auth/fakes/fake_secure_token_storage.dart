import 'package:ai_marketplace_app/core/storage/secure_token_storage.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';

/// A hermetic, in-memory test double for [SecureTokenStorage] — no real
/// `flutter_secure_storage` platform channel is ever touched. Overrides
/// every public method, mirroring [FakeAuthRepository]'s
/// extend-and-override pattern.
class FakeSecureTokenStorage extends SecureTokenStorage {
  FakeSecureTokenStorage({AuthToken? initialToken}) : _token = initialToken;

  AuthToken? _token;

  int writeCallCount = 0;
  int clearCallCount = 0;

  @override
  Future<AuthToken?> read() async => _token;

  @override
  Future<void> write(AuthToken token) async {
    writeCallCount++;
    _token = token;
  }

  @override
  Future<void> clear() async {
    clearCallCount++;
    _token = null;
  }
}
