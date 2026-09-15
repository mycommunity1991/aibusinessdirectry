import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/data/unread_notification_count_repository.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../auth/state/auth_session_controller.dart';
import '../../../customer/data/saved_address_repository.dart';
import '../../../customer/domain/models/address_form_mode.dart';
import '../../../customer/domain/models/saved_address_exception.dart';

/// Minimal placeholder landed on after a successful `verify-otp`.
///
/// Full Home (S-06) belongs to a future Customer Core Loop story — this
/// stub exists only so AUTH-001 has somewhere authenticated to land. Its
/// only added behavior (AUTH-003) is a bare "Log out" action — no dedicated
/// "Manage Sessions" screen is built this story (Plan Decision 11).
///
/// The app-bar person icon is a temporary entry point to Profile & Settings
/// (S-14, CUS-001) — not a bottom-nav tab, since the real 3-tab
/// Home/Activity/Profile shell needs real Home/Activity screens that don't
/// exist yet (`Plan_S03_CUS-001.md` Decision 7).
///
/// The "Find a Service" button still enforces CUS-002's address-required
/// gate (AC5, unchanged) — but as of DIR-001 (`Plan_S06_DIR-001.md`
/// Decision 6), once a saved address exists it opens the real, structured
/// Search Filters screen instead of showing a "coming soon" snackbar. As of
/// AI-001 (`Plan_S07_AI-001.md` Decision 7), the real AI Conversation entry
/// point (S-06/S-07) also exists here, opening `AiConversationScreen`
/// directly — the guided, free-text intake path alongside "Find a
/// Service"'s structured browse. As of `ENG-001`
/// (`Plan_S12_ENG-001.md`, Decision 10/Open Question 4), a "Notifications"
/// entry-point tile also lives here — this is the only screen every
/// authenticated account of any role currently lands on, unlike
/// `storefront`/`profileSettings` which are role-specific.
class HomePlaceholderScreen extends ConsumerWidget {
  const HomePlaceholderScreen({super.key});

  Future<void> _onLogOut(WidgetRef ref, BuildContext context) async {
    final accessToken = ref.read(authSessionProvider)?.accessToken;
    await ref.read(authRepositoryProvider).logout(accessToken);
    await ref.read(authSessionControllerProvider).clear();
    if (context.mounted) {
      context.go(AppRoutes.phoneEntry);
    }
  }

  Future<void> _onFindService(WidgetRef ref, BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    try {
      final addresses = await ref.read(savedAddressRepositoryProvider).list();
      if (!context.mounted) return;
      if (addresses.isEmpty) {
        // AC5: re-prompt for an address (non-skippable this time) instead
        // of proceeding -- unchanged from CUS-002.
        await context.push<bool>(
          AppRoutes.addressForm,
          extra: (
            mode: AddressFormMode.add,
            existingAddress: null,
            subtitle: l10n.addressRequiredForSearchSubtitle,
          ),
        );
      } else {
        // DIR-001, Decision 6: the real Search Filters screen replaces the
        // prior "coming soon" snackbar now that it exists.
        context.push(AppRoutes.searchFilters);
      }
    } on SavedAddressException {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.genericErrorMessage)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: l10n.profileSettingsTooltip,
            onPressed: () => context.push(AppRoutes.profileSettings),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 64,
                color: colorScheme.primary,
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                l10n.homePlaceholderTitle,
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                l10n.homePlaceholderMessage,
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xl),
              // ENG-001, Frontend item 2 -- the Notifications entry-point
              // tile with a live unread-count badge (AC5/AC6).
              const _NotificationsEntryPointCard(),
              const SizedBox(height: AppSpacing.lg),
              // AI-001, Mobile item 27 -- the AI Conversation entry point
              // (S-06/S-07, Decision 7), alongside the existing structured
              // "Find a Service" browse path and the Claim entry point.
              OutlinedButton(
                onPressed: () => context.push(AppRoutes.aiConversation),
                child: Text(l10n.aiConversationEntryPointLabel),
              ),
              const SizedBox(height: AppSpacing.md),
              OutlinedButton(
                onPressed: () => _onFindService(ref, context),
                child: Text(l10n.findServiceButtonLabel),
              ),
              const SizedBox(height: AppSpacing.md),
              // CLM-001, Mobile item 39 -- a secondary entry point into the
              // Claim flow (S-21), reachable independent of stumbling onto
              // an unclaimed listing's card while browsing search results.
              TextButton(
                onPressed: () => context.push(AppRoutes.claimSearch),
                child: Text(l10n.claimEntryPointLabel),
              ),
              const SizedBox(height: AppSpacing.md),
              TextButton(
                onPressed: () => _onLogOut(ref, context),
                child: Text(l10n.logOutLabel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// `ENG-001`'s "Notifications" entry point tile -- mirrors
/// `_LeadsEntryPointCard`'s own shape exactly
/// (`features/provider/presentation/screens/storefront_screen.dart`): a
/// tappable card reading only the [AppRoutes.notificationsInbox] constant,
/// never importing anything from `features/notifications/`
/// (`docs/AI/02_ARCHITECTURE.md`'s "Features must not depend directly on
/// each other" rule) -- the live unread-count badge instead reads the
/// independent `shared/data/unread_notification_count_repository.dart`
/// (mirroring `_VerificationStatusChip`'s identical "shared, deliberately
/// independent read" precedent).
class _NotificationsEntryPointCard extends ConsumerWidget {
  const _NotificationsEntryPointCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final unreadCount = ref.watch(unreadNotificationCountProvider);

    return InkWell(
      key: const ValueKey('home-notifications-entry-point'),
      borderRadius: BorderRadius.circular(AppRadius.small),
      onTap: () => context.push(AppRoutes.notificationsInbox),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(AppRadius.small),
        ),
        child: Row(
          children: [
            Icon(
              Icons.notifications_none_outlined,
              color: colorScheme.onSecondaryContainer,
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                l10n.homeNotificationsEntryLabel,
                style: TextStyle(color: colorScheme.onSecondaryContainer),
              ),
            ),
            unreadCount.when(
              data: (count) => count > 0
                  ? _UnreadCountBadge(count: count)
                  : const SizedBox.shrink(),
              loading: () => const SizedBox.shrink(),
              error: (_, _) => const SizedBox.shrink(),
            ),
            const SizedBox(width: AppSpacing.sm),
            Icon(Icons.chevron_right, color: colorScheme.onSecondaryContainer),
          ],
        ),
      ),
    );
  }
}

/// A small, pill-shaped unread-count badge -- `DESIGN.md`'s `rounded.full`
/// token via [AppRadius.full] (mirroring `VerifiedBadge`'s identical
/// fully-rounded shape).
class _UnreadCountBadge extends StatelessWidget {
  const _UnreadCountBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      key: const ValueKey('home-notifications-unread-badge'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: colorScheme.error,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        '$count',
        style: Theme.of(
          context,
        ).textTheme.labelSmall?.copyWith(color: colorScheme.onError),
      ),
    );
  }
}
