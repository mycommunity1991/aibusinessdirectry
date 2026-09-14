import 'package:ai_marketplace_app/features/leads/data/lead_repository.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead.dart';
import 'package:ai_marketplace_app/features/leads/domain/models/lead_exception.dart';
import 'package:ai_marketplace_app/features/leads/presentation/screens/leads_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_lead_repository.dart';

/// LEAD-001 -- `LeadsScreen` (`Plan_S10_LEAD-001.md`, AC1-AC5).
void main() {
  Lead buildLead(
    String id, {
    String? categoryName = 'Plumbing',
    required DateTime viewedAt,
    LeadOutcomeStatus outcomeStatus = LeadOutcomeStatus.notYetReported,
  }) {
    return Lead(
      id: id,
      categoryName: categoryName,
      viewedAt: viewedAt,
      outcomeStatus: outcomeStatus,
    );
  }

  testWidgets('shows a loading indicator before the first page resolves', (
    tester,
  ) async {
    final fakeRepository = FakeLeadRepository(pages: const [[]]);
    await pumpScreen(
      tester,
      child: const LeadsScreen(),
      overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
    );

    // Deliberately no `pumpAndSettle` yet -- this asserts the very first
    // rendered frame, before `LeadsController.load()`'s post-frame-callback
    // trigger has resolved (idle and loading share the same UI branch).
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();
  });

  testWidgets(
    'a load failure shows a plain-language error, with a working retry '
    '(AC4 -- the caller-has-no-provider-yet 404 case)',
    (tester) async {
      final fakeRepository = FakeLeadRepository(
        listMyLeadsError: const LeadException(type: LeadErrorType.notFound),
      );
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(
        find.text("We couldn't find your provider listing."),
        findsOneWidget,
      );
      expect(find.text('Try again'), findsOneWidget);

      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      expect(fakeRepository.listMyLeadsCallCount, 2);
    },
  );

  testWidgets(
    'the empty state renders textually distinct copy and is genuinely '
    'pull-to-refresh-able, not merely styled (AC2)',
    (tester) async {
      final fakeRepository = FakeLeadRepository(pages: const [[]]);
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(
        find.text(
          "No leads yet — once a customer views your contact details, "
          "they'll show up here.",
        ),
        findsOneWidget,
      );
      expect(find.byType(RefreshIndicator), findsOneWidget);
      expect(fakeRepository.listMyLeadsCallCount, 1);

      // A real swipe gesture on the scrollable underneath the
      // RefreshIndicator -- not just asserting the widget type exists --
      // per AC2's literal "remains pull-to-refreshable" requirement.
      await tester.fling(
        find.byType(SingleChildScrollView),
        const Offset(0, 300),
        1000,
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(fakeRepository.listMyLeadsCallCount, 2);
    },
  );

  testWidgets(
    'a loaded, non-empty list is also genuinely pull-to-refresh-able (AC2)',
    (tester) async {
      final now = DateTime.now();
      final fakeRepository = FakeLeadRepository(
        pages: [
          [buildLead('lead-1', viewedAt: now)],
        ],
      );
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(fakeRepository.listMyLeadsCallCount, 1);

      await tester.fling(find.byType(ListView), const Offset(0, 300), 1000);
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(fakeRepository.listMyLeadsCallCount, 2);
    },
  );

  testWidgets(
    'a null categoryName renders the honest fallback string, never blank '
    'or literal "null" text (Decision 3)',
    (tester) async {
      final fakeRepository = FakeLeadRepository(
        pages: [
          [buildLead('lead-1', categoryName: null, viewedAt: DateTime.now())],
        ],
      );
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('Viewed your profile directly'), findsOneWidget);
      expect(find.text('null'), findsNothing);
    },
  );

  testWidgets('a resolved categoryName renders the real category name, not the '
      'fallback string', (tester) async {
    final fakeRepository = FakeLeadRepository(
      pages: [
        [
          buildLead(
            'lead-1',
            categoryName: 'Electrical',
            viewedAt: DateTime.now(),
          ),
        ],
      ],
    );
    await pumpScreen(
      tester,
      child: const LeadsScreen(),
      overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    expect(find.text('Electrical'), findsOneWidget);
    expect(find.text('Viewed your profile directly'), findsNothing);
  });

  testWidgets(
    'all three outcome-status chips render with visually and textually '
    'distinct copy (AC1/AC5)',
    (tester) async {
      final now = DateTime.now();
      final fakeRepository = FakeLeadRepository(
        pages: [
          [
            buildLead(
              'lead-hired',
              viewedAt: now,
              outcomeStatus: LeadOutcomeStatus.hired,
            ),
            buildLead(
              'lead-not-hired',
              viewedAt: now,
              outcomeStatus: LeadOutcomeStatus.notHired,
            ),
            buildLead(
              'lead-not-yet-reported',
              viewedAt: now,
              outcomeStatus: LeadOutcomeStatus.notYetReported,
            ),
          ],
        ],
      );
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('Hired'), findsOneWidget);
      expect(find.text('Not hired'), findsOneWidget);
      expect(find.text('Not yet reported'), findsOneWidget);

      expect(
        find.byKey(const ValueKey('lead-outcome-chip-hired')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('lead-outcome-chip-notHired')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('lead-outcome-chip-notYetReported')),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'an unrecognized outcome status falls back to the "Not yet reported" '
    'copy, never a blank/crashing chip (forward-compatibility)',
    (tester) async {
      final fakeRepository = FakeLeadRepository(
        pages: [
          [
            buildLead(
              'lead-1',
              viewedAt: DateTime.now(),
              outcomeStatus: LeadOutcomeStatus.unknown,
            ),
          ],
        ],
      );
      await pumpScreen(
        tester,
        child: const LeadsScreen(),
        overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('Not yet reported'), findsOneWidget);
    },
  );

  testWidgets('relative timestamps render correctly for known offsets (AC1)', (
    tester,
  ) async {
    final now = DateTime.now();
    final fakeRepository = FakeLeadRepository(
      pages: [
        [
          buildLead('lead-just-now', viewedAt: now),
          buildLead(
            'lead-minutes',
            viewedAt: now.subtract(const Duration(minutes: 5)),
          ),
          buildLead(
            'lead-hours',
            viewedAt: now.subtract(const Duration(hours: 3)),
          ),
          buildLead(
            'lead-days',
            viewedAt: now.subtract(const Duration(days: 4)),
          ),
        ],
      ],
    );
    await pumpScreen(
      tester,
      child: const LeadsScreen(),
      overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    expect(find.text('Just now'), findsOneWidget);
    expect(find.text('5 minutes ago'), findsOneWidget);
    expect(find.text('3 hours ago'), findsOneWidget);
    expect(find.text('4 days ago'), findsOneWidget);
  });

  testWidgets('scrolling near the bottom loads the next page and appends it '
      '(pagination)', (tester) async {
    final now = DateTime.now();
    final page1 = [
      for (var i = 0; i < 20; i++) buildLead('lead-page1-$i', viewedAt: now),
    ];
    final page2 = [buildLead('lead-page2-0', viewedAt: now)];
    final fakeRepository = FakeLeadRepository(pages: [page1, page2]);
    await pumpScreen(
      tester,
      child: const LeadsScreen(),
      overrides: [leadRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    expect(fakeRepository.listMyLeadsCallCount, 1);

    await tester.fling(find.byType(ListView), const Offset(0, -5000), 3000);
    await tester.pumpAndSettle();

    expect(fakeRepository.listMyLeadsCallCount, 2);
    expect(fakeRepository.lastArgs, (page: 2, pageSize: 20));
  });
}
