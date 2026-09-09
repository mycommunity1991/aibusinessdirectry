"""
Integration tests for `scripts/import_google_places.import_places`
(CLM-001, Decision 1/2/3/4, `Plan_S06_CLM-001.md`) -- exercised against
a real Postgres database with `FakeGooglePlacesClient` (AC8: no test
ever makes a real network call to a paid third-party API).
"""

from sqlalchemy import select

from app.modules.provider.models import (
    BusinessProfile,
    ListingSource,
    Provider,
    ServiceArea,
    VerificationStatus,
)
from app.modules.provider.services.google_places_client import FakeGooglePlacesClient
from app.modules.verification.models import VerificationRecord, VerificationType
from scripts.import_google_places import import_places

_VALID_PLACE = {
    "place_id": "ChIJ_fixture_place_1",
    "name": "Al Noor Plumbing Services LLC",
    "formatted_address": "Shop 12, Al Wasl Road, Dubai, United Arab Emirates",
    "geometry": {"location": {"lat": 25.2048, "lng": 55.2708}},
    "international_phone_number": "+971 4 333 4455",
    "address_components": [
        {"types": ["locality"], "long_name": "Dubai", "short_name": "Dubai"},
        {
            "types": ["administrative_area_level_1"],
            "long_name": "Dubai",
            "short_name": "DU",
        },
        {
            "types": ["country"],
            "long_name": "United Arab Emirates",
            "short_name": "AE",
        },
    ],
    "opening_hours": {
        "periods": [
            {
                "open": {"day": 1, "time": "0900"},
                "close": {"day": 1, "time": "1800"},
            }
        ]
    },
    "types": ["plumber", "point_of_interest"],
}

_MISSING_ADDRESS_PLACE = {
    "place_id": "ChIJ_fixture_place_missing",
    "name": "Ghost Listing",
    # `formatted_address` deliberately omitted -- Decision 3's required
    # field with no nullable fallback.
    "geometry": {"location": {"lat": 25.1, "lng": 55.1}},
}


class TestFreshImport:
    async def test_creates_a_provider_row_with_the_exact_ac1_fields(
        self, db_session
    ) -> None:
        fake_client = FakeGooglePlacesClient(
            place_ids=[_VALID_PLACE["place_id"]],
            details_by_place_id={_VALID_PLACE["place_id"]: _VALID_PLACE},
        )

        summary = await import_places(
            db_session,
            fake_client,
            text_query="plumbers in Dubai",
            country_code="AE",
        )
        await db_session.commit()

        assert summary.created == 1
        assert summary.backfilled == 0
        assert summary.skipped == 0

        result = await db_session.execute(
            select(Provider).where(Provider.google_place_id == _VALID_PLACE["place_id"])
        )
        provider = result.scalar_one()
        assert provider.listing_source == ListingSource.GOOGLE_SEEDED_UNCLAIMED
        assert provider.listing_source != ListingSource.SELF_REGISTERED
        assert provider.is_claimed is False
        assert provider.user_id is None
        assert provider.verification_status == VerificationStatus.APPROVED
        assert provider.is_discoverable is True
        assert provider.country_code == "AE"
        assert provider.phone_country_code == "+971"
        assert provider.phone_number == "43334455"

        business_result = await db_session.execute(
            select(BusinessProfile).where(BusinessProfile.provider_id == provider.id)
        )
        business_profile = business_result.scalar_one()
        assert business_profile.city == "Dubai"

        service_area_result = await db_session.execute(
            select(ServiceArea).where(ServiceArea.provider_id == provider.id)
        )
        assert service_area_result.scalar_one() is not None

        record_result = await db_session.execute(
            select(VerificationRecord).where(
                VerificationRecord.provider_id == provider.id
            )
        )
        record = record_result.scalar_one()
        assert record.status == VerificationStatus.APPROVED
        assert record.verification_type == VerificationType.BUSINESS_LIGHTWEIGHT
        assert record.reviewed_by is None


class TestIdempotentReimport:
    async def test_rerunning_against_unchanged_data_does_not_duplicate(
        self, db_session
    ) -> None:
        fake_client = FakeGooglePlacesClient(
            place_ids=[_VALID_PLACE["place_id"]],
            details_by_place_id={_VALID_PLACE["place_id"]: _VALID_PLACE},
        )

        await import_places(
            db_session, fake_client, text_query="plumbers in Dubai", country_code="AE"
        )
        await db_session.commit()

        summary = await import_places(
            db_session, fake_client, text_query="plumbers in Dubai", country_code="AE"
        )
        await db_session.commit()

        assert summary.created == 0
        assert summary.backfilled == 1

        result = await db_session.execute(
            select(Provider).where(Provider.google_place_id == _VALID_PLACE["place_id"])
        )
        providers = result.scalars().all()
        assert len(providers) == 1

    async def test_backfill_updates_an_unclaimed_listing_with_fresh_data(
        self, db_session
    ) -> None:
        fake_client = FakeGooglePlacesClient(
            place_ids=[_VALID_PLACE["place_id"]],
            details_by_place_id={_VALID_PLACE["place_id"]: _VALID_PLACE},
        )
        await import_places(
            db_session, fake_client, text_query="plumbers in Dubai", country_code="AE"
        )
        await db_session.commit()

        updated_place = dict(_VALID_PLACE)
        updated_place["name"] = "Al Noor Plumbing Services LLC (Renamed)"
        fake_client.details_by_place_id[_VALID_PLACE["place_id"]] = updated_place

        await import_places(
            db_session, fake_client, text_query="plumbers in Dubai", country_code="AE"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Provider).where(Provider.google_place_id == _VALID_PLACE["place_id"])
        )
        provider = result.scalar_one()
        assert provider.display_name == "Al Noor Plumbing Services LLC (Renamed)"


class TestMissingRequiredFieldIsSkipped:
    async def test_a_place_missing_formatted_address_is_skipped_not_imported(
        self, db_session
    ) -> None:
        fake_client = FakeGooglePlacesClient(
            place_ids=[_MISSING_ADDRESS_PLACE["place_id"]],
            details_by_place_id={
                _MISSING_ADDRESS_PLACE["place_id"]: _MISSING_ADDRESS_PLACE
            },
        )

        summary = await import_places(
            db_session, fake_client, text_query="ghosts", country_code="AE"
        )
        await db_session.commit()

        assert summary.created == 0
        assert summary.skipped == 1

        result = await db_session.execute(
            select(Provider).where(
                Provider.google_place_id == _MISSING_ADDRESS_PLACE["place_id"]
            )
        )
        assert result.scalar_one_or_none() is None
