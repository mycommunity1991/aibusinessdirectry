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
import '../../domain/models/otp_entry_args.dart';
import '../../state/auth_session_controller.dart';
import '../../state/otp_entry_controller.dart';
import '../utils/auth_error_copy.dart';

/// S-04 — Mobile OTP Entry. 6-digit code entry with live validation and a
/// single 5:00 countdown that both gates "Resend" and matches the OTP's
/// actual server-side expiry (AC9).
class OtpEntryScreen extends ConsumerStatefulWidget {
  const OtpEntryScreen({
    super.key,
    required this.countryCode,
    required this.phoneNumber,
  });

  final String countryCode;
  final String phoneNumber;

  @override
  ConsumerState<OtpEntryScreen> createState() => _OtpEntryScreenState();
}

class _OtpEntryScreenState extends ConsumerState<OtpEntryScreen> {
  late final TextEditingController _codeController;
  late final OtpEntryArgs _args;

  @override
  void initState() {
    super.initState();
    _args = (countryCode: widget.countryCode, phoneNumber: widget.phoneNumber);
    _codeController = TextEditingController();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(otpEntryControllerProvider(_args));
    final controller = ref.read(otpEntryControllerProvider(_args).notifier);
    final fullPhone = '${widget.countryCode} ${widget.phoneNumber}';

    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l10n.otpEntryTitle,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                l10n.otpEntrySubtitle(fullPhone),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: AppSpacing.xl),
              AppTextField(
                label: l10n.otpCodeFieldLabel,
                controller: _codeController,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                maxLength: 6,
                onChanged: controller.updateCode,
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
                AppErrorMessage(
                  message: authErrorMessage(context, state.error!),
                ),
                const SizedBox(height: AppSpacing.md),
              ],
              PrimaryButton(
                label: l10n.verifyLabel,
                isLoading: state.isVerifying,
                onPressed: state.isCodeComplete
                    ? () => _onVerify(controller)
                    : null,
              ),
              const SizedBox(height: AppSpacing.lg),
              Center(
                child: state.canResend
                    ? TextButton(
                        onPressed: state.isResending
                            ? null
                            : () => _onResend(controller),
                        child: state.isResending
                            ? LoadingIndicator(
                                size: 18,
                                label: l10n.loadingLabel,
                              )
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
              Center(
                child: TextButton(
                  onPressed: () => context.pop(),
                  child: Text(l10n.otpChangeNumberLabel),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _onVerify(OtpEntryController controller) async {
    final token = await controller.verify();
    if (!mounted || token == null) return;

    ref.read(authSessionProvider.notifier).state = token;
    context.go(AppRoutes.homePlaceholder);
  }

  Future<void> _onResend(OtpEntryController controller) async {
    await controller.resend();
    if (!mounted) return;

    final state = ref.read(otpEntryControllerProvider(_args));
    if (state.error == null) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.otpSentConfirmation)));
    }
  }

  String _formatDuration(int totalSeconds) {
    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }
}
