import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../data/verification_repository.dart';
import '../../domain/models/submit_verification_request.dart';
import '../../domain/models/verification_confirm_args.dart';
import '../../domain/models/verification_exception.dart';
import '../utils/verification_error_copy.dart';

/// The "OCR confirm" step AC4 describes (VER-001, item 28,
/// `Plan_S05_VER-001.md`) -- editable fields pre-filled from the preview
/// response, which is **always empty** today (Decision 6, the OCR pass is
/// a stub that never actually reads anything). The copy below must read
/// honestly as "we couldn't read this automatically yet, please fill it
/// in yourself" -- never "here's what we read," which would imply a real
/// extraction happened. Submitting sends exactly what the user typed/
/// edited here, never the (empty) preview response (AC8).
class VerificationConfirmScreen extends ConsumerStatefulWidget {
  const VerificationConfirmScreen({super.key, required this.args});

  final VerificationConfirmArgs args;

  @override
  ConsumerState<VerificationConfirmScreen> createState() =>
      _VerificationConfirmScreenState();
}

class _VerificationConfirmScreenState
    extends ConsumerState<VerificationConfirmScreen> {
  late final _fullNameController = TextEditingController(
    text: widget.args.preview.fullName ?? '',
  );
  late final _idNumberController = TextEditingController(
    text: widget.args.preview.idNumber ?? '',
  );
  late final _expiryDateController = TextEditingController(
    text: widget.args.preview.expiryDate ?? '',
  );

  bool _isSubmitting = false;
  VerificationException? _error;

  @override
  void dispose() {
    _fullNameController.dispose();
    _idNumberController.dispose();
    _expiryDateController.dispose();
    super.dispose();
  }

  bool _isImage(String path) {
    final lower = path.toLowerCase();
    return lower.endsWith('.jpg') ||
        lower.endsWith('.jpeg') ||
        lower.endsWith('.png') ||
        lower.endsWith('.webp');
  }

  Future<void> _onSubmit() async {
    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    final fullName = _fullNameController.text.trim();
    final idNumber = _idNumberController.text.trim();
    final expiryDate = _expiryDateController.text.trim();

    try {
      // Always the user's own submitted/edited values -- never
      // `widget.args.preview`'s (always-empty) fields (AC8).
      await ref
          .read(verificationRepositoryProvider)
          .submit(
            SubmitVerificationRequest(
              documentType: widget.args.documentType,
              fullName: fullName.isEmpty ? null : fullName,
              idNumber: idNumber.isEmpty ? null : idNumber,
              expiryDate: expiryDate.isEmpty ? null : expiryDate,
            ),
          );
      if (!mounted) return;
      context.go(AppRoutes.verificationStatus);
    } on VerificationException catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final file = widget.args.file;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.verificationConfirmTitle)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_isImage(file.path))
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.small),
                  child: Image.file(
                    file,
                    height: 160,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Container(
                      height: 160,
                      color: colorScheme.surfaceContainerHighest,
                      child: const Icon(Icons.broken_image_outlined),
                    ),
                  ),
                )
              else
                Row(
                  children: [
                    const Icon(Icons.insert_drive_file_outlined),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Text(
                        file.uri.pathSegments.isNotEmpty
                            ? file.uri.pathSegments.last
                            : file.path,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: AppSpacing.lg),
              // Decision 6's honesty requirement -- must never imply a
              // real OCR read happened.
              Container(
                key: const ValueKey('verification-ocr-honesty-notice'),
                padding: const EdgeInsets.all(AppSpacing.sm),
                decoration: BoxDecoration(
                  color: colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(AppRadius.small),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.info_outline,
                      color: colorScheme.onSurfaceVariant,
                      size: 20,
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    Expanded(
                      child: Text(
                        l10n.verificationOcrHonestyNotice,
                        style: TextStyle(color: colorScheme.onSurfaceVariant),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              if (_error != null) ...[
                AppErrorMessage(
                  message: verificationErrorMessage(context, _error!),
                ),
                const SizedBox(height: AppSpacing.md),
              ],
              AppTextField(
                label: l10n.verificationFullNameFieldLabel,
                controller: _fullNameController,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.verificationIdNumberFieldLabel,
                controller: _idNumberController,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.verificationExpiryDateFieldLabel,
                hintText: l10n.verificationExpiryDateFieldHint,
                controller: _expiryDateController,
              ),
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                label: l10n.submitLabel,
                isLoading: _isSubmitting,
                onPressed: _isSubmitting ? null : _onSubmit,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
