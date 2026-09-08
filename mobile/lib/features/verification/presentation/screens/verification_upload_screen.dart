import 'dart:io';

import 'package:file_picker/file_picker.dart' as file_picker;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart' as picker;

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/document_type.dart';
import '../../domain/models/verification_confirm_args.dart';
import '../../state/verification_upload_controller.dart';
import '../utils/verification_error_copy.dart';

/// Abstracts device document selection behind one interface so
/// [VerificationUploadScreen] and any widget test can depend on it
/// without ever invoking a real platform channel -- mirrors
/// `PortfolioImagePicker`'s exact pattern
/// (`features/provider/presentation/widgets/portfolio_manager.dart`).
abstract class VerificationDocumentPicker {
  /// Captures a fresh photo via the device camera, or `null` if
  /// cancelled.
  Future<File?> pickFromCamera();

  /// Browses the device's existing files (images or PDFs -- a trade
  /// license is plausibly a PDF), or `null` if cancelled.
  Future<File?> pickFromFiles();
}

/// The real, device-backed [VerificationDocumentPicker]. Used everywhere
/// except widget tests.
class DeviceVerificationDocumentPicker implements VerificationDocumentPicker {
  const DeviceVerificationDocumentPicker();

  @override
  Future<File?> pickFromCamera() async {
    final picked = await picker.ImagePicker().pickImage(
      source: picker.ImageSource.camera,
      imageQuality: 85,
    );
    return picked == null ? null : File(picked.path);
  }

  @override
  Future<File?> pickFromFiles() async {
    final result = await file_picker.FilePicker.pickFiles(
      type: file_picker.FileType.custom,
      allowedExtensions: const ['jpg', 'jpeg', 'png', 'webp', 'pdf'],
    );
    final path = result?.files.single.path;
    return path == null ? null : File(path);
  }
}

final verificationDocumentPickerProvider = Provider<VerificationDocumentPicker>(
  (ref) => const DeviceVerificationDocumentPicker(),
);

/// S-19 -- Verification Upload (VER-001, item 27,
/// `Plan_S05_VER-001.md`). Freelancer providers must submit an Emirates
/// ID with no choice of document type (AC2); Business providers may
/// choose a document type or, per Decision 3's default config, skip the
/// document entirely. Reached either right after PRO-001's onboarding
/// wizard completes, or from the Storefront's verification-status link
/// (Decision, Mobile item 30).
class VerificationUploadScreen extends ConsumerWidget {
  const VerificationUploadScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(verificationUploadControllerProvider);
    final controller = ref.read(verificationUploadControllerProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.verificationUploadTitle)),
      body: SafeArea(
        child: state.isLoadingProviderType
            ? Center(child: LoadingIndicator(label: l10n.loadingLabel))
            : SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      l10n.verificationUploadBody,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    if (state.error != null) ...[
                      AppErrorMessage(
                        message: verificationErrorMessage(
                          context,
                          state.error!,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    if (state.isFreelancer)
                      Text(
                        l10n.verificationDocumentTypeEmiratesIdOnlyMessage,
                        style: Theme.of(context).textTheme.titleSmall,
                      )
                    else
                      _DocumentTypeSelector(
                        selected: state.documentType,
                        onChanged: controller.setDocumentType,
                      ),
                    if (!state.isFreelancer) ...[
                      const SizedBox(height: AppSpacing.lg),
                      SwitchListTile(
                        key: const ValueKey('verification-skip-document'),
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.verificationSkipDocumentLabel),
                        value: state.skipDocument,
                        onChanged: (value) => controller.setSkipDocument(value),
                      ),
                    ],
                    if (!state.skipDocument) ...[
                      const SizedBox(height: AppSpacing.lg),
                      _PickedFilePreview(file: state.pickedFile),
                      const SizedBox(height: AppSpacing.md),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: state.isBusy
                                  ? null
                                  : () => _pickFromCamera(ref, controller),
                              icon: const Icon(Icons.photo_camera_outlined),
                              label: Text(l10n.takePhotoLabel),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: state.isBusy
                                  ? null
                                  : () => _pickFromFiles(ref, controller),
                              icon: const Icon(Icons.attach_file),
                              label: Text(l10n.chooseFileLabel),
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    PrimaryButton(
                      label: l10n.continueLabel,
                      isLoading: state.isBusy,
                      onPressed: _canContinue(state) && !state.isBusy
                          ? () => _onContinue(context, controller, state)
                          : null,
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  Future<void> _pickFromCamera(
    WidgetRef ref,
    VerificationUploadController controller,
  ) async {
    final file = await ref
        .read(verificationDocumentPickerProvider)
        .pickFromCamera();
    if (file != null) controller.setPickedFile(file);
  }

  Future<void> _pickFromFiles(
    WidgetRef ref,
    VerificationUploadController controller,
  ) async {
    final file = await ref
        .read(verificationDocumentPickerProvider)
        .pickFromFiles();
    if (file != null) controller.setPickedFile(file);
  }

  bool _canContinue(VerificationUploadState state) {
    if (state.skipDocument) return true;
    return state.pickedFile != null;
  }

  Future<void> _onContinue(
    BuildContext context,
    VerificationUploadController controller,
    VerificationUploadState state,
  ) async {
    if (state.skipDocument) {
      final ok = await controller.submitWithoutDocument();
      if (!context.mounted || !ok) return;
      context.go(AppRoutes.verificationStatus);
      return;
    }

    final preview = await controller.previewPickedFile();
    if (!context.mounted || preview == null) return;
    context.push(
      AppRoutes.verificationConfirm,
      extra: VerificationConfirmArgs(
        documentType: state.documentType,
        file: state.pickedFile!,
        preview: preview,
      ),
    );
  }
}

/// A document-type chooser, shown only to Business providers (Freelancer
/// is always fixed to Emirates ID, AC2) -- `ChoiceChip`s over a dropdown
/// since there are only three, bounded options.
class _DocumentTypeSelector extends StatelessWidget {
  const _DocumentTypeSelector({
    required this.selected,
    required this.onChanged,
  });

  final DocumentType selected;
  final ValueChanged<DocumentType> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.verificationDocumentTypeLabel,
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            for (final type in DocumentType.values)
              ChoiceChip(
                key: ValueKey('document-type-${type.wireValue}'),
                label: Text(_labelFor(l10n, type)),
                selected: selected == type,
                onSelected: (_) => onChanged(type),
              ),
          ],
        ),
      ],
    );
  }

  String _labelFor(AppLocalizations l10n, DocumentType type) => switch (type) {
    DocumentType.emiratesId => l10n.documentTypeEmiratesIdLabel,
    DocumentType.tradeLicense => l10n.documentTypeTradeLicenseLabel,
    DocumentType.other => l10n.documentTypeOtherLabel,
  };
}

/// A local thumbnail of the picked file -- rendered from the device's own
/// file reference, never a fetched server URL (the pending-slot file is
/// private, Decision 7). Images render as a thumbnail; anything else
/// (a PDF trade license) shows a generic file row with its name.
class _PickedFilePreview extends StatelessWidget {
  const _PickedFilePreview({required this.file});

  final File? file;

  bool _isImage(String path) {
    final lower = path.toLowerCase();
    return lower.endsWith('.jpg') ||
        lower.endsWith('.jpeg') ||
        lower.endsWith('.png') ||
        lower.endsWith('.webp');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final currentFile = file;
    if (currentFile == null) {
      return Text(
        l10n.verificationNoFileSelectedMessage,
        style: Theme.of(context).textTheme.bodyMedium,
      );
    }
    if (_isImage(currentFile.path)) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.small),
        child: Image.file(
          currentFile,
          height: 160,
          width: double.infinity,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) => Container(
            height: 160,
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: const Icon(Icons.broken_image_outlined),
          ),
        ),
      );
    }
    return Row(
      children: [
        const Icon(Icons.insert_drive_file_outlined),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Text(
            currentFile.uri.pathSegments.isNotEmpty
                ? currentFile.uri.pathSegments.last
                : currentFile.path,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
