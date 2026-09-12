import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../features/provider_profile/domain/models/provider_profile_args.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/ranked_provider_results_list.dart';
import '../../domain/models/conversation_message.dart';
import '../../domain/models/conversation_session.dart';
import '../../domain/models/search_request_result.dart';
import '../../state/conversation_controller.dart';
import '../utils/conversation_error_copy.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/typing_indicator_bubble.dart';

/// S-07 -- AI Conversation (AI-001, AC1/AC4/AC6/AC7/AC8/AC11).
///
/// Before a session exists, shows a compose step for the customer's
/// free-text opening message (AC1). Once a session exists, shows the full
/// chat transcript: quick-reply chips when the current turn expects a
/// selection, a free-text input otherwise (never both at once); tapping a
/// past customer bubble opens an inline revise editor (AC8); the >3s/>8s
/// latency tiers (AC6/AC7) render below the transcript while a turn is in
/// flight; and an honest, plain completion state (no fake results list,
/// Decision 1) once the session reaches `completed`/`routed_to_admin`.
/// "Start over" is always visible in the app bar (Decision 5).
///
/// Never renders a confidence/score value anywhere -- the backend response
/// this screen is built from has no such field at all (AC6).
class AiConversationScreen extends ConsumerStatefulWidget {
  const AiConversationScreen({super.key});

  @override
  ConsumerState<AiConversationScreen> createState() =>
      _AiConversationScreenState();
}

class _AiConversationScreenState extends ConsumerState<AiConversationScreen>
    with WidgetsBindingObserver {
  final _composeController = TextEditingController();
  final _answerController = TextEditingController();
  final _reviseController = TextEditingController();
  final _transcriptScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _composeController.dispose();
    _answerController.dispose();
    _reviseController.dispose();
    _transcriptScrollController.dispose();
    super.dispose();
  }

  /// Pauses/resumes the `pending_manual_match` poll loop with the app's
  /// foreground/background lifecycle (AI-002, Mobile item 27) -- no
  /// push-notification delivery channel exists yet, so polling only ever
  /// runs while the app is actually in the foreground.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = ref.read(conversationControllerProvider.notifier);
    if (state == AppLifecycleState.resumed) {
      controller.resumePolling();
    } else {
      controller.pausePolling();
    }
  }

  void _scrollToBottomSoon() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_transcriptScrollController.hasClients) return;
      _transcriptScrollController.jumpTo(
        _transcriptScrollController.position.maxScrollExtent,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(conversationControllerProvider);
    final controller = ref.read(conversationControllerProvider.notifier);

    ref.listen(conversationControllerProvider, (previous, next) {
      final nextSession = next.session;
      if (nextSession == null) return;
      final grew =
          (previous?.session?.messages.length ?? 0) <
          nextSession.messages.length;
      if (grew) {
        _scrollToBottomSoon();
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.aiConversationTitle),
        actions: [
          TextButton(
            key: const ValueKey('ai-conversation-start-over'),
            onPressed: controller.startOver,
            child: Text(l10n.aiConversationStartOverLabel),
          ),
        ],
      ),
      body: SafeArea(
        child: state.isComposing
            ? _ComposeView(
                state: state,
                controller: controller,
                textController: _composeController,
              )
            : _ActiveView(
                state: state,
                controller: controller,
                answerController: _answerController,
                reviseController: _reviseController,
                scrollController: _transcriptScrollController,
              ),
      ),
    );
  }
}

class _ComposeView extends StatelessWidget {
  const _ComposeView({
    required this.state,
    required this.controller,
    required this.textController,
  });

  final ConversationState state;
  final ConversationController controller;
  final TextEditingController textController;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.aiConversationComposeHeading,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            l10n.aiConversationComposeSubtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.lg),
          AppTextField(
            key: const ValueKey('ai-conversation-compose-field'),
            label: l10n.aiConversationComposeFieldLabel,
            hintText: l10n.aiConversationComposeHint,
            controller: textController,
            maxLines: 4,
            minLines: 3,
            enabled: !state.isBusy,
          ),
          const SizedBox(height: AppSpacing.md),
          if (state.error != null) ...[
            AppErrorMessage(
              message: conversationErrorMessage(context, state.error!),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          ValueListenableBuilder<TextEditingValue>(
            valueListenable: textController,
            builder: (context, value, _) {
              return PrimaryButton(
                key: const ValueKey('ai-conversation-start-button'),
                label: l10n.aiConversationStartButtonLabel,
                // AC7 -- never an indefinite spinner past the >8s
                // hand-off tier; the button itself stops animating once
                // `_LatencyStatus` below has already taken over
                // communicating progress via the hand-off message.
                isLoading:
                    state.turnPhase == ConversationTurnPhase.indicator ||
                    state.turnPhase == ConversationTurnPhase.contextual,
                onPressed: (value.text.trim().isEmpty || state.isBusy)
                    ? null
                    : () => controller.start(textController.text),
              );
            },
          ),
          if (state.isBusy) ...[
            const SizedBox(height: AppSpacing.md),
            _LatencyStatus(phase: state.turnPhase),
          ],
        ],
      ),
    );
  }
}

class _ActiveView extends StatelessWidget {
  const _ActiveView({
    required this.state,
    required this.controller,
    required this.answerController,
    required this.reviseController,
    required this.scrollController,
  });

  final ConversationState state;
  final ConversationController controller;
  final TextEditingController answerController;
  final TextEditingController reviseController;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context) {
    final session = state.session!;
    final searchResults = state.searchResults;

    // AI-002, Decision 6: once the session's search request resolves
    // (`matched`/`unmatched`), the shared ranked-results widget takes over
    // the screen's whole body -- the customer's experience from here is
    // identical to `SearchResultsScreen` (S-08), regardless of whether the
    // result came from the automated matcher or an admin (AC4). While
    // still `pending_manual_match` (or before the first poll response
    // arrives), the transcript + honest waiting banner below stay exactly
    // as `AI-001` already shipped them.
    if (session.isTerminal &&
        searchResults != null &&
        searchResults.isResolved) {
      return _ResolvedResultsView(
        searchResults: searchResults,
        searchRequestId: session.searchRequestId,
      );
    }

    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            key: const ValueKey('ai-conversation-transcript'),
            controller: scrollController,
            padding: const EdgeInsets.all(AppSpacing.md),
            itemCount: session.messages.length + (state.isBusy ? 1 : 0),
            itemBuilder: (context, index) {
              if (index >= session.messages.length) {
                return _LatencyStatus(phase: state.turnPhase);
              }
              final message = session.messages[index];
              final canRevise =
                  session.isActive &&
                  message.sender == ConversationMessageSender.customer;
              return ChatBubble(
                message: message,
                onTap: canRevise
                    ? () {
                        // Seeded imperatively, outside of build -- never
                        // mutate a TextEditingController's text as a
                        // side effect of building a widget.
                        reviseController.text = message.content;
                        controller.beginRevise(message.id);
                      }
                    : null,
              );
            },
          ),
        ),
        if (state.error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: AppErrorMessage(
              message: conversationErrorMessage(context, state.error!),
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: _buildInputArea(context, session),
        ),
      ],
    );
  }

  Widget _buildInputArea(BuildContext context, ConversationSession session) {
    if (state.revisingMessageId != null) {
      return _ReviseEditor(
        controller: controller,
        textController: reviseController,
      );
    }

    if (session.isTerminal) {
      return const _CompletionBanner();
    }

    if (session.hasQuickReplyOptions) {
      return _QuickReplyRow(
        options: session.quickReplyOptions!,
        onSelected: controller.submitQuickReply,
      );
    }

    return _FreeTextRow(
      controller: controller,
      textController: answerController,
    );
  }
}

class _FreeTextRow extends StatelessWidget {
  const _FreeTextRow({required this.controller, required this.textController});

  final ConversationController controller;
  final TextEditingController textController;

  void _submit() {
    final text = textController.text;
    if (text.trim().isEmpty) return;
    controller.submitFreeText(text);
    textController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: AppTextField(
            key: const ValueKey('ai-conversation-answer-field'),
            label: l10n.aiConversationFreeTextFieldLabel,
            controller: textController,
            textInputAction: TextInputAction.send,
            onChanged: (_) {},
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        // Never disabled while a turn is in flight -- submitting queues
        // the input instead of blocking it (`16_UX_GUIDELINES.md`).
        IconButton(
          key: const ValueKey('ai-conversation-send-button'),
          tooltip: l10n.aiConversationSendTooltip,
          icon: const Icon(Icons.send),
          onPressed: _submit,
        ),
      ],
    );
  }
}

class _QuickReplyRow extends StatelessWidget {
  const _QuickReplyRow({required this.options, required this.onSelected});

  final List<String> options;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: options
          .map(
            (option) => ActionChip(
              key: ValueKey('ai-conversation-quick-reply-$option'),
              label: Text(option),
              onPressed: () => onSelected(option),
            ),
          )
          .toList(),
    );
  }
}

class _ReviseEditor extends StatelessWidget {
  const _ReviseEditor({required this.controller, required this.textController});

  final ConversationController controller;
  final TextEditingController textController;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          l10n.aiConversationReviseSheetTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.sm),
        AppTextField(
          key: const ValueKey('ai-conversation-revise-field'),
          label: l10n.aiConversationReviseFieldLabel,
          controller: textController,
          maxLines: 3,
          minLines: 1,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: TextButton(
                key: const ValueKey('ai-conversation-revise-cancel'),
                onPressed: () {
                  textController.clear();
                  controller.cancelRevise();
                },
                child: Text(l10n.aiConversationReviseCancelLabel),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            // `PrimaryButton`'s underlying `FilledButton` theme sets a
            // full-width minimum size (`Size.fromHeight`, unbounded width)
            // -- it must be wrapped in `Expanded` whenever placed inside a
            // `Row` (unlike its usual full-width `Column` placement
            // elsewhere), or it forces an infinite-width layout constraint.
            Expanded(
              child: PrimaryButton(
                key: const ValueKey('ai-conversation-revise-save'),
                label: l10n.saveLabel,
                onPressed: () {
                  final text = textController.text;
                  textController.clear();
                  controller.submitRevision(text);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// AC6/AC7's exact staged-feedback tiers, rendered as the last element of
/// the transcript (active session) or below the compose button (before any
/// session exists) -- never a raw confidence value, never an indefinite
/// spinner past 8 seconds.
class _LatencyStatus extends StatelessWidget {
  const _LatencyStatus({required this.phase});

  final ConversationTurnPhase phase;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return switch (phase) {
      ConversationTurnPhase.idle => const SizedBox.shrink(),
      ConversationTurnPhase.indicator => const TypingIndicatorBubble(),
      ConversationTurnPhase.contextual => Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        child: Text(
          l10n.aiConversationContextualLabel,
          key: const ValueKey('ai-conversation-contextual-label'),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
      ConversationTurnPhase.handoff => Container(
        key: const ValueKey('ai-conversation-handoff-banner'),
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.md),
        margin: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(AppRadius.standard),
        ),
        child: Text(
          l10n.aiConversationHandoffMessage,
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSecondaryContainer,
          ),
        ),
      ),
    };
  }
}

/// Decision 1's honest, plain completion confirmation -- no fake results
/// list, since no matching has run yet at the code level for either a
/// `completed` or a `routed_to_admin` session (`AI-002`'s job).
class _CompletionBanner extends StatelessWidget {
  const _CompletionBanner();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.check_circle_outline, size: 48, color: colorScheme.primary),
        const SizedBox(height: AppSpacing.sm),
        Text(
          l10n.aiConversationCompletionTitle,
          key: const ValueKey('ai-conversation-completion-title'),
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          l10n.aiConversationCompletionMessage,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }
}

/// AI-002, Decision 6 -- once the session's search request resolves
/// (`matched`/`unmatched`), takes over the whole screen body, rendering the
/// same shared `RankedProviderResultsList` widget `SearchResultsScreen`
/// (S-08) uses, so the customer's experience is identical whether the
/// result came from the automated matcher or an admin (AC4). Never renders
/// anything that distinguishes the two origins.
class _ResolvedResultsView extends StatelessWidget {
  const _ResolvedResultsView({
    required this.searchResults,
    required this.searchRequestId,
  });

  final SearchRequestResult searchResults;

  /// The session's real, already-known `search_request_id` (AI-002) --
  /// threaded down from `ConversationSession.searchRequestId`, non-`null`
  /// by construction whenever this view is reachable at all (only rendered
  /// once `session.isTerminal` with a resolved `searchResults`, and a
  /// session only ever reaches a terminal state alongside a non-`null`
  /// `search_request_id`, per `ConversationController._syncResultsPolling`).
  /// Passed through to the Provider Profile screen (CON-001, Decision 4)
  /// so a Contact View created from here records its true originating
  /// search request.
  final String? searchRequestId;

  void _onResultTap(BuildContext context, String providerId) {
    final ProviderProfileArgs args = (
      providerId: providerId,
      searchRequestId: searchRequestId,
    );
    context.push(AppRoutes.providerProfile, extra: args);
  }

  void _onClaimTap(BuildContext context, String providerId) {
    context.push(AppRoutes.claimOtp, extra: providerId);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final matches = searchResults.matchedProviders;

    if (matches.isEmpty) {
      return _NoMatchesState(message: l10n.aiConversationNoMatchesMessage);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            l10n.aiConversationResultsHeading,
            key: const ValueKey('ai-conversation-results-heading'),
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ),
        Expanded(
          child: RankedProviderResultsList(
            results: matches,
            onTap: (providerId) => _onResultTap(context, providerId),
            onClaimTap: (providerId) => _onClaimTap(context, providerId),
          ),
        ),
      ],
    );
  }
}

/// AI-002, Decision 6 -- the `unmatched` empty state (a resolved search
/// request with zero matched providers), textually distinct from both the
/// still-pending completion banner and from `SearchResultsScreen`'s own
/// zero-results copy (Decision 7's "textually distinct empty states" rule).
class _NoMatchesState extends StatelessWidget {
  const _NoMatchesState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              message,
              key: const ValueKey('ai-conversation-no-matches-message'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }
}
