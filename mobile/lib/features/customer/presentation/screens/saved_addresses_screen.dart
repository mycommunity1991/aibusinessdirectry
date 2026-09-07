import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/models/address_form_args.dart';
import '../../domain/models/address_form_mode.dart';
import '../../domain/models/saved_address.dart';
import '../../domain/models/saved_address_exception.dart';
import '../../state/saved_addresses_controller.dart';
import '../utils/saved_address_error_copy.dart';

/// S-12 — Saved Addresses (`Plan_S03_CUS-002.md` item 19). Lists all of the
/// caller's own addresses with the default clearly badged (AC6), supports
/// edit (tap a row) and delete (an Undo snackbar, per
/// `docs/AI/16_UX_GUIDELINES.md`'s named example — never a confirmation
/// dialog), and drives AC7's post-delete-of-default flow (Decision 8): a
/// "choose a new default" bottom sheet if other addresses remain, or a
/// clear inline "No default address set" indicator otherwise.
class SavedAddressesScreen extends ConsumerStatefulWidget {
  const SavedAddressesScreen({super.key});

  @override
  ConsumerState<SavedAddressesScreen> createState() =>
      _SavedAddressesScreenState();
}

class _SavedAddressesScreenState extends ConsumerState<SavedAddressesScreen> {
  /// Addresses hidden from the list while their Undo window is open —
  /// nothing is actually deleted server-side until the window expires
  /// without an Undo tap (Decision 8).
  final Set<String> _pendingDeleteIds = {};

  Future<void> _onAdd() async {
    final AddressFormArgs args = (
      mode: AddressFormMode.add,
      existingAddress: null,
      subtitle: null,
    );
    final result = await context.push<bool>(AppRoutes.addressForm, extra: args);
    if (result == true) {
      await ref.read(savedAddressesControllerProvider.notifier).refresh();
    }
  }

  Future<void> _onEdit(SavedAddress address) async {
    final AddressFormArgs args = (
      mode: AddressFormMode.edit,
      existingAddress: address,
      subtitle: null,
    );
    final result = await context.push<bool>(AppRoutes.addressForm, extra: args);
    if (result == true) {
      await ref.read(savedAddressesControllerProvider.notifier).refresh();
    }
  }

  /// How long the Undo snackbar stays up before a delete is finalized
  /// (Decision 8) — driven by our own timer (matching the snackbar's
  /// `duration`) rather than `SnackBar.closed`, whose real dismissal
  /// timing depends on animation completion and isn't reliably
  /// fast-forwardable in widget tests.
  static const _undoWindow = Duration(seconds: 4);

  /// Safety margin added on top of [_undoWindow] before the delete is
  /// actually finalized. The real on-screen `SnackBar` only starts
  /// counting its own `duration` after its entrance transition completes,
  /// and only fully disappears (Undo no longer tappable) after its exit
  /// transition finishes — together, up to ~500ms beyond `duration` on a
  /// real device. Without this margin, a user tapping "Undo" in that
  /// window would see a still-visible, still-tappable button that
  /// silently no-ops because the delete had already been finalized
  /// underneath it (found by `tester` during CUS-002 verification). This
  /// margin guarantees finalize can never fire before the real snackbar
  /// (and its Undo action) has visually and functionally gone away.
  static const _finalizeSafetyMargin = Duration(milliseconds: 500);
  static final _finalizeDelay = _undoWindow + _finalizeSafetyMargin;

  void _onDelete(SavedAddress address) {
    setState(() => _pendingDeleteIds.add(address.id));
    final l10n = AppLocalizations.of(context);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        duration: _undoWindow,
        content: Text(l10n.addressDeletedSnackbar),
        action: SnackBarAction(
          label: l10n.undoLabel,
          onPressed: () {
            if (mounted) {
              setState(() => _pendingDeleteIds.remove(address.id));
            }
          },
        ),
      ),
    );

    Future.delayed(_finalizeDelay, () => _finalizeDelete(address));
  }

  Future<void> _finalizeDelete(SavedAddress address) async {
    if (!mounted || !_pendingDeleteIds.contains(address.id)) {
      // Undo was tapped in the meantime.
      return;
    }
    final controller = ref.read(savedAddressesControllerProvider.notifier);
    await controller.deleteAddress(address.id);
    if (!mounted) return;
    setState(() => _pendingDeleteIds.remove(address.id));

    if (address.isDefault) {
      await _promptForNewDefaultIfNeeded();
    }
  }

  /// AC7: after deleting what was the default address, offer a bottom
  /// sheet to choose a new one from whatever remains — but only if
  /// something remains to choose from. An empty remaining list needs no
  /// prompt; the screen's own empty state already makes "no default" self-
  /// evident (Decision 8).
  Future<void> _promptForNewDefaultIfNeeded() async {
    final remaining = ref.read(savedAddressesControllerProvider).value ?? [];
    if (remaining.isEmpty || !mounted) return;

    final chosenId = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) {
        final sheetL10n = AppLocalizations.of(sheetContext);
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Text(
                  sheetL10n.chooseNewDefaultTitle,
                  style: Theme.of(sheetContext).textTheme.titleMedium,
                ),
              ),
              ...remaining.map(
                (a) => ListTile(
                  title: Text(
                    a.label?.isNotEmpty == true ? a.label! : a.addressLine,
                  ),
                  subtitle: Text(a.addressLine),
                  onTap: () => Navigator.of(sheetContext).pop(a.id),
                ),
              ),
              ListTile(
                title: Text(sheetL10n.notNowLabel),
                onTap: () => Navigator.of(sheetContext).pop(),
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
          ),
        );
      },
    );

    if (chosenId != null && mounted) {
      await ref
          .read(savedAddressesControllerProvider.notifier)
          .setDefault(chosenId);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final addressesAsync = ref.watch(savedAddressesControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.savedAddressesTitle)),
      floatingActionButton: FloatingActionButton(
        onPressed: _onAdd,
        tooltip: l10n.addAddressLabel,
        child: const Icon(Icons.add),
      ),
      body: SafeArea(
        child: addressesAsync.when(
          loading: () =>
              Center(child: LoadingIndicator(label: l10n.loadingLabel)),
          error: (error, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: AppErrorMessage(
                message: savedAddressErrorMessage(
                  context,
                  error is SavedAddressException
                      ? error
                      : const SavedAddressException(
                          type: SavedAddressErrorType.unknown,
                        ),
                ),
              ),
            ),
          ),
          data: (addresses) {
            final visible = addresses
                .where((a) => !_pendingDeleteIds.contains(a.id))
                .toList();

            if (visible.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Text(
                    l10n.savedAddressesEmptyState,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              );
            }

            final hasDefault = visible.any((a) => a.isDefault);

            return ListView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              children: [
                if (!hasDefault) ...[
                  Text(
                    l10n.noDefaultAddressLabel,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: AppSpacing.md),
                ],
                for (final address in visible) ...[
                  _SavedAddressCard(
                    address: address,
                    onEdit: () => _onEdit(address),
                    onDelete: () => _onDelete(address),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _SavedAddressCard extends StatelessWidget {
  const _SavedAddressCard({
    required this.address,
    required this.onEdit,
    required this.onDelete,
  });

  final SavedAddress address;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: ListTile(
        onTap: onEdit,
        title: Row(
          children: [
            Expanded(
              child: Text(
                address.label?.isNotEmpty == true
                    ? address.label!
                    : address.addressLine,
              ),
            ),
            if (address.isDefault) ...[
              const SizedBox(width: AppSpacing.sm),
              Chip(
                label: Text(l10n.defaultAddressBadgeLabel),
                backgroundColor: colorScheme.primaryContainer,
                labelStyle: TextStyle(color: colorScheme.onPrimaryContainer),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ],
        ),
        subtitle: Text(address.addressLine),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: l10n.editAddressTooltip,
              onPressed: onEdit,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: l10n.deleteAddressTooltip,
              onPressed: onDelete,
            ),
          ],
        ),
      ),
    );
  }
}
