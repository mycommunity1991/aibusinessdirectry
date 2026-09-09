import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../customer/data/saved_address_repository.dart';
import '../../customer/domain/models/saved_address.dart';
import '../../customer/domain/models/saved_address_exception.dart';
import '../../../shared/widgets/location_picker/location_pick_result.dart';
import '../data/search_repository.dart';
import '../domain/models/category_option.dart';
import '../domain/models/search_exception.dart';

/// The Search Filters screen's (Decision 6, `Plan_S06_DIR-001.md`) load +
/// selection state: the category-chip options (from `listCategories()`),
/// the chosen origin location (pre-filled from the customer's default
/// saved address, editable via `LocationPickerScreen`), and the radius.
class SearchFiltersState {
  const SearchFiltersState({
    this.categories = const [],
    this.isLoadingCategories = true,
    this.categoriesError,
    this.selectedCategory,
    this.latitude,
    this.longitude,
    this.locationLabel,
    this.isLoadingLocation = true,
    this.radiusKm = defaultRadiusKm,
  });

  /// Mirrors the backend's `SEARCH_DEFAULT_RADIUS_KM`
  /// (`backend/app/core/config.py`) -- the radius slider's starting value
  /// before the customer touches it.
  static const double defaultRadiusKm = 10.0;

  /// Mirrors the backend's `SEARCH_MAX_RADIUS_KM`.
  static const double maxRadiusKm = 100.0;

  final List<CategoryOption> categories;
  final bool isLoadingCategories;
  final SearchException? categoriesError;

  /// `null` means "browse all categories" (Decision 1 -- category is
  /// optional).
  final String? selectedCategory;

  final double? latitude;
  final double? longitude;

  /// A short, human-readable label for the current origin -- the default
  /// address's line, or a plain coordinate string once re-picked via the
  /// map/current-location flow.
  final String? locationLabel;
  final bool isLoadingLocation;

  final double radiusKm;

  bool get hasLocation => latitude != null && longitude != null;

  /// The single "Search" action is enabled only once an origin location is
  /// known -- category and radius always have a usable value (optional/
  /// defaulted respectively).
  bool get canSearch => hasLocation;

  SearchFiltersState copyWith({
    List<CategoryOption>? categories,
    bool? isLoadingCategories,
    SearchException? categoriesError,
    bool clearCategoriesError = false,
    String? selectedCategory,
    bool clearSelectedCategory = false,
    double? latitude,
    double? longitude,
    String? locationLabel,
    bool? isLoadingLocation,
    double? radiusKm,
  }) {
    return SearchFiltersState(
      categories: categories ?? this.categories,
      isLoadingCategories: isLoadingCategories ?? this.isLoadingCategories,
      categoriesError: clearCategoriesError
          ? null
          : (categoriesError ?? this.categoriesError),
      selectedCategory: clearSelectedCategory
          ? null
          : (selectedCategory ?? this.selectedCategory),
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      locationLabel: locationLabel ?? this.locationLabel,
      isLoadingLocation: isLoadingLocation ?? this.isLoadingLocation,
      radiusKm: radiusKm ?? this.radiusKm,
    );
  }
}

/// Loads the category picker options and the customer's default saved
/// address (as the pre-filled origin), and tracks the customer's filter
/// selections up to the "Search" action (`Plan_S06_DIR-001.md`, Mobile
/// item 19).
class SearchFiltersController extends StateNotifier<SearchFiltersState> {
  SearchFiltersController(this._searchRepository, this._savedAddressRepository)
    : super(const SearchFiltersState()) {
    _loadCategories();
    _loadDefaultLocation();
  }

  final SearchRepository _searchRepository;
  final SavedAddressRepository _savedAddressRepository;

  Future<void> _loadCategories() async {
    state = state.copyWith(
      isLoadingCategories: true,
      clearCategoriesError: true,
    );
    try {
      final categories = await _searchRepository.listCategories();
      state = state.copyWith(
        categories: categories,
        isLoadingCategories: false,
      );
    } on SearchException catch (error) {
      state = state.copyWith(
        isLoadingCategories: false,
        categoriesError: error,
      );
    }
  }

  /// Pre-fills the origin from the customer's default saved address, if
  /// one exists -- falling back to the first saved address if none is
  /// marked default, and leaving the origin unset (never a hardcoded
  /// fallback coordinate) if the customer has no saved addresses at all.
  /// Silently leaves the origin unset on any failure -- the screen's own
  /// "Search" gating (`SearchFiltersState.canSearch`) already requires a
  /// location, and the customer can always set one via "Pick on map"/"Use
  /// current location" regardless.
  Future<void> _loadDefaultLocation() async {
    state = state.copyWith(isLoadingLocation: true);
    try {
      final addresses = await _savedAddressRepository.list();
      SavedAddress? defaultAddress;
      for (final address in addresses) {
        if (address.isDefault) {
          defaultAddress = address;
          break;
        }
      }
      defaultAddress ??= addresses.isNotEmpty ? addresses.first : null;
      if (defaultAddress != null) {
        state = state.copyWith(
          latitude: defaultAddress.latitude,
          longitude: defaultAddress.longitude,
          locationLabel: defaultAddress.addressLine,
          isLoadingLocation: false,
        );
      } else {
        state = state.copyWith(isLoadingLocation: false);
      }
    } on SavedAddressException {
      state = state.copyWith(isLoadingLocation: false);
    }
  }

  void selectCategory(String? category) {
    state = state.copyWith(
      selectedCategory: category,
      clearSelectedCategory: category == null,
    );
  }

  /// Applies a location picked via `LocationPickerScreen` ("Pick on map" or
  /// "Use current location") -- replaces whatever origin was pre-filled
  /// from the default saved address.
  void setLocation(LocationPickResult result) {
    state = state.copyWith(
      latitude: result.latitude,
      longitude: result.longitude,
      locationLabel:
          result.addressLine ??
          '${result.latitude.toStringAsFixed(4)}, '
              '${result.longitude.toStringAsFixed(4)}',
    );
  }

  void setRadiusKm(double radiusKm) {
    state = state.copyWith(radiusKm: radiusKm);
  }
}

final searchFiltersControllerProvider =
    StateNotifierProvider.autoDispose<
      SearchFiltersController,
      SearchFiltersState
    >(
      (ref) => SearchFiltersController(
        ref.watch(searchRepositoryProvider),
        ref.watch(savedAddressRepositoryProvider),
      ),
    );
