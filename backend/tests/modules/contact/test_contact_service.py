"""
Integration tests for `ContactService` (CON-001, AC1/AC3/AC4/AC7/AC8),
exercised against a real Postgres database -- this story's single most
safety-critical mechanism (the self-dealing guard, Decision 1,
`Plan_S08_CON-001.md`) is verified here with a direct row-count
assertion, not merely an exception check (AC4's literal wording).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import (
    CustomerProfileNotFoundError,
    ProviderNotFoundError,
    SearchRequestNotFoundError,
    SelfDealingContactError,
)
from app.modules.contact.models import ContactView
from app.modules.notification.models import Notification
from app.modules.search.models import SearchRequest, SearchRequestStatus

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_contact_service,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _count_contact_views(db_session) -> int:
    result = await db_session.execute(select(ContactView))
    return len(result.scalars().all())


async def _count_notifications(db_session) -> int:
    result = await db_session.execute(select(Notification))
    return len(result.scalars().all())


async def _create_search_request(db_session, customer_id: uuid.UUID) -> SearchRequest:
    search_request = SearchRequest(
        customer_id=customer_id,
        status=SearchRequestStatus.MATCHED,
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)
    return search_request


class TestCreateContactViewHappyPath:
    @pytest.mark.anyio
    async def test_creates_exactly_one_row_and_returns_the_providers_contact_data(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "501000001")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000002")
        provider = await create_provider(
            db_session,
            user=provider_owner,
            phone_country_code="+971",
            phone_number="43334455",
            whatsapp_number="43334455",
            display_name="Al Noor Plumbing",
        )
        service = make_contact_service(db_session)

        assert await _count_contact_views(db_session) == 0

        contact_view, returned_provider = await service.create_contact_view(
            customer_user.id, provider_id=provider.id, search_request_id=None
        )
        await db_session.commit()

        assert await _count_contact_views(db_session) == 1
        assert contact_view.customer_id == customer_profile.id
        assert contact_view.provider_id == provider.id
        assert contact_view.search_request_id is None
        assert returned_provider.id == provider.id
        assert returned_provider.phone_country_code == "+971"
        assert returned_provider.phone_number == "43334455"
        assert returned_provider.whatsapp_number == "43334455"
        assert returned_provider.display_name == "Al Noor Plumbing"


class TestSelfDealingRejection:
    """AC3/AC4: the platform's single most safety-critical rule."""

    @pytest.mark.anyio
    async def test_raises_and_creates_no_row_when_the_same_account_owns_both(
        self, db_session
    ) -> None:
        # The same Account holds both a `customer_profiles` row and a
        # `providers` row -- the exact dual-role fixture AC4 requires.
        shared_user = await create_user(db_session, "501000003")
        await create_customer_profile(db_session, shared_user)
        provider = await create_provider(db_session, user=shared_user)
        service = make_contact_service(db_session)

        with pytest.raises(SelfDealingContactError):
            await service.create_contact_view(
                shared_user.id, provider_id=provider.id, search_request_id=None
            )

        # Not merely "an exception was raised" -- assert the row was
        # genuinely never written (AC4's literal wording).
        assert await _count_contact_views(db_session) == 0

    @pytest.mark.anyio
    async def test_does_not_notify_on_a_rejected_self_dealing_attempt(
        self, db_session
    ) -> None:
        shared_user = await create_user(db_session, "501000004")
        await create_customer_profile(db_session, shared_user)
        provider = await create_provider(db_session, user=shared_user)
        service = make_contact_service(db_session)

        with pytest.raises(SelfDealingContactError):
            await service.create_contact_view(
                shared_user.id, provider_id=provider.id, search_request_id=None
            )

        assert await _count_notifications(db_session) == 0


class TestUnclaimedListingContact:
    """An unclaimed, Google-seeded listing has no owning Account, so it
    can never self-deal by construction (Decision 1)."""

    @pytest.mark.anyio
    async def test_succeeds_with_no_self_dealing_rejection(self, db_session) -> None:
        customer_user = await create_user(db_session, "501000005")
        await create_customer_profile(db_session, customer_user)
        unclaimed_provider = await create_provider(
            db_session,
            user=None,
            google_place_id=f"ChIJ_{uuid.uuid4().hex[:10]}",
        )
        service = make_contact_service(db_session)

        contact_view, _provider = await service.create_contact_view(
            customer_user.id,
            provider_id=unclaimed_provider.id,
            search_request_id=None,
        )
        await db_session.commit()

        assert contact_view.provider_id == unclaimed_provider.id
        assert await _count_contact_views(db_session) == 1

    @pytest.mark.anyio
    async def test_creates_no_notification(self, db_session) -> None:
        customer_user = await create_user(db_session, "501000006")
        await create_customer_profile(db_session, customer_user)
        unclaimed_provider = await create_provider(
            db_session,
            user=None,
            google_place_id=f"ChIJ_{uuid.uuid4().hex[:10]}",
        )
        service = make_contact_service(db_session)

        await service.create_contact_view(
            customer_user.id,
            provider_id=unclaimed_provider.id,
            search_request_id=None,
        )
        await db_session.commit()

        assert await _count_notifications(db_session) == 0


class TestClaimedProviderNotification:
    """AC7: every Contact View creation against a claimed provider is a
    candidate trigger for a provider-lead notification."""

    @pytest.mark.anyio
    async def test_creates_exactly_one_notification_addressed_to_the_owner(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "501000007")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000008")
        provider = await create_provider(db_session, user=provider_owner)
        service = make_contact_service(db_session)

        contact_view, _provider = await service.create_contact_view(
            customer_user.id, provider_id=provider.id, search_request_id=None
        )
        await db_session.commit()

        result = await db_session.execute(select(Notification))
        notifications = result.scalars().all()
        assert len(notifications) == 1
        assert notifications[0].user_id == provider_owner.id
        assert notifications[0].related_entity_id == contact_view.id
        assert notifications[0].related_entity_type == "contact_view"


class TestSearchRequestIdValidation:
    """Decision 4: never trust, never silently drop a mismatched
    `search_request_id`."""

    @pytest.mark.anyio
    async def test_the_callers_own_search_request_is_accepted(self, db_session) -> None:
        customer_user = await create_user(db_session, "501000009")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000010")
        provider = await create_provider(db_session, user=provider_owner)
        search_request = await _create_search_request(db_session, customer_profile.id)
        service = make_contact_service(db_session)

        contact_view, _provider = await service.create_contact_view(
            customer_user.id,
            provider_id=provider.id,
            search_request_id=search_request.id,
        )
        await db_session.commit()

        assert contact_view.search_request_id == search_request.id

    @pytest.mark.anyio
    async def test_another_customers_search_request_is_rejected_with_404(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "501000011")
        await create_customer_profile(db_session, customer_user)
        other_customer_user = await create_user(db_session, "501000012")
        other_customer_profile = await create_customer_profile(
            db_session, other_customer_user
        )
        provider_owner = await create_user(db_session, "501000013")
        provider = await create_provider(db_session, user=provider_owner)
        other_search_request = await _create_search_request(
            db_session, other_customer_profile.id
        )
        service = make_contact_service(db_session)

        with pytest.raises(SearchRequestNotFoundError):
            await service.create_contact_view(
                customer_user.id,
                provider_id=provider.id,
                search_request_id=other_search_request.id,
            )

        # The mismatch is rejected outright -- never silently coerced,
        # and no row is created either.
        assert await _count_contact_views(db_session) == 0

    @pytest.mark.anyio
    async def test_a_nonexistent_search_request_id_is_rejected_with_404(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "501000014")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000015")
        provider = await create_provider(db_session, user=provider_owner)
        service = make_contact_service(db_session)

        with pytest.raises(SearchRequestNotFoundError):
            await service.create_contact_view(
                customer_user.id,
                provider_id=provider.id,
                search_request_id=uuid.uuid4(),
            )

    @pytest.mark.anyio
    async def test_an_omitted_search_request_id_leaves_the_column_null(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "501000016")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000017")
        provider = await create_provider(db_session, user=provider_owner)
        service = make_contact_service(db_session)

        contact_view, _provider = await service.create_contact_view(
            customer_user.id, provider_id=provider.id, search_request_id=None
        )
        await db_session.commit()

        assert contact_view.search_request_id is None


class TestProviderNotFound:
    @pytest.mark.anyio
    async def test_raises_for_a_nonexistent_provider(self, db_session) -> None:
        customer_user = await create_user(db_session, "501000018")
        await create_customer_profile(db_session, customer_user)
        service = make_contact_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.create_contact_view(
                customer_user.id, provider_id=uuid.uuid4(), search_request_id=None
            )

    @pytest.mark.anyio
    async def test_raises_for_a_soft_deleted_provider(self, db_session) -> None:
        customer_user = await create_user(db_session, "501000019")
        await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "501000020")
        provider = await create_provider(
            db_session, user=provider_owner, is_active=False
        )
        service = make_contact_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.create_contact_view(
                customer_user.id, provider_id=provider.id, search_request_id=None
            )


class TestCustomerProfileDefensiveCheck:
    @pytest.mark.anyio
    async def test_raises_if_the_caller_has_no_customer_profile(
        self, db_session
    ) -> None:
        customer_user_without_profile = await create_user(db_session, "501000021")
        provider_owner = await create_user(db_session, "501000022")
        provider = await create_provider(db_session, user=provider_owner)
        service = make_contact_service(db_session)

        with pytest.raises(CustomerProfileNotFoundError):
            await service.create_contact_view(
                customer_user_without_profile.id,
                provider_id=provider.id,
                search_request_id=None,
            )
