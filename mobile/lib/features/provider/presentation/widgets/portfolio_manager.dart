import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart' as picker;

import '../../../../core/network/api_config.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../data/provider_repository.dart';
import '../../domain/models/portfolio_photo.dart';
import '../../domain/models/provider_exception.dart';
import '../utils/provider_error_copy.dart';

/// Abstracts device photo selection behind one interface, so
/// [PortfolioManager] and any widget test can depend on it without ever
/// invoking the real `image_picker` platform channel -- mirrors
/// `LocationService`'s exact pattern (`shared/widgets/location_picker/
/// location_service.dart`, CUS-002).
abstract class PortfolioImagePicker {
  /// Returns the picked image file, or `null` if the user cancelled.
  Future<File?> pickImage();
}

/// The real, device-backed [PortfolioImagePicker] — wraps `image_picker`
/// directly. Used everywhere except widget tests.
class DevicePortfolioImagePicker implements PortfolioImagePicker {
  const DevicePortfolioImagePicker();

  @override
  Future<File?> pickImage() async {
    final picked = await picker.ImagePicker().pickImage(
      source: picker.ImageSource.gallery,
      imageQuality: 85,
    );
    return picked == null ? null : File(picked.path);
  }
}

final portfolioImagePickerProvider = Provider<PortfolioImagePicker>(
  (ref) => const DevicePortfolioImagePicker(),
);

/// The Storefront's Portfolio section (PRO-002, item 29,
/// `Plan_S04_PRO-002.md`) -- a list of the caller's existing photos with a
/// remove action and up/down reordering per photo (chosen over
/// drag-to-reorder as the simpler mechanism to make accessible,
/// `docs/AI/07_UI_GUIDELINES.md`'s touch-target rule), an "Add Photo"
/// action (picker → upload), and empty-state copy
/// (`docs/AI/16_UX_GUIDELINES.md`'s "why it's empty + one primary action"
/// formula) when there are no photos yet.
///
/// Unlike the other three Storefront sections, portfolio actions persist
/// immediately (add/remove/reorder each call their own endpoint the moment
/// they happen) rather than needing an explicit "Save" -- there's no
/// meaningful "draft" state for a photo list. [onPhotosChanged] keeps the
/// parent `StorefrontController` in sync with the server's authoritative
/// list after every action.
class PortfolioManager extends ConsumerStatefulWidget {
  const PortfolioManager({
    super.key,
    required this.photos,
    required this.onPhotosChanged,
  });

  final List<PortfolioPhoto> photos;
  final ValueChanged<List<PortfolioPhoto>> onPhotosChanged;

  @override
  ConsumerState<PortfolioManager> createState() => _PortfolioManagerState();
}

class _PortfolioManagerState extends ConsumerState<PortfolioManager> {
  bool _isBusy = false;
  ProviderException? _error;

  Future<void> _addPhoto() async {
    final imageFile = await ref.read(portfolioImagePickerProvider).pickImage();
    if (imageFile == null || !mounted) return;
    setState(() {
      _isBusy = true;
      _error = null;
    });
    try {
      final photo = await ref
          .read(providerRepositoryProvider)
          .uploadPortfolioPhoto(imageFile);
      if (!mounted) return;
      widget.onPhotosChanged([...widget.photos, photo]);
    } on ProviderException catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _removePhoto(PortfolioPhoto photo) async {
    setState(() {
      _isBusy = true;
      _error = null;
    });
    try {
      await ref.read(providerRepositoryProvider).deletePortfolioPhoto(photo.id);
      if (!mounted) return;
      widget.onPhotosChanged(
        widget.photos.where((existing) => existing.id != photo.id).toList(),
      );
    } on ProviderException catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _move(int index, int delta) async {
    final newIndex = index + delta;
    if (newIndex < 0 || newIndex >= widget.photos.length) return;
    final reordered = List<PortfolioPhoto>.of(widget.photos);
    final moved = reordered.removeAt(index);
    reordered.insert(newIndex, moved);

    setState(() {
      _isBusy = true;
      _error = null;
    });
    try {
      final saved = await ref
          .read(providerRepositoryProvider)
          .reorderPortfolio(reordered.map((photo) => photo.id).toList());
      if (!mounted) return;
      widget.onPhotosChanged(saved);
    } on ProviderException catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final photos = widget.photos;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_error != null) ...[
          AppErrorMessage(message: providerErrorMessage(context, _error!)),
          const SizedBox(height: AppSpacing.sm),
        ],
        if (photos.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
            child: Text(
              l10n.portfolioEmptyStateMessage,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          )
        else
          for (var index = 0; index < photos.length; index++)
            _PortfolioPhotoTile(
              key: ValueKey('portfolio-photo-${photos[index].id}'),
              photo: photos[index],
              canMoveUp: index > 0,
              canMoveDown: index < photos.length - 1,
              enabled: !_isBusy,
              onMoveUp: () => _move(index, -1),
              onMoveDown: () => _move(index, 1),
              onRemove: () => _removePhoto(photos[index]),
            ),
        const SizedBox(height: AppSpacing.sm),
        OutlinedButton.icon(
          onPressed: _isBusy ? null : _addPhoto,
          icon: _isBusy
              ? const LoadingIndicator(size: 16)
              : const Icon(Icons.add_photo_alternate_outlined),
          label: Text(l10n.addPhotoLabel),
        ),
      ],
    );
  }
}

/// One portfolio photo row: a thumbnail, its caption (if any), and
/// remove/reorder controls.
class _PortfolioPhotoTile extends StatelessWidget {
  const _PortfolioPhotoTile({
    super.key,
    required this.photo,
    required this.canMoveUp,
    required this.canMoveDown,
    required this.enabled,
    required this.onMoveUp,
    required this.onMoveDown,
    required this.onRemove,
  });

  final PortfolioPhoto photo;
  final bool canMoveUp;
  final bool canMoveDown;
  final bool enabled;
  final VoidCallback onMoveUp;
  final VoidCallback onMoveDown;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.small),
              child: Image.network(
                '${ApiConfig.mediaOrigin}${photo.mediaUrl}',
                width: 56,
                height: 56,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  width: 56,
                  height: 56,
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.broken_image_outlined),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                photo.caption ?? '',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            IconButton(
              tooltip: l10n.moveUpTooltip,
              icon: const Icon(Icons.arrow_upward),
              onPressed: enabled && canMoveUp ? onMoveUp : null,
            ),
            IconButton(
              tooltip: l10n.moveDownTooltip,
              icon: const Icon(Icons.arrow_downward),
              onPressed: enabled && canMoveDown ? onMoveDown : null,
            ),
            IconButton(
              tooltip: l10n.removePhotoTooltip,
              icon: const Icon(Icons.delete_outline),
              onPressed: enabled ? onRemove : null,
            ),
          ],
        ),
      ),
    );
  }
}
