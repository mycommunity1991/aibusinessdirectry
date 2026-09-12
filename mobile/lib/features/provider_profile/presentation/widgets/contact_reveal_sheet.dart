import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/contact_exception.dart';
import '../../domain/models/contact_reveal.dart';
import '../../domain/models/provider_profile_args.dart';
import '../../state/contact_reveal_controller.dart';
import '../utils/contact_error_copy.dart';
import '../utils/contact_launcher.dart';

/// The Contact Reveal bottom sheet (CON-001, AC2/AC6) --
/// `docs/AI/DESIGN.md`'s `bottom-sheet` component, used "for Contact Reveal
/// ... specifically" per its own doc comment. Calls `POST /contact-views`
/// the moment it opens (via [ContactRevealController]) and, on success,
/// immediately shows the phone number plus Call/WhatsApp buttons -- no
/// quote request, approval wait, or in-app messaging step exists anywhere
/// in this flow (AC2). Always includes the "contact happens outside the
/// app" note (AC6).
class ContactRevealSheet extends ConsumerWidget {
  const ContactRevealSheet({super.key, required this.args});

  final ProviderProfileArgs args;

  /// Opens this sheet via `showModalBottomSheet`, per
  /// `07_UI_GUIDELINES.md`/`DESIGN.md`'s bottom-sheet convention for
  /// contextual actions rather than a full screen or dialog.
  static Future<void> show(BuildContext context, ProviderProfileArgs args) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppRadius.bottomSheet),
        ),
      ),
      builder: (context) => ContactRevealSheet(args: args),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(contactRevealControllerProvider(args));

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          top: AppSpacing.lg,
          bottom: AppSpacing.lg + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: switch (state.status) {
          ContactRevealStatus.loading => _LoadingContent(l10n: l10n),
          ContactRevealStatus.error => _ErrorContent(
            error: state.error!,
            onRetry: () => ref
                .read(contactRevealControllerProvider(args).notifier)
                .retry(),
          ),
          ContactRevealStatus.loaded => _RevealedContent(reveal: state.reveal!),
        },
      ),
    );
  }
}

class _LoadingContent extends StatelessWidget {
  const _LoadingContent({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 160,
      child: Center(
        child: LoadingIndicator(
          key: const ValueKey('contact-reveal-loading'),
          label: l10n.loadingLabel,
        ),
      ),
    );
  }
}

class _ErrorContent extends StatelessWidget {
  const _ErrorContent({required this.error, required this.onRetry});

  final ContactException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AppErrorMessage(message: contactErrorMessage(context, error)),
        const SizedBox(height: AppSpacing.md),
        OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
      ],
    );
  }
}

class _RevealedContent extends ConsumerWidget {
  const _RevealedContent({required this.reveal});

  final ContactReveal reveal;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;
    final launcher = ref.read(contactLauncherProvider);
    final fullPhoneNumber = reveal.fullPhoneNumber;
    final whatsappNumber = reveal.whatsappNumber;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          l10n.contactSheetTitle,
          style: textTheme.titleLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          fullPhoneNumber ?? l10n.contactSheetNoPhoneNumberMessage,
          key: const ValueKey('contact-reveal-phone-number'),
          style: textTheme.headlineSmall,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.lg),
        PrimaryButton(
          key: const ValueKey('contact-reveal-call-button'),
          label: l10n.contactSheetCallLabel,
          icon: Icons.call,
          onPressed: fullPhoneNumber == null
              ? null
              : () => launcher.launchCall(fullPhoneNumber.replaceAll(' ', '')),
        ),
        if (whatsappNumber != null) ...[
          const SizedBox(height: AppSpacing.sm),
          OutlinedButton.icon(
            key: const ValueKey('contact-reveal-whatsapp-button'),
            onPressed: () => launcher.launchWhatsApp(
              whatsappNumber.replaceAll(RegExp(r'[^0-9]'), ''),
            ),
            icon: const Icon(Icons.chat_outlined),
            label: Text(l10n.contactSheetWhatsAppLabel),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.info_outline,
              size: 16,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: Text(
                l10n.contactSheetOutsideAppNote,
                key: const ValueKey('contact-reveal-outside-app-note'),
                style: textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
