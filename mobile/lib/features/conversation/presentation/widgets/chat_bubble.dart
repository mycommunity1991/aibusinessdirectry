import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../domain/models/conversation_message.dart';

/// Renders one transcript entry as `chat-bubble-ai`/`chat-bubble-user`
/// (`docs/AI/DESIGN.md`) -- AI in a neutral tone, customer in the
/// primary-tinted tone, aligned to the *reading-order* start/end via
/// [AlignmentDirectional] rather than a literal `Alignment.centerLeft`/
/// `centerRight`. The latter would not mirror under RTL -- exactly the
/// chat-bubble RTL bug `docs/AI/15_SCREEN_INVENTORY.md` flags as this
/// screen's highest RTL risk (AC11).
class ChatBubble extends StatelessWidget {
  const ChatBubble({super.key, required this.message, this.onTap});

  final ConversationMessage message;

  /// Tap-to-revise (AC8) -- only non-null for a past customer message on a
  /// still-active session; `null` renders a plain, non-interactive bubble.
  final VoidCallback? onTap;

  bool get _isCustomer => message.sender == ConversationMessageSender.customer;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    final backgroundColor = _isCustomer
        ? colorScheme.primaryContainer
        : colorScheme.surfaceContainerHighest;
    final textColor = _isCustomer
        ? colorScheme.onPrimaryContainer
        : colorScheme.onSurface;

    final bubble = Container(
      constraints: const BoxConstraints(maxWidth: 280),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(AppRadius.largeCard),
      ),
      child: Text(
        message.content,
        style: textTheme.bodyMedium?.copyWith(color: textColor),
      ),
    );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Align(
        alignment: _isCustomer
            ? AlignmentDirectional.centerEnd
            : AlignmentDirectional.centerStart,
        child: onTap == null
            ? bubble
            : Semantics(
                hint: l10n.aiConversationTapToEditTooltip,
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.largeCard),
                  onTap: onTap,
                  child: bubble,
                ),
              ),
      ),
    );
  }
}
