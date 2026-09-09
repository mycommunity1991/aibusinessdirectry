"""
CLI entry point to bulk-import / re-sync Google Places listings as
Google-seeded-unclaimed Provider rows (CLM-001, Decision 1,
`Plan_S06_CLM-001.md`).

Follows `seed_roles.py`/`grant_admin_role.py`'s exact shape: a thin
`async def main()` using `app.database.session.async_session` directly,
no HTTP layer or FastAPI DI container involved -- no scheduler/cron
infrastructure exists anywhere in this codebase (Decision 1), and none
is introduced by this story.

The **same script run** is both "the bulk seed" (first run, every place
is new) and "a subsequent sync job" (later runs, most places already
exist) -- idempotency is achieved by looking up each fetched place's
`google_place_id` via `ProviderRepository.get_by_google_place_id`
before deciding whether to create (`ProviderService.
create_google_seeded_provider`) or backfill-only
(`ProviderService.backfill_google_seeded_provider`, AC7's field-write
policy). A place missing `name`/`geometry.location`/`formatted_address`
is skipped, never imported with a fabricated address/coordinates
(Decision 3, enforced by `google_places_client.map_place_details`).

Usage (from the `backend/` directory, so `app`/`scripts` are importable):
    uv run python -m scripts.import_google_places \\
        --query "plumbers in Dubai" --country-code AE
"""

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import async_session
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import VerificationStatus
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.portfolio_repository import PortfolioRepository
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.provider_search_repository import (
    ProviderSearchRepository,
)
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.services.google_places_client import (
    GooglePlacesClient,
    HttpxGooglePlacesClient,
    MappedGooglePlace,
)
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.models import VerificationType
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportSummary:
    """Outcome counts for one `import_places` run -- returned so both
    the CLI's own logging and a test can assert on the exact numbers."""

    created: int
    backfilled: int
    skipped: int


def _provider_service(session: AsyncSession) -> ProviderService:
    """
    Direct-construction wiring, script-level (not FastAPI's DI
    container, since there is no request scope here) -- mirrors
    `test_admin_verification_service.py`'s own `_provider_service`
    helper exactly.
    """
    return ProviderService(
        provider_repository=ProviderRepository(session),
        business_profile_repository=BusinessProfileRepository(session),
        freelancer_profile_repository=FreelancerProfileRepository(session),
        provider_category_label_repository=ProviderCategoryLabelRepository(session),
        service_area_repository=ServiceAreaRepository(session),
        role_assignment_service=RoleAssignmentService(RoleRepository(session)),
        provider_search_repository=ProviderSearchRepository(session),
        portfolio_repository=PortfolioRepository(session),
    )


def _business_details(mapped: MappedGooglePlace) -> dict[str, object]:
    """
    Decision 3's field mapping, `BusinessProfile`-shaped --
    `trade_license_number` is deliberately never a key here (Google
    never provides it), so neither `create_google_seeded_provider` nor
    `backfill_google_seeded_provider` ever touches it.
    """
    return {
        "address_line": mapped.address_line,
        "city": mapped.city,
        "region": mapped.region,
        "latitude": mapped.latitude,
        "longitude": mapped.longitude,
        "operating_hours": mapped.operating_hours,
        "delivery_radius_meters": None,
    }


async def import_places(
    session: AsyncSession,
    google_places_client: GooglePlacesClient,
    *,
    text_query: str,
    country_code: str,
) -> ImportSummary:
    """
    Fetches places matching `text_query` and creates-or-backfills a
    Google-seeded-unclaimed Provider for each (Decision 1/2/3/4). Flush
    only -- the caller (`main()` below, or a test) controls the commit
    boundary.
    """
    provider_repository = ProviderRepository(session)
    provider_service = _provider_service(session)
    verification_record_repository = VerificationRecordRepository(session)

    place_ids = await google_places_client.search_places(
        text_query=text_query, region=country_code
    )

    created = 0
    backfilled = 0
    skipped = 0

    for place_id in place_ids:
        mapped = await google_places_client.get_place_details(place_id)
        if mapped is None:
            logger.warning(
                "Skipping place_id=%s -- missing a required field "
                "(name/geometry.location/formatted_address).",
                place_id,
            )
            skipped += 1
            continue

        resolved_country_code = mapped.country_code or country_code
        business_details = _business_details(mapped)

        existing = await provider_repository.get_by_google_place_id(
            mapped.google_place_id
        )
        if existing is None:
            provider = await provider_service.create_google_seeded_provider(
                google_place_id=mapped.google_place_id,
                display_name=mapped.display_name,
                phone_country_code=mapped.phone_country_code,
                phone_number=mapped.phone_number,
                country_code=resolved_country_code,
                business_details=business_details,
                category_label=mapped.category_label,
            )
            # Decision 2: a matching, system-generated
            # `verification_records` row, kept honestly in sync with
            # `providers.verification_status=approved` -- `reviewed_by
            # =None` since no human admin reviewed it.
            await verification_record_repository.create(
                {
                    "provider_id": provider.id,
                    "verification_type": VerificationType.BUSINESS_LIGHTWEIGHT,
                    "status": VerificationStatus.APPROVED,
                    "submitted_at": datetime.now(UTC),
                    "reviewed_at": datetime.now(UTC),
                    "reviewed_by": None,
                }
            )
            created += 1
        else:
            await provider_service.backfill_google_seeded_provider(
                existing,
                display_name=mapped.display_name,
                phone_country_code=mapped.phone_country_code,
                phone_number=mapped.phone_number,
                country_code=resolved_country_code,
                business_details=business_details,
                category_label=mapped.category_label,
            )
            backfilled += 1

    return ImportSummary(created=created, backfilled=backfilled, skipped=skipped)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk-import or re-sync Google Places listings as "
            "Google-seeded-unclaimed Provider rows."
        )
    )
    parser.add_argument(
        "--query",
        required=True,
        help='Free-text search query, e.g. "plumbers in Dubai".',
    )
    parser.add_argument(
        "--country-code",
        required=True,
        help=(
            "ISO 3166-1 alpha-2 country code, e.g. AE -- biases the search "
            "and is used as a fallback if a place's own address components "
            "don't include a country."
        ),
    )
    return parser.parse_args()


async def main(text_query: str, country_code: str) -> None:
    if not settings.GOOGLE_PLACES_API_KEY:
        raise SystemExit(
            "GOOGLE_PLACES_API_KEY is not set -- required to run this script "
            "(deliberately optional at app-boot time, Decision 10; required "
            "only here)."
        )

    async with httpx.AsyncClient() as http_client:
        google_places_client = HttpxGooglePlacesClient(
            api_key=settings.GOOGLE_PLACES_API_KEY, http_client=http_client
        )
        async with async_session() as session:
            summary = await import_places(
                session,
                google_places_client,
                text_query=text_query,
                country_code=country_code,
            )
            await session.commit()

    logger.info(
        "Google Places import complete: created=%d backfilled=%d skipped=%d",
        summary.created,
        summary.backfilled,
        summary.skipped,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    asyncio.run(main(args.query, args.country_code))
