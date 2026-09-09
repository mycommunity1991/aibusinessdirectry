/// Mirrors the backend's `CategoryOptionResponse`
/// (`backend/app/modules/search/schemas.py`, DIR-001, Decision 1) -- one
/// distinct category label in use by a discoverable provider, backing the
/// Search Filters screen's category chip picker.
class CategoryOption {
  const CategoryOption({required this.label});

  factory CategoryOption.fromJson(Map<String, dynamic> json) {
    return CategoryOption(label: json['label'] as String);
  }

  final String label;
}
