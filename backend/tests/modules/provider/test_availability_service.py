"""
Integration tests for `AvailabilityService` (PRO-002, AC3), exercised
against a real Postgres database (mirrors `test_session_service.py`'s
precedent) -- upsert semantics (create-then-update, not duplicate),
7-entry synthesis, and the ownership boundary (no `{id}` at all, so this
proves it structurally) are all best verified against real repository
queries.
"""

import uuid
from datetime import time

import pytest

from app.core.exceptions import ProviderNotFoundError
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
    Weekday,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.portfolio_repository import (
    PortfolioRepository,
)
from app.modules.provider.repositories.provider_availability_repository import (
    ProviderAvailabilityRepository,
)
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
from app.modules.provider.services.availability_service import AvailabilityService
from app.modules.provider.services.provider_service import ProviderService


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_provider(db_session, user: User, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Plumbing",
        "slug": f"acme-plumbing-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.PENDING,
        "is_discoverable": False,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


def _provider_service(db_session) -> ProviderService:
    return ProviderService(
        provider_repository=ProviderRepository(db_session),
        business_profile_repository=BusinessProfileRepository(db_session),
        freelancer_profile_repository=FreelancerProfileRepository(db_session),
        provider_category_label_repository=ProviderCategoryLabelRepository(db_session),
        service_area_repository=ServiceAreaRepository(db_session),
        role_assignment_service=RoleAssignmentService(RoleRepository(db_session)),
        provider_search_repository=ProviderSearchRepository(db_session),
        portfolio_repository=PortfolioRepository(db_session),
    )


def _availability_service(db_session) -> AvailabilityService:
    return AvailabilityService(
        provider_availability_repository=ProviderAvailabilityRepository(db_session),
        provider_service=_provider_service(db_session),
    )


def _monday_open_entry(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "weekday": Weekday.MONDAY,
        "open_time": time(9, 0),
        "close_time": time(18, 0),
        "is_emergency_available": False,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestGetMyAvailabilityBeforeAnyPut:
    @pytest.mark.anyio
    async def test_returns_seven_synthesized_closed_entries(self, db_session) -> None:
        """AC3: `GET`-equivalent before any `PUT` returns all 7 weekdays,
        each closed (both times `None`)."""
        user = await _create_user(db_session, "506000001")
        await _create_provider(db_session, user)
        service = _availability_service(db_session)

        entries = await service.get_my_availability(user.id)

        assert len(entries) == 7
        assert {e.weekday for e in entries} == set(Weekday)
        assert all(e.open_time is None and e.close_time is None for e in entries)
        assert all(e.is_emergency_available is False for e in entries)

    @pytest.mark.anyio
    async def test_raises_not_found_for_a_caller_with_no_provider(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "506000002")
        service = _availability_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.get_my_availability(user.id)


class TestUpdateMyAvailability:
    @pytest.mark.anyio
    async def test_first_put_creates_all_submitted_rows(self, db_session) -> None:
        user = await _create_user(db_session, "506000003")
        await _create_provider(db_session, user)
        service = _availability_service(db_session)

        result = await service.update_my_availability(user.id, [_monday_open_entry()])

        monday = next(e for e in result if e.weekday == Weekday.MONDAY)
        assert monday.open_time == time(9, 0)
        assert monday.close_time == time(18, 0)
        # The other 6 weekdays remain synthesized-closed.
        assert len(result) == 7
        others = [e for e in result if e.weekday != Weekday.MONDAY]
        assert all(e.open_time is None for e in others)

    @pytest.mark.anyio
    async def test_second_put_updates_the_same_row_not_a_duplicate(
        self, db_session
    ) -> None:
        """A second `PUT` with different values updates (not
        duplicates) the same weekday row."""
        user = await _create_user(db_session, "506000004")
        await _create_provider(db_session, user)
        service = _availability_service(db_session)

        await service.update_my_availability(user.id, [_monday_open_entry()])
        result = await service.update_my_availability(
            user.id,
            [
                _monday_open_entry(
                    open_time=time(10, 0),
                    close_time=time(20, 0),
                    is_emergency_available=True,
                )
            ],
        )

        monday_entries = [e for e in result if e.weekday == Weekday.MONDAY]
        assert len(monday_entries) == 1
        assert monday_entries[0].open_time == time(10, 0)
        assert monday_entries[0].close_time == time(20, 0)
        assert monday_entries[0].is_emergency_available is True

        # Confirm no duplicate row was created at the repository level.
        rows = await ProviderAvailabilityRepository(db_session).list_for_provider(
            (await _provider_service(db_session).get_my_provider(user.id)).id
        )
        assert len([r for r in rows if r.weekday == Weekday.MONDAY]) == 1

    @pytest.mark.anyio
    async def test_a_closed_day_has_null_open_and_close_time(self, db_session) -> None:
        user = await _create_user(db_session, "506000005")
        await _create_provider(db_session, user)
        service = _availability_service(db_session)

        result = await service.update_my_availability(
            user.id,
            [
                {
                    "weekday": Weekday.TUESDAY,
                    "open_time": None,
                    "close_time": None,
                    "is_emergency_available": False,
                }
            ],
        )

        tuesday = next(e for e in result if e.weekday == Weekday.TUESDAY)
        assert tuesday.open_time is None
        assert tuesday.close_time is None

    @pytest.mark.anyio
    async def test_a_second_providers_availability_is_never_affected(
        self, db_session
    ) -> None:
        """AC7/AC8: this endpoint has no `{id}` at all -- ownership is
        structural, proven by resolving strictly from each caller's own
        `user_id`."""
        first_user = await _create_user(db_session, "506000006")
        await _create_provider(db_session, first_user)
        second_user = await _create_user(db_session, "506000007")
        await _create_provider(db_session, second_user, display_name="Other Co")
        service = _availability_service(db_session)

        await service.update_my_availability(first_user.id, [_monday_open_entry()])

        second_result = await service.get_my_availability(second_user.id)
        assert all(e.open_time is None for e in second_result)


class TestGetAvailabilityForProvider:
    """
    CON-001, Decision 6, `Plan_S08_CON-001.md` -- the same seven-day
    synthesis, keyed by an arbitrary `provider_id` rather than the
    caller's own `user_id`, no ownership check.
    """

    @pytest.mark.anyio
    async def test_returns_seven_synthesized_closed_entries_for_a_fresh_provider(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "506000008")
        provider = await _create_provider(db_session, user)
        service = _availability_service(db_session)

        entries = await service.get_availability_for_provider(provider.id)

        assert len(entries) == 7
        assert {e.weekday for e in entries} == set(Weekday)
        assert all(e.open_time is None and e.close_time is None for e in entries)

    @pytest.mark.anyio
    async def test_matches_get_my_availability_for_an_equivalent_fixture(
        self, db_session
    ) -> None:
        """Arbitrary-target lookup produces byte-for-byte the same
        entries `get_my_availability` would for its own caller."""
        user = await _create_user(db_session, "506000009")
        provider = await _create_provider(db_session, user)
        service = _availability_service(db_session)
        await service.update_my_availability(user.id, [_monday_open_entry()])

        via_owner = await service.get_my_availability(user.id)
        via_arbitrary_target = await service.get_availability_for_provider(provider.id)

        assert via_owner == via_arbitrary_target

    @pytest.mark.anyio
    async def test_requires_no_ownership_and_is_called_by_a_different_caller(
        self, db_session
    ) -> None:
        """No `ProviderNotFoundError`/ownership check exists for this
        method at all -- any resolved `provider_id` works, regardless of
        who is asking."""
        owner = await _create_user(db_session, "506000010")
        provider = await _create_provider(
            db_session, owner, display_name="Someone Else"
        )
        service = _availability_service(db_session)

        entries = await service.get_availability_for_provider(provider.id)

        assert len(entries) == 7
