import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/claim_exception.dart';
import '../../domain/models/claim_review_reason.dart';
import '../../state/claim_otp_controller.dart';
import '../utils/claim_error_copy.dart';

/// S-22 — Claim OTP Verification (CLM-001, AC4/AC5/AC6).
///
/// Requests an OTP against the target listing's own public phone number as
/// soon as this screen opens (AC4) -- copy never displays the actual
/// number (AC4's spirit: the claimant is proving they already have access
/// to it, not being told what it is). If the listing has no public number
/// at all, [ClaimOtpController] skips the code-entry UI entirely and
/// auto-submits the admin-review fallback (AC6's no-public-number case).
///
/// The "This isn't working" link is always visible once code entry is
/// showing -- never gated behind a failure count (AC6, matching S-22's
/// literal screen spec).
class ClaimOtpScreen extends ConsumerStatefulWidget {
  const ClaimOtpScreen({super.key, required this.providerId});

  final String providerId;

  @override
  ConsumerState<ClaimOtpScreen> createState() => _ClaimOtpScreenState();
}

class _ClaimOtpScreenState extends ConsumerState<ClaimOtpScreen> {
  late final TextEditingController _codeController;

  @override
  void initState() {
    super.initState();
    _codeController = TextEditingController();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  ClaimOtpController get _controller =>
      ref.read(claimOtpControllerProvider(widget.providerId).notifier);

  Future<void> _onVerify() async {
    final result = await _controller.verify();
    if (!mounted || result == null) return;
    // The screen itself renders the success state below (ClaimOtpStatus
    // .claimed) -- no navigation happens here; "Continue to Verification"
    // is that state's own action.
  }

  Future<void> _onResend() async {
    await _controller.resend();
    if (!mounted) return;
    final state = ref.read(claimOtpControllerProvider(widget.providerId));
    if (state.error == null) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.otpSentConfirmation)));
    }
  }

  Future<void> _onNotWorkingTapped() async {
    final reason = await showModalBottomSheet<ClaimReviewReason>(
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
                  sheetL10n.claimReviewSheetTitle,
                  style: Theme.of(sheetContext).textTheme.titleMedium,
                ),
              ),
              ListTile(
                title: Text(sheetL10n.claimReviewReasonNoCodeLabel),
                onTap: () =>
                    Navigator.of(sheetContext).pop(ClaimReviewReason.otpFailed),
              ),
              ListTile(
                title: Text(sheetL10n.claimReviewReasonWrongNumberLabel),
                onTap: () =>
                    Navigator.of(sheetContext).pop(ClaimReviewReason.otpFailed),
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
          ),
        );
      },
    );
    if (reason == null || !mounted) return;
    await _controller.submitReviewReason(reason);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(claimOtpControllerProvider(widget.providerId));

    return Scaffold(
      appBar: AppBar(title: Text(l10n.claimOtpTitle)),
      body: SafeArea(
        child: switch (state.status) {
          ClaimOtpStatus.requestingOtp || ClaimOtpStatus.submittingReview =>
            Center(child: LoadingIndicator(label: l10n.loadingLabel)),
          ClaimOtpStatus.error => _ErrorState(
            error: state.error!,
            onRetry: () => _controller.retryInitialRequest(),
          ),
          ClaimOtpStatus.reviewConfirmed => const _ReviewConfirmedState(),
          ClaimOtpStatus.claimed => const _ClaimedSuccessState(),
          ClaimOtpStatus.codeEntry => _CodeEntryView(
            state: state,
            codeController: _codeController,
            onCodeChanged: _controller.updateCode,
            onVerify: _onVerify,
            onResend: _onResend,
            onNotWorkingTapped: _onNotWorkingTapped,
          ),
        },
      ),
    );
  }
}

class _CodeEntryView extends StatelessWidget {
  const _CodeEntryView({
    required this.state,
    required this.codeController,
    required this.onCodeChanged,
    required this.onVerify,
    required this.onResend,
    required this.onNotWorkingTapped,
  });

  final ClaimOtpState state;
  final TextEditingController codeController;
  final ValueChanged<String> onCodeChanged;
  final VoidCallback onVerify;
  final VoidCallback onResend;
  final VoidCallback onNotWorkingTapped;

  String _formatDuration(int totalSeconds) {
    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.claimOtpSubtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.xl),
          AppTextField(
            label: l10n.otpCodeFieldLabel,
            controller: codeController,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ],
            maxLength: 6,
            onChanged: onCodeChanged,
          ),
          if (state.code.isNotEmpty && !state.isCodeComplete) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              l10n.otpIncompleteError,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          if (state.error != null) ...[
            AppErrorMessage(message: claimErrorMessage(context, state.error!)),
            const SizedBox(height: AppSpacing.md),
          ],
          PrimaryButton(
            label: l10n.verifyLabel,
            isLoading: state.isVerifying,
            onPressed: state.isCodeComplete ? onVerify : null,
          ),
          const SizedBox(height: AppSpacing.lg),
          Center(
            child: state.canResend
                ? TextButton(
                    onPressed: state.isResending ? null : onResend,
                    child: state.isResending
                        ? LoadingIndicator(size: 18, label: l10n.loadingLabel)
                        : Text(l10n.resendCodeLabel),
                  )
                : Text(
                    l10n.resendCodeCountdown(
                      _formatDuration(state.remainingSeconds),
                    ),
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
          ),
          const SizedBox(height: AppSpacing.sm),
          // AC6 -- always visible, never gated behind a failure count.
          Center(
            child: TextButton(
              key: const ValueKey('claim-otp-not-working-link'),
              onPressed: onNotWorkingTapped,
              child: Text(l10n.claimNotWorkingLinkLabel),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});

  final ClaimException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(message: claimErrorMessage(context, error)),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
          ],
        ),
      ),
    );
  }
}

/// AC6 -- shown after `request-admin-review` succeeds, whether triggered
/// manually from the "This isn't working" sheet or automatically for a
/// listing with no public phone number on record.
class _ReviewConfirmedState extends StatelessWidget {
  const _ReviewConfirmedState();

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
            Icon(
              Icons.hourglass_top_outlined,
              size: 64,
              color: colorScheme.primary,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              l10n.claimReviewConfirmedTitle,
              key: const ValueKey('claim-review-confirmed-title'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              l10n.claimReviewConfirmedMessage,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

/// AC5 -- shown after a successful `verify-otp` finalizes the claim.
/// Points the claimant toward VER-001's document submission flow (the same
/// Verification gate a self-registered Business goes through) rather than
/// silently landing on any generic screen.
class _ClaimedSuccessState extends StatelessWidget {
  const _ClaimedSuccessState();

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
            Icon(
              Icons.check_circle_outline,
              size: 64,
              color: colorScheme.primary,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              l10n.claimSuccessTitle,
              key: const ValueKey('claim-success-title'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              l10n.claimSuccessMessage,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: AppSpacing.xl),
            PrimaryButton(
              label: l10n.claimContinueToVerificationLabel,
              onPressed: () => context.go(AppRoutes.verificationUpload),
            ),
          ],
        ),
      ),
    );
  }
}
