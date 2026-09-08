/// Mirrors the backend's `PortfolioPhotoResponse`
/// (`backend/app/modules/provider/schemas.py`, PRO-002, AC2) — one of the
/// caller's own portfolio photos, returned by `GET`/`POST
/// /providers/me/portfolio` and `PUT /providers/me/portfolio/order`.
class PortfolioPhoto {
  const PortfolioPhoto({
    required this.id,
    required this.mediaUrl,
    this.caption,
    required this.sortOrder,
  });

  factory PortfolioPhoto.fromJson(Map<String, dynamic> json) {
    return PortfolioPhoto(
      id: json['id'] as String,
      mediaUrl: json['media_url'] as String,
      caption: json['caption'] as String?,
      sortOrder: (json['sort_order'] as num).toInt(),
    );
  }

  final String id;

  /// A relative, served URL path, e.g. `/media/portfolios/...` — resolve
  /// against `ApiConfig.mediaOrigin` (not `ApiConfig.baseUrl`, which
  /// includes the `/api/v1` prefix media isn't served under) to display it.
  final String mediaUrl;
  final String? caption;
  final int sortOrder;
}
