import 'package:ai_marketplace_app/features/leads/data/lead_repository.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead_exception.dart';
import 'package:ai_marketplace_app/features/leads/state/leads_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_lead_repository.dart';

/// LEAD-001 -- `LeadsController` (`Plan_S10_LEAD-001.md`, Frontend item 1,
/// AC1/AC2). Exercised directly via a [ProviderContainer], with no widget
/// tree involved, mirroring `write_review_controller_test.dart`'s pattern.
void main() {
  ProviderContainer buildContainer(FakeLeadRepository repository) {
    final container = ProviderContainer(
      overrides: [leadRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
    return container;
  }

  Lead buildLead(
    String id, {
    LeadOutcomeStatus status = LeadOutcomeStatus.hired,
  }) {
    return Lead(
      id: id,
      categoryName: 'Plumbing',
      viewedAt: DateTime.utc(2026, 1, 1),
      outcomeStatus: status,
    );
  }

  test('load() reaches loaded status with the fetched leads (AC1)', () async {
    final leads = [buildLead('lead-1'), buildLead('lead-2')];
    final fakeRepository = FakeLeadRepository(pages: [leads]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(leadsControllerProvider);
    expect(state.status, LeadsStatus.loaded);
    expect(state.leads, leads);
    expect(state.hasMore, isFalse);
  });

  test('load() with zero leads reaches loaded status with an empty list, '
      'never error (AC2)', () async {
    final fakeRepository = FakeLeadRepository(pages: const [[]]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(leadsControllerProvider);
    expect(state.status, LeadsStatus.loaded);
    expect(state.leads, isEmpty);
  });

  test('a load failure maps to the error status, carrying the exception '
      'unchanged', () async {
    final fakeRepository = FakeLeadRepository(
      listMyLeadsError: const LeadException(type: LeadErrorType.notFound),
    );
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();

    final state = container.read(leadsControllerProvider);
    expect(state.status, LeadsStatus.error);
    expect(state.error?.type, LeadErrorType.notFound);
  });

  test('loadMore() appends the next page to the already-loaded list '
      '(pagination page-append behavior)', () async {
    final page1 = [buildLead('lead-1'), buildLead('lead-2')];
    final page2 = [buildLead('lead-3'), buildLead('lead-4')];
    final fakeRepository = FakeLeadRepository(pages: [page1, page2]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();
    expect(container.read(leadsControllerProvider).hasMore, isTrue);

    await notifier.loadMore();

    final state = container.read(leadsControllerProvider);
    expect(state.leads, [...page1, ...page2]);
    expect(state.page, 2);
    expect(state.hasMore, isFalse);
    expect(fakeRepository.listMyLeadsCallCount, 2);
  });

  test('loadMore() is a no-op once hasMore is false', () async {
    final page1 = [buildLead('lead-1')];
    final fakeRepository = FakeLeadRepository(pages: [page1]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();
    expect(container.read(leadsControllerProvider).hasMore, isFalse);

    await notifier.loadMore();

    expect(fakeRepository.listMyLeadsCallCount, 1);
    expect(container.read(leadsControllerProvider).leads, page1);
  });

  test('refresh() resets to page 1, replacing the accumulated list rather '
      'than appending to it (AC2)', () async {
    final page1 = [buildLead('lead-1'), buildLead('lead-2')];
    final page2 = [buildLead('lead-3'), buildLead('lead-4')];
    final fakeRepository = FakeLeadRepository(pages: [page1, page2]);
    final container = buildContainer(fakeRepository);
    final notifier = container.read(leadsControllerProvider.notifier);

    await notifier.load();
    await notifier.loadMore();
    expect(container.read(leadsControllerProvider).leads.length, 4);

    await notifier.refresh();

    final state = container.read(leadsControllerProvider);
    expect(state.leads, page1);
    expect(state.page, 1);
    expect(fakeRepository.lastArgs, (page: 1, pageSize: 20));
  });
}
