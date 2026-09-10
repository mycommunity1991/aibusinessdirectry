import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';

/// The AI Conversation screen's (S-07) 0-500ms/500ms-3s typing-indicator
/// tier (AC6) -- three animated dots, no text, rendered inside an
/// AI-toned `chat-bubble-ai` shell so it visually reads as "the AI is
/// composing a reply," not a generic spinner.
class TypingIndicatorBubble extends StatefulWidget {
  const TypingIndicatorBubble({super.key});

  @override
  State<TypingIndicatorBubble> createState() => _TypingIndicatorBubbleState();
}

class _TypingIndicatorBubbleState extends State<TypingIndicatorBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Align(
        alignment: AlignmentDirectional.centerStart,
        child: Semantics(
          label: l10n.aiConversationTypingIndicatorLabel,
          child: Container(
            key: const ValueKey('ai-conversation-typing-indicator'),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.md,
            ),
            decoration: BoxDecoration(
              color: colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(AppRadius.largeCard),
            ),
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, _) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(3, (index) {
                    final t = (_controller.value + (index / 3)) % 1.0;
                    final proximityToPeak = 1 - ((t - 0.5).abs() * 2);
                    final opacity = (0.3 + 0.7 * proximityToPeak).clamp(
                      0.3,
                      1.0,
                    );
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: Opacity(
                        opacity: opacity,
                        child: CircleAvatar(
                          radius: 4,
                          backgroundColor: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    );
                  }),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
