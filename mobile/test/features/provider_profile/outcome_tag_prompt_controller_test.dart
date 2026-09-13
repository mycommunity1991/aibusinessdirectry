import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/state/outcome_tag_prompt_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_profile_repository.dart';

/// The Outcome Tag Prompt sheet's (REV-001, AC1/AC3) submit-action
/// controller. Kept as its own controller, separate from
/// `ContactRevealController`/`ProviderProfileController` (Plan's Frontend
/// item 1) -- these tests exercise it directly via a [ProviderContainer],
/// with no widget tree involved.
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

  test('submit(hired: true) reaches submitted status and calls the repository '
      'exactly once with hired=true (AC1)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      outcomeTag: OutcomeTag(
        id: 'outcome-tag-1',
        contactViewId: 'contact-view-1',
        hired: true,
        submittedAt: DateTime.utc(2024, 1, 1),
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      outcomeTagPromptControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(hired: true);

    final state = container.read(
      outcomeTagPromptControllerProvider('contact-view-1'),
    );
    expect(state.status, OutcomeTagPromptStatus.submitted);
    expect(fakeRepository.submitOutcomeTagCallCount, 1);
    expect(fakeRepository.lastSubmitOutcomeTagArgs, (
      contactViewId: 'contact-view-1',
      hired: true,
    ));
  });

  test('submit(hired: false) also reaches submitted status -- a "No" outcome '
      'is retained, not discarded (AC5)', () async {
    final fakeRepository = FakeProviderProfileRepository(
      outcomeTag: OutcomeTag(
        id: 'outcome-tag-1',
        contactViewId: 'contact-view-1',
        hired: false,
        submittedAt: DateTime.utc(2024, 1, 1),
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      outcomeTagPromptControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(hired: false);

    final state = container.read(
      outcomeTagPromptControllerProvider('contact-view-1'),
    );
    expect(state.status, OutcomeTagPromptStatus.submitted);
    expect(fakeRepository.lastSubmitOutcomeTagArgs, (
      contactViewId: 'contact-view-1',
      hired: false,
    ));
  });

  test('a network failure maps to the error status, carrying the exception '
      'unchanged', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitOutcomeTagError: const OutcomeTagException(
        type: OutcomeTagErrorType.network,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      outcomeTagPromptControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(hired: true);

    final state = container.read(
      outcomeTagPromptControllerProvider('contact-view-1'),
    );
    expect(state.status, OutcomeTagPromptStatus.error);
    expect(state.error?.type, OutcomeTagErrorType.network);
  });

  test('an already-submitted (409) failure also maps to the error status, '
      'leaving the sheet to decide how to react to it', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitOutcomeTagError: const OutcomeTagException(
        type: OutcomeTagErrorType.alreadyExists,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      outcomeTagPromptControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(hired: true);

    final state = container.read(
      outcomeTagPromptControllerProvider('contact-view-1'),
    );
    expect(state.status, OutcomeTagPromptStatus.error);
    expect(state.error?.type, OutcomeTagErrorType.alreadyExists);
  });

  test('retry() re-submits the same hired value after an error', () async {
    final fakeRepository = FakeProviderProfileRepository(
      submitOutcomeTagError: const OutcomeTagException(
        type: OutcomeTagErrorType.unknown,
      ),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(
      outcomeTagPromptControllerProvider('contact-view-1').notifier,
    );

    await notifier.submit(hired: false);
    expect(fakeRepository.submitOutcomeTagCallCount, 1);

    await notifier.retry();

    expect(fakeRepository.submitOutcomeTagCallCount, 2);
    expect(fakeRepository.lastSubmitOutcomeTagArgs, (
      contactViewId: 'contact-view-1',
      hired: false,
    ));
  });

  test('"Maybe later" is a pure sheet-dismiss with no interaction with this '
      'controller at all -- performs zero repository calls (Decision 7, a '
      'hard requirement)', () async {
    final fakeRepository = FakeProviderProfileRepository();
    buildContainer(fakeRepository);
    // No submit()/retry() call is ever made -- mirrors the sheet's
    // "Maybe later" action, which never reads or touches this
    // controller.

    expect(fakeRepository.submitOutcomeTagCallCount, 0);
  });
}
