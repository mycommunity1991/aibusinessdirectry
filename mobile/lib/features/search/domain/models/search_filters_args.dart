/// The filters chosen on the Search Filters screen (S-06 entry point,
/// `Plan_S06_DIR-001.md` Decision 6), passed to the Search Results screen
/// (S-08) via GoRouter's `extra` -- mirrors `AddressFormArgs`/
/// `OtpEntryArgs`'s record-typedef pattern.
///
/// [category] is `null` for "browse all categories" (Decision 1 -- category
/// is optional on the backend). [latitude]/[longitude] are always a
/// concrete origin point (either the customer's default saved address or a
/// live device fix via "Use current location") -- the Search Results
/// screen is only ever reached with a fully-resolved origin once the
/// Search Filters screen's "Search" action fires.
typedef SearchFiltersArgs = ({
  String? category,
  double latitude,
  double longitude,
  double radiusKm,
});
