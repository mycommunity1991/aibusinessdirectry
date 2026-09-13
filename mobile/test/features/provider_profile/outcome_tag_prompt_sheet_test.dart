import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/outcome_tag_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/presentation/widgets/outcome_tag_prompt_sheet.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_profile_repository.dart';

/// The Outcome Tag Prompt bottom sheet (REV-001, AC1/AC3).
void main() {
  Future<void> pumpSheet(
    WidgetTester tester, {
    required List<Override> overrides,
    String contactViewId = 'contact-view-1',
    String providerDisplayName = 'Al Noor Plumbing Services LLC',
    String? providerPhotoUrl,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides,
        child: MaterialApp(
          theme: AppTheme.light(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => OutcomeTagPromptSheet.show(
                  context,
                  contactViewId: contactViewId,
                  providerDisplayName: providerDisplayName,
                  providerPhotoUrl: providerPhotoUrl,
                ),
                child: const Text('open-sheet'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open-sheet'));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'renders the provider name/photo, the "Did you hire them?" title, and '
    'all three actions (AC1/AC3, 15_SCREEN_INVENTORY.md)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository();

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.byKey(const ValueKey('outcome-tag-prompt-provider-photo')),
        findsOneWidget,
      );
      expect(find.text('Al Noor Plumbing Services LLC'), findsOneWidget);
      expect(find.text('Did you hire them?'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('outcome-tag-prompt-yes-button')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('outcome-tag-prompt-no-button')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('outcome-tag-prompt-maybe-later-button')),
        findsOneWidget,
      );
      // Merely opening the sheet must never call the repository -- unlike
      // ContactRevealSheet, nothing is submitted automatically.
      expect(fakeRepository.submitOutcomeTagCallCount, 0);
    },
  );

  testWidgets(
    'renders the provider photo widget when a photo URL is supplied too '
    '(falls back gracefully if the network image never resolves in tests)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository();

      await pumpSheet(
        tester,
        providerPhotoUrl: '/media/providers/provider-1/photo.jpg',
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.byKey(const ValueKey('outcome-tag-prompt-provider-photo')),
        findsOneWidget,
      );
    },
  );

  testWidgets('tapping Yes submits hired=true and closes the sheet (AC1)', (
    tester,
  ) async {
    final fakeRepository = FakeProviderProfileRepository(
      outcomeTag: OutcomeTag(
        id: 'outcome-tag-1',
        contactViewId: 'contact-view-1',
        hired: true,
        submittedAt: DateTime.utc(2024, 1, 1),
      ),
    );

    await pumpSheet(
      tester,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    await tester.tap(
      find.byKey(const ValueKey('outcome-tag-prompt-yes-button')),
    );
    await tester.pump();

    expect(fakeRepository.submitOutcomeTagCallCount, 1);
    expect(fakeRepository.lastSubmitOutcomeTagArgs, (
      contactViewId: 'contact-view-1',
      hired: true,
    ));

    // The sheet shows a brief confirmation, then auto-closes -- advance
    // past that delay before settling the resulting close animation.
    await tester.pump(const Duration(milliseconds: 700));
    await tester.pumpAndSettle();

    expect(find.byType(OutcomeTagPromptSheet), findsNothing);
  });

  testWidgets(
    'tapping No submits hired=false and closes the sheet (AC1/AC5 -- "No" '
    'is a valid, retained outcome)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        outcomeTag: OutcomeTag(
          id: 'outcome-tag-1',
          contactViewId: 'contact-view-1',
          hired: false,
          submittedAt: DateTime.utc(2024, 1, 1),
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('outcome-tag-prompt-no-button')),
      );
      await tester.pump();

      expect(fakeRepository.submitOutcomeTagCallCount, 1);
      expect(fakeRepository.lastSubmitOutcomeTagArgs, (
        contactViewId: 'contact-view-1',
        hired: false,
      ));

      // The sheet shows a brief confirmation, then auto-closes -- advance
      // past that delay before settling the resulting close animation.
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pumpAndSettle();

      expect(find.byType(OutcomeTagPromptSheet), findsNothing);
    },
  );

  testWidgets(
    'tapping "Maybe later" closes the sheet with ZERO repository calls '
    '(Decision 7 -- a hard requirement)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository();

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('outcome-tag-prompt-maybe-later-button')),
      );
      await tester.pumpAndSettle();

      expect(find.byType(OutcomeTagPromptSheet), findsNothing);
      expect(fakeRepository.submitOutcomeTagCallCount, 0);
    },
  );

  testWidgets(
    'a network failure shows a plain-language error with retry, which '
    're-submits the same hired value',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        submitOutcomeTagError: const OutcomeTagException(
          type: OutcomeTagErrorType.network,
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('outcome-tag-prompt-yes-button')),
      );
      await tester.pumpAndSettle();

      expect(
        find.text(
          "We couldn't connect. Check your internet connection and try again.",
        ),
        findsOneWidget,
      );
      expect(fakeRepository.submitOutcomeTagCallCount, 1);

      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      expect(fakeRepository.submitOutcomeTagCallCount, 2);
      expect(fakeRepository.lastSubmitOutcomeTagArgs, (
        contactViewId: 'contact-view-1',
        hired: true,
      ));
    },
  );

  testWidgets(
    'a 404 (not found/not owned, an effectively-unreachable edge case) '
    'closes the sheet quietly, never showing a scary error',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        submitOutcomeTagError: const OutcomeTagException(
          type: OutcomeTagErrorType.notFound,
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('outcome-tag-prompt-yes-button')),
      );
      await tester.pumpAndSettle();

      expect(find.byType(OutcomeTagPromptSheet), findsNothing);
      expect(
        find.text('Something went wrong. Please try again.'),
        findsNothing,
      );
    },
  );

  testWidgets('a 409 (already submitted, an effectively-unreachable edge case) '
      'closes the sheet quietly too', (tester) async {
    final fakeRepository = FakeProviderProfileRepository(
      submitOutcomeTagError: const OutcomeTagException(
        type: OutcomeTagErrorType.alreadyExists,
      ),
    );

    await pumpSheet(
      tester,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    await tester.tap(
      find.byKey(const ValueKey('outcome-tag-prompt-no-button')),
    );
    await tester.pumpAndSettle();

    expect(find.byType(OutcomeTagPromptSheet), findsNothing);
  });
}
