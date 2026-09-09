import 'package:ai_marketplace_app/features/search/data/search_repository.dart';
import 'package:ai_marketplace_app/features/search/domain/models/search_exception.dart';
import 'package:ai_marketplace_app/features/search/domain/models/search_filters_args.dart';
import 'package:ai_marketplace_app/features/search/domain/models/search_result_provider.dart';
import 'package:ai_marketplace_app/features/search/presentation/screens/search_results_screen.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import 'fakes/fake_search_repository.dart';

/// S-08 -- Search Results (`Plan_S06_DIR-001.md`, AC3/AC4/AC5, Decision 2/7).
void main() {
  const SearchFiltersArgs filters = (
    category: null,
    latitude: 25.2048,
    longitude: 55.2708,
    radiusKm: 10.0,
  );

  const providerWithNoReviews = SearchResultProvider(
    id: 'provider-1',
    displayName: 'Speedy Plumbing',
    slug: 'speedy-plumbing',
    providerType: ProviderType.business,
    categoryLabels: ['Plumbing'],
    reviewCount: 0,
    distanceMeters: 850,
  );

  // Decision 2's "has reviews" path can only be exercised via fixture-
  // injected data today (no real code path produces a non-null
  // average_rating yet, since no Review domain exists) -- this is the
  // deliberate, documented fixture case, not a gap.
  const providerWithReviews = SearchResultProvider(
    id: 'provider-2',
    displayName: 'Al Wasl Cleaning Co.',
    slug: 'al-wasl-cleaning-co',
    providerType: ProviderType.business,
    categoryLabels: ['Cleaning'],
    averageRating: 4.8,
    reviewCount: 3,
    distanceMeters: 2400,
  );

  testWidgets('reached with no filters (Decision 7) shows the pre-search empty '
      'state, distinct from the zero-results copy, and never calls the '
      'repository', (tester) async {
    final fakeRepository = FakeSearchRepository();

    await pumpScreen(
      tester,
      child: const SearchResultsScreen(filters: null),
      overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Choose a category or search nearby to see providers.'),
      findsOneWidget,
    );
    expect(
      find.text('No results for this search — try widening your search area.'),
      findsNothing,
    );
    expect(fakeRepository.searchProvidersCallCount, 0);
  });

  testWidgets(
    'a search returning zero results shows the post-search "no results" '
    'copy, distinct from the pre-search copy (Decision 7, AC4)',
    (tester) async {
      final fakeRepository = FakeSearchRepository(results: const []);

      await pumpScreen(
        tester,
        child: const SearchResultsScreen(filters: filters),
        overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(fakeRepository.searchProvidersCallCount, 1);
      expect(
        find.text(
          'No results for this search — try widening your search area.',
        ),
        findsOneWidget,
      );
      expect(
        find.text('Choose a category or search nearby to see providers.'),
        findsNothing,
      );
    },
  );

  testWidgets(
    'renders "No reviews yet" for a provider with a null average_rating, '
    'never a synthesized "0.0 (0 reviews)" (Decision 2)',
    (tester) async {
      final fakeRepository = FakeSearchRepository(
        results: const [providerWithNoReviews],
      );

      await pumpScreen(
        tester,
        child: const SearchResultsScreen(filters: filters),
        overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('Speedy Plumbing'), findsOneWidget);
      expect(find.text('No reviews yet'), findsOneWidget);
      expect(find.textContaining('0.0'), findsNothing);
    },
  );

  testWidgets(
    'renders "4.8 (3 reviews)" for a provider with a fixture-injected '
    'rating (Decision 2 -- the only way this path is exercisable today)',
    (tester) async {
      final fakeRepository = FakeSearchRepository(
        results: const [providerWithReviews],
      );

      await pumpScreen(
        tester,
        child: const SearchResultsScreen(filters: filters),
        overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('Al Wasl Cleaning Co.'), findsOneWidget);
      expect(find.text('4.8 (3 reviews)'), findsOneWidget);
    },
  );

  testWidgets(
    'renders distance formatted as meters under 1 km and kilometers at or '
    'above 1 km (AC3)',
    (tester) async {
      final fakeRepository = FakeSearchRepository(
        results: const [providerWithNoReviews, providerWithReviews],
      );

      await pumpScreen(
        tester,
        child: const SearchResultsScreen(filters: filters),
        overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
      );
      await tester.pumpAndSettle();

      expect(find.text('850 m away'), findsOneWidget);
      expect(find.text('2.4 km away'), findsOneWidget);
    },
  );

  testWidgets('a load failure shows a plain-language error, with retry', (
    tester,
  ) async {
    final fakeRepository = FakeSearchRepository(
      searchProvidersError: const SearchException(
        type: SearchErrorType.unknown,
      ),
    );

    await pumpScreen(
      tester,
      child: const SearchResultsScreen(filters: filters),
      overrides: [searchRepositoryProvider.overrideWithValue(fakeRepository)],
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Something went wrong. Please try again.'),
      findsOneWidget,
    );
    expect(find.text('Try again'), findsOneWidget);

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(fakeRepository.searchProvidersCallCount, 2);
  });
}
