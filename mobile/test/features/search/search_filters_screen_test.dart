import 'package:ai_marketplace_app/core/routing/app_routes.dart';
import 'package:ai_marketplace_app/features/customer/data/saved_address_repository.dart';
import 'package:ai_marketplace_app/features/customer/domain/models/saved_address.dart';
import 'package:ai_marketplace_app/features/search/data/search_repository.dart';
import 'package:ai_marketplace_app/features/search/domain/models/category_option.dart';
import 'package:ai_marketplace_app/features/search/presentation/screens/search_results_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../auth/test_helpers.dart';
import '../customer/fakes/fake_saved_address_repository.dart';
import 'fakes/fake_search_repository.dart';

/// Search Filters screen (`Plan_S06_DIR-001.md`, Decision 6, Mobile item 19).
void main() {
  const defaultAddress = SavedAddress(
    id: 'address-1',
    label: 'Home',
    addressLine: 'Villa 12, Al Wasl Road',
    city: 'Dubai',
    region: 'Dubai',
    countryCode: 'AE',
    latitude: 25.2048,
    longitude: 55.2708,
    isDefault: true,
  );

  testWidgets(
    'category chips populate from the repository\'s listCategories(), '
    'including the "All categories" option',
    (tester) async {
      final fakeSearchRepository = FakeSearchRepository(
        categories: const [
          CategoryOption(label: 'Plumbing'),
          CategoryOption(label: 'Cleaning'),
        ],
      );

      await pumpApp(
        tester,
        initialLocation: AppRoutes.searchFilters,
        overrides: [
          searchRepositoryProvider.overrideWithValue(fakeSearchRepository),
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(fakeSearchRepository.listCategoriesCallCount, 1);
      expect(find.text('All categories'), findsOneWidget);
      expect(find.text('Plumbing'), findsOneWidget);
      expect(find.text('Cleaning'), findsOneWidget);
    },
  );

  testWidgets('the location field pre-fills from the customer\'s default saved '
      'address', (tester) async {
    await pumpApp(
      tester,
      initialLocation: AppRoutes.searchFilters,
      overrides: [
        searchRepositoryProvider.overrideWithValue(FakeSearchRepository()),
        savedAddressRepositoryProvider.overrideWithValue(
          FakeSavedAddressRepository(initialAddresses: const [defaultAddress]),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('Villa 12, Al Wasl Road'), findsOneWidget);
    // The "Search" action is enabled once a location is known.
    expect(
      tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Search'))
          .onPressed,
      isNotNull,
    );
  });

  testWidgets(
    'with no saved addresses, the location field shows "no location set" '
    'and "Search" stays disabled until one is picked',
    (tester) async {
      await pumpApp(
        tester,
        initialLocation: AppRoutes.searchFilters,
        overrides: [
          searchRepositoryProvider.overrideWithValue(FakeSearchRepository()),
          savedAddressRepositoryProvider.overrideWithValue(
            FakeSavedAddressRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('No location set yet'), findsOneWidget);
      expect(
        tester
            .widget<FilledButton>(find.widgetWithText(FilledButton, 'Search'))
            .onPressed,
        isNull,
      );
    },
  );

  testWidgets('"Search" navigates to the Search Results screen and submits the '
      'chosen category, the pre-filled location, and the chosen radius', (
    tester,
  ) async {
    final fakeSearchRepository = FakeSearchRepository(
      categories: const [CategoryOption(label: 'Plumbing')],
    );

    await pumpApp(
      tester,
      initialLocation: AppRoutes.searchFilters,
      overrides: [
        searchRepositoryProvider.overrideWithValue(fakeSearchRepository),
        savedAddressRepositoryProvider.overrideWithValue(
          FakeSavedAddressRepository(initialAddresses: const [defaultAddress]),
        ),
      ],
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Plumbing'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Search'));
    await tester.pumpAndSettle();

    expect(find.byType(SearchResultsScreen), findsOneWidget);
    expect(fakeSearchRepository.searchProvidersCallCount, 1);
    expect(fakeSearchRepository.lastSearchArgs, (
      category: 'Plumbing',
      latitude: defaultAddress.latitude,
      longitude: defaultAddress.longitude,
      radiusKm: 10.0,
      page: 1,
      pageSize: 20,
    ));
  });
}
