import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../data/verification_repository.dart';
import '../../domain/models/document_type.dart';
import '../../domain/models/verification_document.dart';
import '../../domain/models/verification_exception.dart';
import '../../domain/models/verification_record.dart';
import '../../state/verification_status_controller.dart';
import '../utils/verification_error_copy.dart';

/// S-20 -- Verification Status (VER-001, item 29, `Plan_S05_VER-001.md`).
/// Shows the caller's own current verification cycle (AC6) -- a plain-
/// language status per `docs/AI/16_UX_GUIDELINES.md`'s internal-to-user-
/// facing copy mapping table, an empty/first-time state with a "Start
/// Verification" CTA when nothing has been submitted yet, and a
/// "Resubmit" action after a rejection that routes back to S-19 (AC7 --
/// resubmission always creates a fresh cycle, never mutates the rejected
/// one).
class VerificationStatusScreen extends ConsumerWidget {
  const VerificationStatusScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(verificationStatusControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.verificationStatusTitle)),
      body: SafeArea(
        child: state.isLoading
            ? Center(child: LoadingIndicator(label: l10n.loadingLabel))
            : state.error != null
            ? _LoadError(error: state.error!)
            : state.record == null
            ? const _EmptyState()
            : _StatusContent(record: state.record!),
      ),
    );
  }
}

class _LoadError extends ConsumerWidget {
  const _LoadError({required this.error});

  final VerificationException error;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(message: verificationErrorMessage(context, error)),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(
              onPressed: () => ref
                  .read(verificationStatusControllerProvider.notifier)
                  .load(),
              child: Text(l10n.retryLabel),
            ),
          ],
        ),
      ),
    );
  }
}

/// Shown when [VerificationStatusController]'s `getMyCurrentStatus()`
/// returns `null` -- "you haven't submitted yet" is a normal, expected
/// first-time state, not an error (per
/// `docs/AI/16_UX_GUIDELINES.md`'s "why it's empty + one primary action"
/// formula).
class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.verified_outlined, size: 64, color: colorScheme.primary),
            const SizedBox(height: AppSpacing.lg),
            Text(
              l10n.verificationNotSubmittedMessage,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: AppSpacing.lg),
            PrimaryButton(
              label: l10n.startVerificationLabel,
              onPressed: () => context.push(AppRoutes.verificationUpload),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusContent extends StatelessWidget {
  const _StatusContent({required this.record});

  final VerificationRecord record;

  String _bodyFor(AppLocalizations l10n, VerificationRecord record) =>
      switch (record.status) {
        VerificationRecordStatus.pending ||
        VerificationRecordStatus.underReview =>
          l10n.verificationUnderReviewMessage,
        VerificationRecordStatus.approved => l10n.verificationApprovedMessage,
        VerificationRecordStatus.rejected =>
          record.rejectionReason ?? l10n.verificationRejectedMessage,
      };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _StatusBadge(status: record.status),
          const SizedBox(height: AppSpacing.md),
          Text(
            _bodyFor(l10n, record),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (record.status == VerificationRecordStatus.rejected) ...[
            const SizedBox(height: AppSpacing.xl),
            PrimaryButton(
              label: l10n.resubmitLabel,
              onPressed: () => context.push(AppRoutes.verificationUpload),
            ),
          ],
          if (record.documents.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.xl),
            Text(
              l10n.verificationSubmittedDocumentsLabel,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            for (final document in record.documents)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                child: _DocumentPreview(document: document),
              ),
          ],
        ],
      ),
    );
  }
}

/// A compact status badge -- "Pending"/"Under Review" both render as "in
/// review" copy per `16_UX_GUIDELINES.md`'s mapping table.
class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final VerificationRecordStatus status;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final (label, background, icon) = switch (status) {
      VerificationRecordStatus.pending ||
      VerificationRecordStatus.underReview => (
        l10n.verificationStatusUnderReviewBadge,
        colorScheme.secondaryContainer,
        Icons.hourglass_top_outlined,
      ),
      VerificationRecordStatus.approved => (
        l10n.verificationStatusApprovedBadge,
        colorScheme.primaryContainer,
        Icons.verified_outlined,
      ),
      VerificationRecordStatus.rejected => (
        l10n.verificationStatusRejectedBadge,
        colorScheme.errorContainer,
        Icons.error_outline,
      ),
    };
    return Container(
      key: const ValueKey('verification-status-badge'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadius.small),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18),
          const SizedBox(width: AppSpacing.xs),
          Text(label, style: Theme.of(context).textTheme.labelLarge),
        ],
      ),
    );
  }
}

/// A submitted document's in-app preview -- fetched via
/// [VerificationRepository.getDocumentBytes] and rendered with
/// `Image.memory`, **never** a raw `Image.network`/direct-URL call
/// (Decision 7, the document is private). Falls back to a generic file
/// icon for anything `Image.memory` can't decode (a PDF trade license).
class _DocumentPreview extends ConsumerWidget {
  const _DocumentPreview({required this.document});

  final VerificationDocument document;

  String _labelFor(AppLocalizations l10n, DocumentType type) => switch (type) {
    DocumentType.emiratesId => l10n.documentTypeEmiratesIdLabel,
    DocumentType.tradeLicense => l10n.documentTypeTradeLicenseLabel,
    DocumentType.other => l10n.documentTypeOtherLabel,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return Card(
      key: ValueKey('verification-document-${document.id}'),
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Row(
          children: [
            SizedBox(
              width: 56,
              height: 56,
              child: FutureBuilder<List<int>>(
                future: ref
                    .read(verificationRepositoryProvider)
                    .getDocumentBytes(document.id),
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Center(child: LoadingIndicator(size: 20));
                  }
                  final bytes = snapshot.data;
                  if (bytes == null) {
                    return const Icon(Icons.insert_drive_file_outlined);
                  }
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(AppRadius.small),
                    child: Image.memory(
                      Uint8List.fromList(bytes),
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) =>
                          const Icon(Icons.insert_drive_file_outlined),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: Text(_labelFor(l10n, document.documentType))),
          ],
        ),
      ),
    );
  }
}
