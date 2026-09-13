import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_config.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/outcome_tag_exception.dart';
import '../../state/outcome_tag_prompt_controller.dart';
import '../utils/outcome_tag_error_copy.dart';

/// The Outcome Tag Prompt bottom sheet (REV-001, AC1/AC3) --
/// `docs/AI/DESIGN.md`'s `bottom-sheet` component, per
/// `15_SCREEN_INVENTORY.md`'s spec: "Provider name/photo, Yes/No" with a
/// "Yes / No" primary action. Opened directly after the Contact Reveal
/// sheet closes on a real reveal (Decision 6, `Plan_S09_REV-001.md`) --
/// never in parallel with it, and never via a Notifications Inbox
/// tap-through, since none exists.
///
/// Submits `hired=true`/`hired=false` on Yes/No, then closes the sheet.
/// "Maybe later" (and any other dismiss path -- swipe-down, tap-outside)
/// closes the sheet with **zero** network calls -- it never reads or
/// touches [outcomeTagPromptControllerProvider] at all (Decision 7, a hard
/// requirement).
class OutcomeTagPromptSheet extends ConsumerStatefulWidget {
  const OutcomeTagPromptSheet({
    super.key,
    required this.contactViewId,
    required this.providerDisplayName,
    this.providerPhotoUrl,
  });

  final String contactViewId;
  final String providerDisplayName;
  final String? providerPhotoUrl;

  /// Opens this sheet via `showModalBottomSheet`, per
  /// `07_UI_GUIDELINES.md`/`DESIGN.md`'s bottom-sheet convention, mirroring
  /// `ContactRevealSheet.show`'s identical shape.
  static Future<void> show(
    BuildContext context, {
    required String contactViewId,
    required String providerDisplayName,
    String? providerPhotoUrl,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppRadius.bottomSheet),
        ),
      ),
      builder: (context) => OutcomeTagPromptSheet(
        contactViewId: contactViewId,
        providerDisplayName: providerDisplayName,
        providerPhotoUrl: providerPhotoUrl,
      ),
    );
  }

  @override
  ConsumerState<OutcomeTagPromptSheet> createState() =>
      _OutcomeTagPromptSheetState();
}

class _OutcomeTagPromptSheetState extends ConsumerState<OutcomeTagPromptSheet> {
  /// How long the brief "Thanks!" confirmation is shown before the sheet
  /// auto-closes on a successful submission -- a minor UX-completeness
  /// detail, not itself an AC requirement.
  static const _autoCloseDelay = Duration(milliseconds: 700);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = outcomeTagPromptControllerProvider(widget.contactViewId);

    ref.listen(provider, (previous, next) {
      if (next.status == OutcomeTagPromptStatus.submitted) {
        // Captured synchronously, before the async gap below -- avoids
        // using [context] itself once the delay has elapsed.
        final navigator = Navigator.of(context);
        Future.delayed(_autoCloseDelay, () {
          if (mounted) navigator.pop();
        });
        return;
      }
      if (next.status == OutcomeTagPromptStatus.error &&
          !_isRecoverable(next.error)) {
        // A 404/409 -- both mean "nothing more to do here" from the
        // customer's point of view (Plan's Frontend item 1). Close
        // quietly rather than surfacing a scary error.
        Navigator.of(context).pop();
      }
    });

    final state = ref.watch(provider);

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          top: AppSpacing.lg,
          bottom: AppSpacing.lg + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: switch (state.status) {
          OutcomeTagPromptStatus.submitted => _ConfirmationContent(l10n: l10n),
          OutcomeTagPromptStatus.error when _isRecoverable(state.error) =>
            _ErrorContent(
              error: state.error!,
              onRetry: () => ref.read(provider.notifier).retry(),
            ),
          _ => _PromptContent(
            l10n: l10n,
            providerDisplayName: widget.providerDisplayName,
            providerPhotoUrl: widget.providerPhotoUrl,
            isSubmitting: state.status == OutcomeTagPromptStatus.submitting,
            onYes: () => ref.read(provider.notifier).submit(hired: true),
            onNo: () => ref.read(provider.notifier).submit(hired: false),
            onMaybeLater: () => Navigator.of(context).pop(),
          ),
        },
      ),
    );
  }

  /// Only a genuine network/unknown failure is worth showing as an inline
  /// error with retry -- a 404/`notFound` or 409/`alreadyExists` is an
  /// effectively-unreachable edge case in the normal flow, handled instead
  /// by quietly closing the sheet (see [build]'s `ref.listen`).
  bool _isRecoverable(OutcomeTagException? error) {
    return error?.type == OutcomeTagErrorType.network ||
        error?.type == OutcomeTagErrorType.unknown;
  }
}

class _PromptContent extends StatelessWidget {
  const _PromptContent({
    required this.l10n,
    required this.providerDisplayName,
    required this.providerPhotoUrl,
    required this.isSubmitting,
    required this.onYes,
    required this.onNo,
    required this.onMaybeLater,
  });

  final AppLocalizations l10n;
  final String providerDisplayName;
  final String? providerPhotoUrl;
  final bool isSubmitting;
  final VoidCallback onYes;
  final VoidCallback onNo;
  final VoidCallback onMaybeLater;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            _ProviderPhoto(photoUrl: providerPhotoUrl),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                providerDisplayName,
                key: const ValueKey('outcome-tag-prompt-provider-name'),
                style: textTheme.titleMedium,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          l10n.outcomeTagPromptTitle,
          style: textTheme.titleLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        PrimaryButton(
          key: const ValueKey('outcome-tag-prompt-yes-button'),
          label: l10n.outcomeTagPromptYesLabel,
          isLoading: isSubmitting,
          onPressed: isSubmitting ? null : onYes,
        ),
        const SizedBox(height: AppSpacing.sm),
        OutlinedButton(
          key: const ValueKey('outcome-tag-prompt-no-button'),
          onPressed: isSubmitting ? null : onNo,
          child: Text(l10n.outcomeTagPromptNoLabel),
        ),
        const SizedBox(height: AppSpacing.sm),
        TextButton(
          key: const ValueKey('outcome-tag-prompt-maybe-later-button'),
          onPressed: isSubmitting ? null : onMaybeLater,
          child: Text(l10n.outcomeTagPromptMaybeLaterLabel),
        ),
      ],
    );
  }
}

class _ProviderPhoto extends StatelessWidget {
  const _ProviderPhoto({required this.photoUrl});

  final String? photoUrl;

  static const double _size = 48;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final photoUrl = this.photoUrl;
    final placeholder = CircleAvatar(
      radius: _size / 2,
      backgroundColor: colorScheme.surfaceContainerHighest,
      child: Icon(
        Icons.storefront_outlined,
        color: colorScheme.onSurfaceVariant,
      ),
    );

    return SizedBox(
      key: const ValueKey('outcome-tag-prompt-provider-photo'),
      height: _size,
      width: _size,
      child: photoUrl == null
          ? placeholder
          : ClipOval(
              child: Image.network(
                '${ApiConfig.mediaOrigin}$photoUrl',
                height: _size,
                width: _size,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => placeholder,
              ),
            ),
    );
  }
}

class _ErrorContent extends StatelessWidget {
  const _ErrorContent({required this.error, required this.onRetry});

  final OutcomeTagException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AppErrorMessage(message: outcomeTagErrorMessage(context, error)),
        const SizedBox(height: AppSpacing.md),
        OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
      ],
    );
  }
}

class _ConfirmationContent extends StatelessWidget {
  const _ConfirmationContent({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 96,
      child: Center(
        child: Text(
          l10n.outcomeTagPromptThanksMessage,
          key: const ValueKey('outcome-tag-prompt-confirmation'),
          style: Theme.of(context).textTheme.titleMedium,
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
