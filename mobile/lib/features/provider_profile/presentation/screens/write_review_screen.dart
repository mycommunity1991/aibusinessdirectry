import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_config.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../domain/models/review_exception.dart';
import '../../domain/models/write_review_args.dart';
import '../../state/write_review_controller.dart';
import '../utils/review_error_copy.dart';

const _maxCommentLength = 2000;

/// S-10 -- Write a Review (REV-002, AC6). Only ever reached by
/// `context.push(AppRoutes.writeReview, extra: WriteReviewArgs(...))` from
/// `ProviderProfileScreen._onContactTap`, after a real `hired=true` Outcome
/// Tag Prompt submission (Decision 7, `Plan_S09_REV-002.md`) -- no other
/// call site, deep link, or menu item anywhere in the app navigates here.
///
/// Provider name/photo, a [_StarRatingInput] (1-5, no default selection so
/// Submit stays disabled until a rating is chosen, AC3), an optional
/// multi-line comment field (2000-char max, matching the backend's own
/// cap), and a Submit button. A successful submission shows a brief
/// "Thanks!" confirmation, then pops back to `ProviderProfileScreen`
/// (mirrors [OutcomeTagPromptSheet]'s own confirmation pattern, reused
/// here as this screen's own final state, not the sheet's).
class WriteReviewScreen extends ConsumerStatefulWidget {
  const WriteReviewScreen({super.key, required this.args});

  final WriteReviewArgs args;

  @override
  ConsumerState<WriteReviewScreen> createState() => _WriteReviewScreenState();
}

class _WriteReviewScreenState extends ConsumerState<WriteReviewScreen> {
  /// How long the brief "Thanks!" confirmation is shown before this screen
  /// auto-pops on a successful submission -- mirrors
  /// `OutcomeTagPromptSheet`'s identical `_autoCloseDelay` constant.
  static const _autoPopDelay = Duration(milliseconds: 700);

  final _commentController = TextEditingController();

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = writeReviewControllerProvider(widget.args.contactViewId);

    ref.listen(provider, (previous, next) {
      if (next.status == WriteReviewStatus.submitted) {
        // Captured synchronously, before the async gap below -- avoids
        // using [context] itself once the delay has elapsed.
        final navigator = Navigator.of(context);
        Future.delayed(_autoPopDelay, () {
          if (mounted) navigator.pop();
        });
      }
    });

    final state = ref.watch(provider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.writeReviewTitle)),
      body: SafeArea(
        child: state.status == WriteReviewStatus.submitted
            ? _ConfirmationContent(l10n: l10n)
            : _FormContent(
                l10n: l10n,
                providerDisplayName: widget.args.providerDisplayName,
                providerPhotoUrl: widget.args.providerPhotoUrl,
                rating: state.rating,
                commentController: _commentController,
                isSubmitting: state.status == WriteReviewStatus.submitting,
                error: state.status == WriteReviewStatus.error
                    ? state.error
                    : null,
                onRatingSelected: (rating) =>
                    ref.read(provider.notifier).selectRating(rating),
                onSubmit: () => ref
                    .read(provider.notifier)
                    .submit(
                      comment: _commentController.text.trim().isEmpty
                          ? null
                          : _commentController.text.trim(),
                    ),
              ),
      ),
    );
  }
}

class _FormContent extends StatelessWidget {
  const _FormContent({
    required this.l10n,
    required this.providerDisplayName,
    required this.providerPhotoUrl,
    required this.rating,
    required this.commentController,
    required this.isSubmitting,
    required this.error,
    required this.onRatingSelected,
    required this.onSubmit,
  });

  final AppLocalizations l10n;
  final String providerDisplayName;
  final String? providerPhotoUrl;
  final int? rating;
  final TextEditingController commentController;
  final bool isSubmitting;
  final ReviewException? error;
  final ValueChanged<int> onRatingSelected;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              _ProviderPhoto(photoUrl: providerPhotoUrl),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  providerDisplayName,
                  key: const ValueKey('write-review-provider-name'),
                  style: textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            l10n.writeReviewRatingLabel,
            style: textTheme.titleMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.sm),
          _StarRatingInput(rating: rating, onRatingSelected: onRatingSelected),
          const SizedBox(height: AppSpacing.lg),
          AppTextField(
            label: l10n.writeReviewCommentLabel,
            controller: commentController,
            maxLines: 5,
            minLines: 3,
            maxLength: _maxCommentLength,
          ),
          if (error != null) ...[
            const SizedBox(height: AppSpacing.md),
            AppErrorMessage(message: reviewErrorMessage(context, error!)),
          ],
          const SizedBox(height: AppSpacing.xl),
          PrimaryButton(
            key: const ValueKey('write-review-submit-button'),
            label: l10n.writeReviewSubmitLabel,
            isLoading: isSubmitting,
            onPressed: (rating == null || isSubmitting) ? null : onSubmit,
          ),
        ],
      ),
    );
  }
}

/// A five-star tappable rating input, 1-5 (AC3) -- no new package, per the
/// Plan's own note that a star rating is expressible with five plain
/// `Icon(Icons.star / Icons.star_border)` widgets.
class _StarRatingInput extends StatelessWidget {
  const _StarRatingInput({
    required this.rating,
    required this.onRatingSelected,
  });

  final int? rating;
  final ValueChanged<int> onRatingSelected;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var star = 1; star <= 5; star++)
          IconButton(
            key: ValueKey('write-review-star-$star'),
            iconSize: 36,
            onPressed: () => onRatingSelected(star),
            icon: Icon(
              rating != null && star <= rating!
                  ? Icons.star
                  : Icons.star_border,
              color: rating != null && star <= rating!
                  ? colorScheme.primary
                  : colorScheme.onSurfaceVariant,
            ),
          ),
      ],
    );
  }
}

class _ProviderPhoto extends StatelessWidget {
  const _ProviderPhoto({required this.photoUrl});

  final String? photoUrl;

  static const double _size = 48;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final photoUrl = this.photoUrl;
    final placeholder = CircleAvatar(
      radius: _size / 2,
      backgroundColor: colorScheme.surfaceContainerHighest,
      child: Icon(
        Icons.storefront_outlined,
        color: colorScheme.onSurfaceVariant,
      ),
    );

    return SizedBox(
      key: const ValueKey('write-review-provider-photo'),
      height: _size,
      width: _size,
      child: photoUrl == null
          ? placeholder
          : ClipOval(
              child: Image.network(
                '${ApiConfig.mediaOrigin}$photoUrl',
                height: _size,
                width: _size,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => placeholder,
              ),
            ),
    );
  }
}

class _ConfirmationContent extends StatelessWidget {
  const _ConfirmationContent({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        l10n.writeReviewThanksMessage,
        key: const ValueKey('write-review-confirmation'),
        style: Theme.of(context).textTheme.titleMedium,
        textAlign: TextAlign.center,
      ),
    );
  }
}
