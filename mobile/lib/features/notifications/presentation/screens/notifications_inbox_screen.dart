import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/utils/relative_time.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../provider_profile/presentation/widgets/outcome_tag_prompt_sheet.dart';
import '../../domain/models/notification_exception.dart';
import '../../domain/models/notification_item.dart';
import '../../state/notifications_controller.dart';
import '../utils/notification_error_copy.dart';

/// `ENG-001` -- Notifications Inbox (`Plan_S12_ENG-001.md`, AC5/AC6,
/// Decision 10). Lists the caller's own notifications, grouped into a
/// "New" section (`readAt == null`) and an "Earlier" section
/// (`readAt != null`, AC6's literal grouping requirement), most-recent
/// notification first within the raw, server-returned order. Tapping a row
/// marks it read, then deep-links by `relatedEntityType`:
///
/// - `verification_record` -> [AppRoutes.verificationStatus].
/// - `contact_view` + `type == "new_contact_view"` -> [AppRoutes.leads].
/// - `contact_view` + `type == "outcome_tag_prompt"` -> reopens the
///   existing [OutcomeTagPromptSheet] (REV-001, `ADR-050`) as a modal,
///   reused as-is rather than a new screen (Decision 10's explicit
///   direction) -- the only place in the app `features/notifications/`
///   imports another feature's widget, mirroring how Decision 10 itself
///   calls this out as a deliberate, explicit reuse rather than the
///   general "features must not depend on each other" default.
/// - `manual_match_assignment` -> no navigation at all; rendered read-only,
///   tapping only marks it read (Decision 9's "in-app-row-only, no admin
///   mobile surface" scope).
class NotificationsInboxScreen extends ConsumerStatefulWidget {
  const NotificationsInboxScreen({super.key});

  @override
  ConsumerState<NotificationsInboxScreen> createState() =>
      _NotificationsInboxScreenState();
}

class _NotificationsInboxScreenState
    extends ConsumerState<NotificationsInboxScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    // Mirrors `LeadsScreen`'s own post-frame-callback pattern --
    // `NotificationsController` starts idle and never auto-loads itself, so
    // a test can construct it deterministically.
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(notificationsControllerProvider.notifier).load();
    });
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final threshold = _scrollController.position.maxScrollExtent - 200;
    if (_scrollController.position.pixels >= threshold) {
      ref.read(notificationsControllerProvider.notifier).loadMore();
    }
  }

  Future<void> _onRefresh() =>
      ref.read(notificationsControllerProvider.notifier).refresh();

  Future<void> _onNotificationTap(NotificationItem notification) async {
    await ref
        .read(notificationsControllerProvider.notifier)
        .markRead(notification.id);
    if (!mounted) return;

    switch (notification.relatedEntityType) {
      case 'verification_record':
        context.push(AppRoutes.verificationStatus);
      case 'contact_view' when notification.type == 'new_contact_view':
        context.push(AppRoutes.leads);
      case 'contact_view' when notification.type == 'outcome_tag_prompt':
        final contactViewId = notification.relatedEntityId;
        if (contactViewId == null) return;
        await OutcomeTagPromptSheet.show(
          context,
          contactViewId: contactViewId,
          providerDisplayName: AppLocalizations.of(
            context,
          ).notificationsOutcomeTagPromptGenericProviderLabel,
        );
      case 'manual_match_assignment':
        // Decision 9 -- no mobile surface for this admin-only trigger;
        // tapping only marks it read (already done above).
        break;
      default:
        // A related-entity type this app version doesn't recognize yet --
        // forward-compatibility no-op, mirrors `LeadOutcomeStatus.unknown`'s
        // own defensive-only fallback philosophy.
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(notificationsControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.notificationsInboxTitle)),
      body: SafeArea(
        child: switch (state.status) {
          NotificationsStatus.idle || NotificationsStatus.loading => Center(
            child: LoadingIndicator(label: l10n.loadingLabel),
          ),
          NotificationsStatus.error => _NotificationsErrorState(
            error: state.error!,
            onRetry: () =>
                ref.read(notificationsControllerProvider.notifier).load(),
          ),
          NotificationsStatus.loaded =>
            state.notifications.isEmpty
                ? _NotificationsEmptyState(
                    message: l10n.notificationsEmptyStateMessage,
                    onRefresh: _onRefresh,
                  )
                : _NotificationsList(
                    notifications: state.notifications,
                    isLoadingMore: state.isLoadingMore,
                    scrollController: _scrollController,
                    onRefresh: _onRefresh,
                    onTap: _onNotificationTap,
                  ),
        },
      ),
    );
  }
}

class _NotificationsErrorState extends StatelessWidget {
  const _NotificationsErrorState({required this.error, required this.onRetry});

  final NotificationException error;
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
            AppErrorMessage(message: notificationErrorMessage(context, error)),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
          ],
        ),
      ),
    );
  }
}

/// The "no notifications yet" empty state -- still wrapped in a genuinely
/// working [RefreshIndicator] (mirrors `_LeadsEmptyState`'s exact
/// `RefreshIndicator` + `LayoutBuilder` + `ConstrainedBox(minHeight: ...)`
/// shape), so a caller can always pull-to-refresh even while the list is
/// empty.
class _NotificationsEmptyState extends StatelessWidget {
  const _NotificationsEmptyState({
    required this.message,
    required this.onRefresh,
  });

  final String message;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.notifications_none_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      message,
                      key: const ValueKey('notifications-empty-state'),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// One flattened row in the sectioned list -- either a section header or a
/// notification item. A plain sealed hierarchy (not a widget itself) so
/// [_NotificationsList] can build a single, genuinely-scrollable
/// `ListView` spanning both sections (AC6's New/Earlier grouping) while
/// still supporting one shared scroll controller for pagination.
sealed class _InboxRow {
  const _InboxRow();
}

class _HeaderRow extends _InboxRow {
  const _HeaderRow(this.label);
  final String label;
}

class _ItemRow extends _InboxRow {
  const _ItemRow(this.notification);
  final NotificationItem notification;
}

class _NotificationsList extends StatelessWidget {
  const _NotificationsList({
    required this.notifications,
    required this.isLoadingMore,
    required this.scrollController,
    required this.onRefresh,
    required this.onTap,
  });

  final List<NotificationItem> notifications;
  final bool isLoadingMore;
  final ScrollController scrollController;
  final Future<void> Function() onRefresh;
  final Future<void> Function(NotificationItem) onTap;

  List<_InboxRow> _buildRows(AppLocalizations l10n) {
    final newItems = notifications.where((n) => n.readAt == null).toList();
    final earlierItems = notifications.where((n) => n.readAt != null).toList();
    return [
      if (newItems.isNotEmpty) ...[
        _HeaderRow(l10n.notificationsNewSectionHeader),
        for (final notification in newItems) _ItemRow(notification),
      ],
      if (earlierItems.isNotEmpty) ...[
        _HeaderRow(l10n.notificationsEarlierSectionHeader),
        for (final notification in earlierItems) _ItemRow(notification),
      ],
    ];
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final rows = _buildRows(l10n);

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.builder(
        key: const ValueKey('notifications-list'),
        controller: scrollController,
        // Always scrollable, even when the loaded list is short enough to
        // fit the viewport -- otherwise a short list would have no
        // overscroll to pull against, silently breaking pull-to-refresh
        // for exactly that case (mirrors `LeadsScreen`'s identical
        // reasoning).
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        itemCount: rows.length + (isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= rows.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: LoadingIndicator(size: 24)),
            );
          }
          final row = rows[index];
          return switch (row) {
            _HeaderRow() => Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Text(
                row.label,
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ),
            _ItemRow() => _NotificationCard(
              notification: row.notification,
              onTap: () => onTap(row.notification),
            ),
          };
        },
      ),
    );
  }
}

/// One notification's card -- title, body, and a relative timestamp, with
/// a small unread-indicator dot for `readAt == null` rows.
class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification, required this.onTap});

  final NotificationItem notification;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final isUnread = notification.readAt == null;

    return Card(
      key: ValueKey('notification-row-${notification.id}'),
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.standard),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (isUnread)
                Padding(
                  padding: const EdgeInsets.only(
                    top: AppSpacing.xs,
                    right: AppSpacing.sm,
                  ),
                  child: Container(
                    key: const ValueKey('notification-unread-dot'),
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: colorScheme.primary,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(notification.title, style: textTheme.titleMedium),
                    const SizedBox(height: AppSpacing.xs),
                    Text(notification.body, style: textTheme.bodyMedium),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      formatRelativeTime(context, notification.createdAt),
                      style: textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
