import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../provider/data/provider_repository.dart';
import '../../../provider/domain/models/provider_exception.dart';
import '../../../provider/presentation/utils/provider_error_copy.dart';
import '../../domain/models/customer_profile.dart';
import '../../state/customer_profile_controller.dart';
import '../utils/customer_error_copy.dart';

/// S-14 — Profile & Settings, scoped to CUS-001's fields (display name,
/// avatar — a plain URL text field, no file-upload picker,
/// `Plan_S03_CUS-001.md` Decision 6 — a visible EN/AR language toggle with
/// immediate effect (AC6), and a notification-channel picker), CUS-002's
/// Saved Addresses entry point, plus PRO-001's "List Your Business" entry
/// point (the S-14 link slot CUS-001's own Plan named but explicitly
/// deferred, `Plan_S03_CUS-002.md` item 22 / `Plan_S04_PRO-001.md` item 32).
///
/// Deliberately does **not** add delete-account or legal-link entries —
/// those belong to their own not-yet-built stories (`Plan_S03_CUS-001.md`
/// Decision 7, out-of-scope list).
class ProfileSettingsScreen extends ConsumerStatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  ConsumerState<ProfileSettingsScreen> createState() =>
      _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends ConsumerState<ProfileSettingsScreen> {
  final _displayNameController = TextEditingController();
  final _avatarUrlController = TextEditingController();

  /// Only seeded once, the first time the profile finishes loading — a
  /// later provider rebuild (e.g. after a successful save) must never
  /// stomp on text the user is actively editing in the other field.
  bool _controllersSeeded = false;

  @override
  void dispose() {
    _displayNameController.dispose();
    _avatarUrlController.dispose();
    super.dispose();
  }

  void _seedControllers(CustomerProfile profile) {
    if (_controllersSeeded) return;
    _displayNameController.text = profile.displayName;
    _avatarUrlController.text = profile.avatarUrl ?? '';
    _controllersSeeded = true;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(customerProfileControllerProvider);
    final controller = ref.read(customerProfileControllerProvider.notifier);
    final profile = state.profile;

    if (profile != null) {
      _seedControllers(profile);
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.profileSettingsTitle)),
      body: SafeArea(
        child: profile == null
            ? _LoadOutcome(
                state: state,
                onRetry: () => controller.retry(),
                loadingLabel: l10n.loadingLabel,
              )
            : SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (state.error != null) ...[
                      AppErrorMessage(
                        message: customerProfileErrorMessage(
                          context,
                          state.error!,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),
                    ],
                    _EditableField(
                      label: l10n.profileDisplayNameLabel,
                      controller: _displayNameController,
                      enabled: !state.isSaving,
                      currentValue: profile.displayName,
                      saveTooltip: l10n.saveLabel,
                      allowEmpty: false,
                      onSave: (value) =>
                          controller.updateDisplayName(value.trim()),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    _EditableField(
                      label: l10n.profileAvatarUrlLabel,
                      hintText: l10n.profileAvatarUrlHint,
                      controller: _avatarUrlController,
                      enabled: !state.isSaving,
                      currentValue: profile.avatarUrl ?? '',
                      saveTooltip: l10n.saveLabel,
                      onSave: (value) =>
                          controller.updateAvatarUrl(value.trim()),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Text(
                      l10n.profileLanguageLabel,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    SegmentedButton<String>(
                      segments: [
                        ButtonSegment(
                          value: 'en',
                          label: Text(l10n.languageOptionEnglish),
                        ),
                        ButtonSegment(
                          value: 'ar',
                          label: Text(l10n.languageOptionArabic),
                        ),
                      ],
                      selected: {profile.language},
                      onSelectionChanged: state.isSaving
                          ? null
                          : (selection) => controller.updateLanguage(
                              Locale(selection.first),
                            ),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Text(
                      l10n.profileNotificationChannelLabel,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    RadioGroup<NotificationChannel>(
                      groupValue: profile.notificationChannel,
                      onChanged: (channel) {
                        if (!state.isSaving && channel != null) {
                          controller.updateNotificationChannel(channel);
                        }
                      },
                      child: Column(
                        children: [
                          _NotificationChannelOption(
                            icon: Icons.chat_bubble_outline,
                            label: l10n.notificationChannelWhatsapp,
                            channel: NotificationChannel.whatsapp,
                            enabled: !state.isSaving,
                          ),
                          _NotificationChannelOption(
                            icon: Icons.sms_outlined,
                            label: l10n.notificationChannelSms,
                            channel: NotificationChannel.sms,
                            enabled: !state.isSaving,
                          ),
                          _NotificationChannelOption(
                            icon: Icons.email_outlined,
                            label: l10n.notificationChannelEmail,
                            channel: NotificationChannel.email,
                            enabled: !state.isSaving,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Card(
                      margin: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.location_on_outlined),
                        title: Text(l10n.savedAddressesTitle),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push(AppRoutes.savedAddresses),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Card(
                      margin: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.storefront_outlined),
                        title: Text(l10n.listYourBusinessLabel),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => _onListYourBusiness(context),
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  /// Handles the "List Your Business" tile (PRO-001, item 32,
  /// `Plan_S04_PRO-001.md`; PRO-002, item 30, `Plan_S04_PRO-002.md`):
  /// checks `getMyProvider()` first -- if the caller already has a
  /// listing, navigates to the Storefront screen (S-25) to manage it
  /// (this branch previously only showed a snackbar, PRO-001 Decision 9);
  /// otherwise navigates to the onboarding intro (S-15).
  Future<void> _onListYourBusiness(BuildContext context) async {
    try {
      final existing = await ref
          .read(providerRepositoryProvider)
          .getMyProvider();
      if (!context.mounted) return;
      if (existing != null) {
        context.push(AppRoutes.storefront);
        return;
      }
      context.push(AppRoutes.providerIntro);
    } on ProviderException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(providerErrorMessage(context, error))),
      );
    }
  }
}

/// Loading spinner or a retry-able error state — rendered only until the
/// initial `GET /customers/me` resolves (afterwards, [state.error] is
/// rendered inline above the form instead, so a failed *save* never hides
/// the rest of the screen).
class _LoadOutcome extends StatelessWidget {
  const _LoadOutcome({
    required this.state,
    required this.onRetry,
    required this.loadingLabel,
  });

  final CustomerProfileState state;
  final VoidCallback onRetry;
  final String loadingLabel;

  @override
  Widget build(BuildContext context) {
    if (state.error != null) {
      final l10n = AppLocalizations.of(context);
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AppErrorMessage(
                message: customerProfileErrorMessage(context, state.error!),
              ),
              const SizedBox(height: AppSpacing.md),
              OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
            ],
          ),
        ),
      );
    }
    return Center(child: LoadingIndicator(label: loadingLabel));
  }
}

/// A text field paired with an explicit per-field save action — enabled
/// only once the field's text actually differs from the server's current
/// value, so a no-op tap never fires a `PATCH` with nothing to change.
class _EditableField extends StatefulWidget {
  const _EditableField({
    required this.label,
    required this.controller,
    required this.enabled,
    required this.currentValue,
    required this.saveTooltip,
    required this.onSave,
    this.hintText,
    this.allowEmpty = true,
  });

  final String label;
  final String? hintText;
  final TextEditingController controller;
  final bool enabled;
  final String currentValue;
  final String saveTooltip;
  final ValueChanged<String> onSave;

  /// `display_name` is `NOT NULL` server-side — its field passes `false`
  /// so the save action stays disabled on a blank/whitespace-only value,
  /// instead of round-tripping a guaranteed-422 `PATCH`. `avatar_url` is
  /// nullable and passes `true` (an empty value is a valid "clear it").
  final bool allowEmpty;

  @override
  State<_EditableField> createState() => _EditableFieldState();
}

class _EditableFieldState extends State<_EditableField> {
  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() => setState(() {});

  bool get _isDirty => widget.controller.text != widget.currentValue;

  bool get _canSave =>
      _isDirty &&
      (widget.allowEmpty || widget.controller.text.trim().isNotEmpty);

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: AppTextField(
            label: widget.label,
            hintText: widget.hintText,
            controller: widget.controller,
            enabled: widget.enabled,
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Padding(
          padding: const EdgeInsets.only(top: AppSpacing.sm),
          child: IconButton(
            icon: const Icon(Icons.check),
            tooltip: widget.saveTooltip,
            onPressed: widget.enabled && _canSave
                ? () => widget.onSave(widget.controller.text)
                : null,
          ),
        ),
      ],
    );
  }
}

/// One row of the notification-channel picker (`RadioListTile` rather than
/// a horizontal `SegmentedButton`, deliberately — three options with the
/// longer Arabic labels this screen needs would risk an `RenderFlex`
/// overflow at narrow widths; a vertical list has no such ceiling).
///
/// Its selection/change handling comes from the ancestor
/// [RadioGroup]<[NotificationChannel]> the screen wraps these tiles in
/// (the modern, non-deprecated replacement for passing `groupValue`/
/// `onChanged` to every individual [RadioListTile]).
class _NotificationChannelOption extends StatelessWidget {
  const _NotificationChannelOption({
    required this.icon,
    required this.label,
    required this.channel,
    required this.enabled,
  });

  final IconData icon;
  final String label;
  final NotificationChannel channel;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return RadioListTile<NotificationChannel>(
      value: channel,
      enabled: enabled,
      secondary: Icon(icon),
      title: Text(label),
      contentPadding: EdgeInsets.zero,
    );
  }
}
