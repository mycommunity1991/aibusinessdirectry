import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/state/write_review_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_profile_repository.dart';

/// The Write-a-Review screen's (S-10, REV-002, AC1/AC3) submit-action
/// controller. Kept as its own controller, separate from
/// `OutcomeTagPromptController`/`ContactRevealController`/
/// `ProviderProfileController` (Plan's Frontend item 1) -- these tests
/// exercise it directly via a [ProviderContainer], with no widget tree
/// involved.
void main() {
  ProviderContainer buildContainer(FakeProviderProfileRepository repository) {
    final container = ProviderContainer(
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  test('selectRating updates the visible state without submitting', () {
    final fakeRepository = FakeProviderProfileRepository();
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(4);

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.rating, 4);
    expect(state.status, WriteReviewStatus.idle);
    expect(fakeRepository.submitReviewCallCount, 0);
  });

  test('submit() with no rating selected performs zero repository calls '
      '(Submit stays disabled until a rating is chosen, AC3)', () async {
    final fakeRepository = FakeProviderProfileRepository();
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(comment: 'Great work');

    expect(fakeRepository.submitReviewCallCount, 0);
    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.idle);
  });

  test('submit() with a rating and a comment reaches submitted status and '
      'calls the repository exactly once with both values (AC1)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      review: Review(
        id: 'review-1',
        contactViewId: 'contact-view-1',
        providerId: 'provider-1',
        rating: 5,
        comment: 'Great work',
        createdAt: DateTime.utc(2024, 1, 1),
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(5);
    await notifier.submit(comment: 'Great work');

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.submitted);
    expect(fakeRepository.submitReviewCallCount, 1);
    expect(fakeRepository.lastSubmitReviewArgs, (
      contactViewId: 'contact-view-1',
      rating: 5,
      comment: 'Great work',
    ));
  });

  test('submit() with a rating and no comment reaches submitted status, '
      'sending comment: null (AC3, comment is optional)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      review: Review(
        id: 'review-1',
        contactViewId: 'contact-view-1',
        providerId: 'provider-1',
        rating: 3,
        comment: null,
        createdAt: DateTime.utc(2024, 1, 1),
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(3);
    await notifier.submit();

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.submitted);
    expect(fakeRepository.lastSubmitReviewArgs, (
      contactViewId: 'contact-view-1',
      rating: 3,
      comment: null,
    ));
  });

  test('a network failure maps to the error status, carrying the exception '
      'unchanged', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitReviewError: const ReviewException(type: ReviewErrorType.network),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(2);
    await notifier.submit();

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.error);
    expect(state.error?.type, ReviewErrorType.network);
  });

  test('an anchor-not-verified (409) failure maps to the error status '
      '(REV-002, AC2/Decision 5)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitReviewError: const ReviewException(
        type: ReviewErrorType.anchorNotVerified,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(1);
    await notifier.submit();

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.error);
    expect(state.error?.type, ReviewErrorType.anchorNotVerified);
  });

  test('an already-exists (409) failure maps to the error status (REV-002, '
      'AC1)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitReviewError: const ReviewException(
        type: ReviewErrorType.alreadyExists,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(4);
    await notifier.submit();

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.error);
    expect(state.error?.type, ReviewErrorType.alreadyExists);
  });

  test('a not-found (404) failure maps to the error status (REV-002, '
      'Decision 5)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitReviewError: const ReviewException(type: ReviewErrorType.notFound),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      writeReviewControllerProvider('contact-view-1').notifier,
    );

    notifier.selectRating(4);
    await notifier.submit();

    final state = container.read(
      writeReviewControllerProvider('contact-view-1'),
    );
    expect(state.status, WriteReviewStatus.error);
    expect(state.error?.type, ReviewErrorType.notFound);
  });
}
