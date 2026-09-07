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
import '../../domain/models/auth_token.dart';
import '../../domain/models/otp_entry_args.dart';
import '../../state/auth_session_controller.dart';
import '../../state/oauth_sign_in_controller.dart';
import '../../state/phone_entry_controller.dart';
import '../utils/auth_error_copy.dart';

/// S-03 — Sign In / Sign Up. Offers Google, Apple, and mobile-number paths
/// (AC1) — Google/Apple wired to [OAuthSignInController] (AUTH-002), mobile
/// number wired to [PhoneEntryController] (AUTH-001).
class PhoneEntryScreen extends ConsumerStatefulWidget {
  const PhoneEntryScreen({super.key});

  @override
  ConsumerState<PhoneEntryScreen> createState() => _PhoneEntryScreenState();
}

class _PhoneEntryScreenState extends ConsumerState<PhoneEntryScreen> {
  late final TextEditingController _countryCodeController;
  late final TextEditingController _phoneController;
  bool _touched = false;

  @override
  void initState() {
    super.initState();
    final initial = ref.read(phoneEntryControllerProvider);
    _countryCodeController = TextEditingController(text: initial.countryCode);
    _phoneController = TextEditingController(text: initial.phoneNumber);
  }

  @override
  void dispose() {
    _countryCodeController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(phoneEntryControllerProvider);
    final controller = ref.read(phoneEntryControllerProvider.notifier);
    final oauthState = ref.watch(oauthSignInControllerProvider);

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.xl),
              Text(
                l10n.phoneEntryTitle,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                l10n.phoneEntrySubtitle,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: AppSpacing.xl),
              _OAuthOptionButton(
                label: l10n.continueWithGoogle,
                icon: Icons.g_mobiledata,
                isLoading: oauthState.isLoading(OAuthProvider.google),
                onPressed: oauthState.loadingProvider == null
                    ? _onGoogleSignIn
                    : null,
              ),
              const SizedBox(height: AppSpacing.sm),
              _OAuthOptionButton(
                label: l10n.continueWithApple,
                icon: Icons.apple,
                isLoading: oauthState.isLoading(OAuthProvider.apple),
                onPressed: oauthState.loadingProvider == null
                    ? _onAppleSignIn
                    : null,
              ),
              if (oauthState.error != null) ...[
                const SizedBox(height: AppSpacing.md),
                AppErrorMessage(
                  message: authErrorMessage(context, oauthState.error!),
                ),
              ],
              const SizedBox(height: AppSpacing.lg),
              Row(
                children: [
                  const Expanded(child: Divider()),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                    ),
                    child: Text(l10n.orDividerLabel),
                  ),
                  const Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: AppSpacing.lg),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 96,
                    child: AppTextField(
                      label: l10n.countryCodeFieldLabel,
                      controller: _countryCodeController,
                      keyboardType: TextInputType.phone,
                      onChanged: (value) {
                        controller.updateCountryCode(value);
                        setState(() => _touched = true);
                      },
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: AppTextField(
                      label: l10n.phoneNumberFieldLabel,
                      hintText: l10n.phoneNumberFieldHint,
                      controller: _phoneController,
                      keyboardType: TextInputType.phone,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      onChanged: (value) {
                        controller.updatePhoneNumber(value);
                        setState(() => _touched = true);
                      },
                    ),
                  ),
                ],
              ),
              if (_touched && !state.isValid) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  !state.isCountryCodeValid
                      ? l10n.countryCodeInvalidError
                      : l10n.phoneNumberInvalidError,
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
                label: l10n.continueWithMobileNumber,
                isLoading: state.isSubmitting,
                onPressed: state.isValid ? () => _onSubmit(controller) : null,
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                l10n.termsAndPrivacyNotice,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _onSubmit(PhoneEntryController controller) async {
    setState(() => _touched = true);
    final succeeded = await controller.submit();
    if (!mounted || !succeeded) return;

    final state = ref.read(phoneEntryControllerProvider);
    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(l10n.otpSentConfirmation)));

    final OtpEntryArgs args = (
      countryCode: state.countryCode,
      phoneNumber: state.phoneNumber,
      expiresInSeconds: state.otpExpiresInSeconds,
    );
    context.push(AppRoutes.otpEntry, extra: args);
  }

  Future<void> _onGoogleSignIn() async {
    final controller = ref.read(oauthSignInControllerProvider.notifier);
    final token = await controller.signInWithGoogle();
    await _handleOAuthResult(token);
  }

  Future<void> _onAppleSignIn() async {
    final controller = ref.read(oauthSignInControllerProvider.notifier);
    final token = await controller.signInWithApple();
    await _handleOAuthResult(token);
  }

  Future<void> _handleOAuthResult(AuthToken? token) async {
    if (!mounted || token == null) return;
    await ref.read(authSessionControllerProvider).setSession(token);
    if (!mounted) return;
    // Session is already fully live at this point (CUS-002, AC4) — routes
    // to the skippable first-address prompt (S-05) instead of Home
    // directly; skipping there still reaches Home with no blocking step.
    context.go(AppRoutes.addFirstAddress);
  }
}

/// A real, tappable Google/Apple sign-in option (AC1) — replaces AUTH-001's
/// disabled "coming soon" placeholder. Shows a loading spinner in place of
/// its label while its own sign-in is in flight, and is disabled while
/// *any* provider is loading (guards against a double-tap starting two
/// concurrent native sign-in flows).
class _OAuthOptionButton extends StatelessWidget {
  const _OAuthOptionButton({
    required this.label,
    required this.icon,
    required this.isLoading,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final bool isLoading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? LoadingIndicator(size: 20, label: label)
          : Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon),
                const SizedBox(width: AppSpacing.sm),
                Text(label),
              ],
            ),
    );
  }
}
