"""
Google Places API client (CLM-001, Decision 10, `Plan_S06_CLM-001.md`).

A swappable `GooglePlacesClient` Protocol -- mirroring `DocumentOcrService`
(ADR-018)/`FileStorage` (ADR-017)'s already-established "external
capability with no live-tested implementation in CI" shape -- with
`HttpxGooglePlacesClient` as the real implementation (plain REST calls
via the already-approved `httpx` dependency, no new SDK) and
`FakeGooglePlacesClient` for tests (AC8: no automated test may make a
real network call to a paid third-party API).

Field names throughout (`geometry.location`, `formatted_address`,
`international_phone_number`, `address_components`, `opening_hours.
periods`, `types`) are the legacy Google Places API (Place Search/Place
Details) JSON shape -- the exact shape Decision 3's field-mapping table
is written against.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
# Google's `opening_hours.periods[].open.day`/`close.day` use 0=Sunday,
# matching `datetime.weekday()`'s convention but offset by one --
# translated to this codebase's `provider.weekday` enum values (Monday-
# first) here, once, rather than re-derived at every call site.
_GOOGLE_DAY_INDEX_TO_WEEKDAY = {
    0: "sunday",
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
}
# A tiny, best-effort lookup for Decision 3's "humanized primary category
# label" -- deliberately small and interim, mirroring DIR-001 Decision
# 1's identical posture pending the real Category taxonomy
# (`13_OPEN_DECISIONS.md` item 1). Falls back to a titleized version of
# the raw Google `types[0]` value for any type not in this table.
_GOOGLE_TYPE_LABELS: dict[str, str] = {
    "plumber": "Plumbing",
    "electrician": "Electrical",
    "restaurant": "Restaurant",
    "cafe": "Cafe",
    "beauty_salon": "Beauty Salon",
    "hair_care": "Hair Care",
    "car_repair": "Auto Repair",
    "florist": "Florist",
    "bakery": "Bakery",
    "gym": "Fitness",
    "lawyer": "Legal Services",
    "dentist": "Dental",
    "doctor": "Medical",
    "real_estate_agency": "Real Estate",
}


@dataclass(frozen=True)
class MappedGooglePlace:
    """
    One Google Place, already mapped onto this codebase's
    `providers`/`business_profiles` field shape (Decision 3's field
    table) -- the shared output of both `HttpxGooglePlacesClient` and
    `FakeGooglePlacesClient`'s `get_place_details`, so the import
    script's own logic never branches on which implementation produced
    it.
    """

    google_place_id: str
    display_name: str
    address_line: str
    latitude: float
    longitude: float
    phone_country_code: str | None
    phone_number: str | None
    city: str | None
    region: str | None
    country_code: str
    operating_hours: dict[str, dict[str, str] | None] | None
    category_label: str | None


class GooglePlacesClient(Protocol):
    """
    Swappable Google Places API capability -- the import script's own
    service layer depends on this Protocol, never on a concrete class
    (Decision 10), exactly like `VerificationService` depends on
    `DocumentOcrService`.
    """

    async def search_places(
        self, *, text_query: str, region: str | None = None
    ) -> list[str]:
        """Returns the `place_id`s matching a free-text search query."""
        ...

    async def get_place_details(self, place_id: str) -> MappedGooglePlace | None:
        """
        Fetches and maps one place's details (Decision 3). Returns
        `None` if the place is missing any of `name`/`geometry.location`/
        `formatted_address` -- the fields with no nullable column to
        fall back to (Decision 3) -- so it is skipped, never imported
        with a fabricated address/coordinates.
        """
        ...


def _extract_address_component(
    address_components: list[dict[str, Any]], component_type: str, *, short: bool
) -> str | None:
    for component in address_components:
        if component_type in component.get("types", []):
            key = "short_name" if short else "long_name"
            value = component.get(key)
            return str(value) if value else None
    return None


def _parse_phone(
    international_phone_number: str | None,
) -> tuple[str | None, str | None]:
    """
    Best-effort split of Google's `international_phone_number` (e.g.
    `"+971 4 123 4567"`) into `phone_country_code`/`phone_number` --
    the country-calling-code token is the first whitespace-delimited
    segment, everything else (digits only) is the subscriber number.
    Returns `(None, None)` if Google has no public phone number for
    this place (Decision 3 -- never fabricated).
    """
    if not international_phone_number:
        return None, None

    parts = international_phone_number.strip().split(" ", 1)
    if len(parts) != 2 or not parts[0].startswith("+"):
        return None, None

    country_code = parts[0]
    subscriber_digits = "".join(ch for ch in parts[1] if ch.isdigit())
    if not subscriber_digits:
        return None, None
    return country_code, subscriber_digits


def _map_operating_hours(
    opening_hours: dict[str, Any] | None,
) -> dict[str, dict[str, str] | None] | None:
    """
    Best-effort maps Google's `opening_hours.periods` onto this schema's
    single open/close-per-weekday JSONB shape (Decision 3) -- the first
    period per day if multiple exist (e.g. a lunch-break split).
    Returns `None` if Google provides no periods at all (never
    fabricated "closed all day").
    """
    if not opening_hours:
        return None
    periods = opening_hours.get("periods")
    if not periods:
        return None

    mapped: dict[str, dict[str, str] | None] = {}
    for period in periods:
        open_info = period.get("open")
        close_info = period.get("close")
        if not open_info or not close_info:
            continue
        weekday = _GOOGLE_DAY_INDEX_TO_WEEKDAY.get(open_info.get("day"))
        if weekday is None or weekday in mapped:
            continue
        open_time = open_info.get("time")
        close_time = close_info.get("time")
        if not open_time or not close_time:
            continue
        mapped[weekday] = {
            "open": f"{open_time[:2]}:{open_time[2:]}",
            "close": f"{close_time[:2]}:{close_time[2:]}",
        }

    return mapped or None


def _map_category_label(types: list[str] | None) -> str | None:
    if not types:
        return None
    raw_type = types[0]
    return _GOOGLE_TYPE_LABELS.get(raw_type, raw_type.replace("_", " ").title())


def map_place_details(raw: dict[str, Any]) -> MappedGooglePlace | None:
    """
    Maps one raw Google Place Details `result` object onto
    `MappedGooglePlace` per Decision 3's field table. Returns `None`
    (skip, never fabricate) if `name`/`geometry.location`/
    `formatted_address` is missing -- the three fields with no nullable
    column to fall back to.
    """
    place_id = raw.get("place_id")
    name = raw.get("name")
    geometry = raw.get("geometry") or {}
    location = geometry.get("location") or {}
    latitude = location.get("lat")
    longitude = location.get("lng")
    formatted_address = raw.get("formatted_address")

    if not place_id or not name or not formatted_address:
        return None
    if latitude is None or longitude is None:
        return None

    address_components = raw.get("address_components") or []
    phone_country_code, phone_number = _parse_phone(
        raw.get("international_phone_number")
    )

    return MappedGooglePlace(
        google_place_id=str(place_id),
        display_name=str(name),
        address_line=str(formatted_address),
        latitude=float(latitude),
        longitude=float(longitude),
        phone_country_code=phone_country_code,
        phone_number=phone_number,
        city=_extract_address_component(address_components, "locality", short=False),
        region=_extract_address_component(
            address_components, "administrative_area_level_1", short=False
        ),
        country_code=(
            _extract_address_component(address_components, "country", short=True) or ""
        ),
        operating_hours=_map_operating_hours(raw.get("opening_hours")),
        category_label=_map_category_label(raw.get("types")),
    )


class HttpxGooglePlacesClient:
    """
    Real `GooglePlacesClient` implementation, using plain `httpx` REST
    calls against the legacy Google Places API (Text Search + Place
    Details) -- no Google Maps/Places SDK dependency (Decision 10).
    Only ever constructed by `scripts/import_google_places.py`; never
    wired into the FastAPI DI container, since no request-time endpoint
    in this story calls Google Places directly.
    """

    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http_client = http_client

    async def search_places(
        self, *, text_query: str, region: str | None = None
    ) -> list[str]:
        params: dict[str, str] = {"query": text_query, "key": self._api_key}
        if region:
            params["region"] = region

        response = await self._http_client.get(_TEXT_SEARCH_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        return [
            str(result["place_id"])
            for result in payload.get("results", [])
            if result.get("place_id")
        ]

    async def get_place_details(self, place_id: str) -> MappedGooglePlace | None:
        params = {"place_id": place_id, "key": self._api_key}
        response = await self._http_client.get(_PLACE_DETAILS_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result")
        if not result:
            logger.warning("No Place Details result for place_id=%s", place_id)
            return None
        return map_place_details(result)


@dataclass
class FakeGooglePlacesClient:
    """
    Test-only `GooglePlacesClient` -- returns canned fixture places
    instead of making any real network call (AC8). `place_ids` drives
    `search_places`'s return value; `details_by_place_id` holds the raw
    (unmapped) Google-shaped `dict` for each id, mapped on the fly via
    `map_place_details` (the identical mapping/skip logic
    `HttpxGooglePlacesClient` uses), so a test can exercise the "missing
    required field -> skipped" path by supplying an intentionally
    incomplete raw dict.
    """

    place_ids: list[str] = field(default_factory=list)
    details_by_place_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def search_places(
        self, *, text_query: str, region: str | None = None
    ) -> list[str]:
        return list(self.place_ids)

    async def get_place_details(self, place_id: str) -> MappedGooglePlace | None:
        raw = self.details_by_place_id.get(place_id)
        if raw is None:
            return None
        return map_place_details(raw)
