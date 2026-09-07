import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/saved_address_repository.dart';
import '../domain/models/saved_address.dart';

/// Manages the Saved Addresses screen's (S-12) list — load, and refresh
/// after create/edit/delete (`Plan_S03_CUS-002.md` item 16).
class SavedAddressesController
    extends AutoDisposeAsyncNotifier<List<SavedAddress>> {
  @override
  Future<List<SavedAddress>> build() {
    return ref.watch(savedAddressRepositoryProvider).list();
  }

  /// Re-fetches the list — used after any create/edit/delete so the screen
  /// always reflects the server's authoritative state (in particular,
  /// which address — if any — is currently default, AC7).
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(savedAddressRepositoryProvider).list(),
    );
  }

  /// Permanently (server-side: soft-)deletes [addressId], then refreshes
  /// the list. Callers (the screen) are responsible for the Undo-snackbar
  /// delay before invoking this (`Plan_S03_CUS-002.md` Decision 8) — by the
  /// time this is called, the delete is final.
  Future<void> deleteAddress(String addressId) async {
    await ref.read(savedAddressRepositoryProvider).delete(addressId);
    await refresh();
  }

  /// Marks [addressId] as the default address (AC7's "choose a new
  /// default" bottom sheet action), then refreshes the list.
  Future<void> setDefault(String addressId) async {
    await ref
        .read(savedAddressRepositoryProvider)
        .update(addressId, isDefault: true);
    await refresh();
  }
}

final savedAddressesControllerProvider =
    AsyncNotifierProvider.autoDispose<
      SavedAddressesController,
      List<SavedAddress>
    >(SavedAddressesController.new);
