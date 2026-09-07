import 'package:ai_marketplace_app/features/customer/data/saved_address_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address_exception.dart';
import 'package:dio/dio.dart';

/// A hermetic test double for [SavedAddressRepository] — no real Dio/network
/// calls are ever made. Mirrors `fake_customer_repository.dart`'s pattern,
/// but also enforces AC2 (default-uniqueness) and AC7 (no auto-promotion on
/// delete) in-memory, the same way the real backend does, so widget tests
/// exercising those flows don't need a real server.
class FakeSavedAddressRepository extends SavedAddressRepository {
  FakeSavedAddressRepository({
    List<SavedAddress>? initialAddresses,
    this.listError,
    this.createError,
    this.updateError,
    this.deleteError,
  }) : _addresses = List.of(initialAddresses ?? const []),
       super(Dio());

  final List<SavedAddress> _addresses;

  /// The failure `list` throws, if any.
  final SavedAddressException? listError;

  /// The failure `create` throws, if any.
  final SavedAddressException? createError;

  /// The failure `update` throws, if any.
  final SavedAddressException? updateError;

  /// The failure `delete` throws, if any.
  final SavedAddressException? deleteError;

  int listCallCount = 0;
  int createCallCount = 0;
  int updateCallCount = 0;
  int deleteCallCount = 0;
  String? lastDeletedId;

  int _nextId = 1;

  @override
  Future<List<SavedAddress>> list() async {
    listCallCount++;
    if (listError != null) {
      throw listError!;
    }
    return List.unmodifiable(_addresses);
  }

  @override
  Future<SavedAddress> create({
    String? label,
    required String addressLine,
    String? city,
    String? region,
    required String countryCode,
    required double latitude,
    required double longitude,
    bool isDefault = false,
  }) async {
    createCallCount++;
    if (createError != null) {
      throw createError!;
    }
    if (isDefault) {
      _unsetOtherDefaults();
    }
    final address = SavedAddress(
      id: 'address-${_nextId++}',
      label: label,
      addressLine: addressLine,
      city: city,
      region: region,
      countryCode: countryCode,
      latitude: latitude,
      longitude: longitude,
      isDefault: isDefault,
    );
    _addresses.add(address);
    return address;
  }

  @override
  Future<SavedAddress> update(
    String addressId, {
    String? label,
    String? addressLine,
    String? city,
    String? region,
    String? countryCode,
    double? latitude,
    double? longitude,
    bool? isDefault,
  }) async {
    updateCallCount++;
    if (updateError != null) {
      throw updateError!;
    }
    final index = _addresses.indexWhere((a) => a.id == addressId);
    if (index == -1) {
      throw const SavedAddressException(type: SavedAddressErrorType.notFound);
    }
    if (isDefault == true) {
      _unsetOtherDefaults();
    }
    final existing = _addresses[index];
    final updated = SavedAddress(
      id: existing.id,
      label: label ?? existing.label,
      addressLine: addressLine ?? existing.addressLine,
      city: city ?? existing.city,
      region: region ?? existing.region,
      countryCode: countryCode ?? existing.countryCode,
      latitude: latitude ?? existing.latitude,
      longitude: longitude ?? existing.longitude,
      isDefault: isDefault ?? existing.isDefault,
    );
    _addresses[index] = updated;
    return updated;
  }

  @override
  Future<void> delete(String addressId) async {
    deleteCallCount++;
    lastDeletedId = addressId;
    if (deleteError != null) {
      throw deleteError!;
    }
    // Mirrors the real backend (Decision 3/AC7): soft-delete only, never
    // auto-promotes a new default.
    _addresses.removeWhere((a) => a.id == addressId);
  }

  void _unsetOtherDefaults() {
    for (var i = 0; i < _addresses.length; i++) {
      if (_addresses[i].isDefault) {
        _addresses[i] = _addresses[i].copyWith(isDefault: false);
      }
    }
  }
}
