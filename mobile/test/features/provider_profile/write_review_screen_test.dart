import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/review_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/write_review_args.dart';
import 'package:ai_marketplace_app/features/provider_profile/presentation/screens/write_review_screen.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_profile_repository.dart';

/// S-10 -- Write a Review (REV-002, AC1/AC3/AC6). Pumped as a genuinely
/// pushed route (not the app's only route) so a successful submission's
/// auto-pop (mirrors `OutcomeTagPromptSheet`'s own confirmation pattern)
/// is testable the same way a real navigation stack would behave.
Future<void> pumpWriteReviewScreen(
  WidgetTester tester, {
  required WriteReviewArgs args,
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => WriteReviewScreen(args: args),
                  ),
                ),
                child: const Text('push-write-review'),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('push-write-review'));
  await tester.pumpAndSettle();
}

void main() {
  const WriteReviewArgs args = (
    contactViewId: 'contact-view-1',
    providerId: 'provider-1',
    providerDisplayName: 'Al Noor Plumbing Services LLC',
    providerPhotoUrl: null,
  );

  testWidgets('renders the provider name and photo (REV-002)', (tester) async {
    await pumpWriteReviewScreen(
      tester,
      args: args,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(
          FakeProviderProfileRepository(),
        ),
      ],
    );

    expect(
      find.byKey(const ValueKey('write-review-provider-name')),
      findsOneWidget,
    );
    expect(find.text('Al Noor Plumbing Services LLC'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('write-review-provider-photo')),
      findsOneWidget,
    );
  });

  testWidgets(
    'Submit stays disabled until a star rating is chosen (AC3, no default '
    'selection)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository();
      await pumpWriteReviewScreen(
        tester,
        args: args,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      final submitButton = tester.widget<FilledButton>(
        find.descendant(
          of: find.byKey(const ValueKey('write-review-submit-button')),
          matching: find.byType(FilledButton),
        ),
      );
      expect(submitButton.onPressed, isNull);

      await tester.tap(find.text('Submit review'));
      await tester.pumpAndSettle();
      expect(fakeRepository.submitReviewCallCount, 0);
    },
  );

  testWidgets('tapping a star selects that rating and enables Submit', (
    tester,
  ) async {
    await pumpWriteReviewScreen(
      tester,
      args: args,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(
          FakeProviderProfileRepository(),
        ),
      ],
    );

    await tester.tap(find.byKey(const ValueKey('write-review-star-4')));
    await tester.pump();

    final submitButton = tester.widget<FilledButton>(
      find.descendant(
        of: find.byKey(const ValueKey('write-review-submit-button')),
        matching: find.byType(FilledButton),
      ),
    );
    expect(submitButton.onPressed, isNotNull);

    // Stars 1-4 are filled, star 5 remains outlined.
    Icon iconFor(int star) => tester.widget<Icon>(
      find.descendant(
        of: find.byKey(ValueKey('write-review-star-$star')),
        matching: find.byType(Icon),
      ),
    );
    for (var star = 1; star <= 4; star++) {
      expect(iconFor(star).icon, Icons.star);
    }
    expect(iconFor(5).icon, Icons.star_border);
  });

  testWidgets(
    'a successful submission sends the selected rating and typed comment, '
    'shows a brief confirmation, then pops back (AC1)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        review: Review(
          id: 'review-1',
          contactViewId: 'contact-view-1',
          providerId: 'provider-1',
          rating: 5,
          comment: 'Excellent service',
          createdAt: DateTime.utc(2024, 1, 1),
        ),
      );
      await pumpWriteReviewScreen(
        tester,
        args: args,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      await tester.tap(find.byKey(const ValueKey('write-review-star-5')));
      await tester.pump();
      await tester.enterText(find.byType(TextField), 'Excellent service');
      await tester.pump();
      await tester.tap(find.text('Submit review'));
      await tester.pump();

      expect(fakeRepository.submitReviewCallCount, 1);
      expect(fakeRepository.lastSubmitReviewArgs, (
        contactViewId: 'contact-view-1',
        rating: 5,
        comment: 'Excellent service',
      ));

      await tester.pump();
      expect(
        find.byKey(const ValueKey('write-review-confirmation')),
        findsOneWidget,
      );

      // Auto-pop, mirroring OutcomeTagPromptSheet's own confirmation
      // pattern.
      await tester.pumpAndSettle(const Duration(seconds: 1));
      expect(find.text('push-write-review'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('write-review-confirmation')),
        findsNothing,
      );
    },
  );

  testWidgets('an anchor-not-verified (409) failure shows a plain-language '
      'error, never a raw exception', (tester) async {
    final fakeRepository = FakeProviderProfileRepository(
      submitReviewError: const ReviewException(
        type: ReviewErrorType.anchorNotVerified,
      ),
    );
    await pumpWriteReviewScreen(
      tester,
      args: args,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    await tester.tap(find.byKey(const ValueKey('write-review-star-3')));
    await tester.pump();
    await tester.tap(find.text('Submit review'));
    await tester.pumpAndSettle();

    expect(
      find.text('Something went wrong. Please try again.'),
      findsOneWidget,
    );
    expect(find.textContaining('ReviewException'), findsNothing);
  });
}
