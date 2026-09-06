import 'package:ai_marketplace_app/features/customer/data/customer_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/customer_profile.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/customer_profile_exception.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [CustomerRepository] — no real Dio/network
/// calls are ever made. Mirrors
/// `test/features/auth/fakes/fake_auth_repository.dart`'s pattern.
class FakeCustomerRepository extends CustomerRepository {
  FakeCustomerRepository({
    CustomerProfile? profile,
    this.getMyProfileError,
    this.updateMyProfileError,
  }) : _profile = profile ?? defaultProfile,
       super(Dio());

  /// A representative "just registered" default — matches the backend's
  /// own defaults (Decision 6, `Plan_S03_CUS-001.md`: placeholder display
  /// name, no avatar, WhatsApp channel, English).
  static const defaultProfile = CustomerProfile(
    id: 'profile-1',
    displayName: 'New Customer',
    avatarUrl: null,
    language: 'en',
    notificationChannel: NotificationChannel.whatsapp,
  );

  CustomerProfile _profile;

  /// The failure `getMyProfile` throws, if any.
  final CustomerProfileException? getMyProfileError;

  /// The failure `updateMyProfile` throws, if any.
  final CustomerProfileException? updateMyProfileError;

  int getMyProfileCallCount = 0;
  int updateMyProfileCallCount = 0;

  /// The exact arguments of the most recent `updateMyProfile` call, keyed
  /// by parameter name — lets a test assert precisely which fields were
  /// (and weren't) sent, without needing to inspect a raw JSON payload.
  Map<String, dynamic>? lastUpdateArgs;

  @override
  Future<CustomerProfile> getMyProfile() async {
    getMyProfileCallCount++;
    if (getMyProfileError != null) {
      throw getMyProfileError!;
    }
    return _profile;
  }

  @override
  Future<CustomerProfile> updateMyProfile({
    String? displayName,
    String? avatarUrl,
    bool clearAvatarUrl = false,
    String? language,
    NotificationChannel? notificationChannel,
  }) async {
    updateMyProfileCallCount++;
    lastUpdateArgs = {
      'displayName': displayName,
      'avatarUrl': avatarUrl,
      'clearAvatarUrl': clearAvatarUrl,
      'language': language,
      'notificationChannel': notificationChannel,
    };
    if (updateMyProfileError != null) {
      throw updateMyProfileError!;
    }
    _profile = CustomerProfile(
      id: _profile.id,
      displayName: displayName ?? _profile.displayName,
      avatarUrl: clearAvatarUrl ? null : (avatarUrl ?? _profile.avatarUrl),
      language: language ?? _profile.language,
      notificationChannel: notificationChannel ?? _profile.notificationChannel,
    );
    return _profile;
  }
}
