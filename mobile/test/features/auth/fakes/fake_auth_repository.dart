import 'package:ai_marketplace_app/features/auth/data/auth_repository.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_exception.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_token.dart';
import 'package:ai_marketplace_app/features/auth/domain/models/auth_user.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [AuthRepository] — no real Dio/network calls
/// are ever made. The base [Dio] passed to `super` is never touched since
/// every public method is overridden below.
class FakeAuthRepository extends AuthRepository {
  FakeAuthRepository({
    this.requestOtpError,
    this.verifyOtpError,
    this.requestOtpExpiresInSeconds,
    AuthToken? tokenToReturn,
  }) : _tokenToReturn = tokenToReturn ?? _defaultToken,
       super(Dio());

  static final _defaultToken = AuthToken(
    accessToken: 'test-access-token',
    tokenType: 'bearer',
    user: const AuthUser(
      id: 'user-1',
      phoneCountryCode: '+971',
      phoneNumber: '501234567',
      status: 'active',
      preferredLanguage: 'en',
      roles: ['customer'],
    ),
  );

  final AuthException? requestOtpError;
  final AuthException? verifyOtpError;
  final AuthToken _tokenToReturn;

  /// The `expires_in_seconds` this fake's `requestOtp` resolves with —
  /// `null` by default, matching a not-yet-known/unspecified server value
  /// in tests that don't care about it.
  final int? requestOtpExpiresInSeconds;

  int requestOtpCallCount = 0;
  int verifyOtpCallCount = 0;

  @override
  Future<int?> requestOtp({
    required String phoneCountryCode,
    required String phoneNumber,
  }) async {
    requestOtpCallCount++;
    if (requestOtpError != null) {
      throw requestOtpError!;
    }
    return requestOtpExpiresInSeconds;
  }

  @override
  Future<AuthToken> verifyOtp({
    required String phoneCountryCode,
    required String phoneNumber,
    required String code,
  }) async {
    verifyOtpCallCount++;
    if (verifyOtpError != null) {
      throw verifyOtpError!;
    }
    return _tokenToReturn;
  }
}
