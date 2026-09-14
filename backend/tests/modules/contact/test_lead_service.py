"""
Integration tests for `LeadService` (LEAD-001, AC1/AC2/AC4/AC5,
`Plan_S10_LEAD-001.md`) -- this story's correctness-critical core.
Decision 3 (category two-hop resolution, its two distinct honest-null
dead-ends) and Decision 5 (three-state outcome_status mapping) are each
tested separately, per the Plan's own explicit instruction (mirrors
`REV-001` test 15/AC6's "explicit, separately-named test cases"
precedent).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ProviderNotFoundError
from app.modules.category.models import Category
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.contact.models import ContactView
from app.modules.contact.repositories.contact_view_repository import (
    ContactViewRepository,
)
from app.modules.contact.repositories.outcome_tag_repository import (
    OutcomeTagRepository,
)
from app.modules.contact.schemas import LeadOutcomeStatus
from app.modules.contact.services.lead_service import LeadService
from app.modules.search.models import SearchRequest, SearchRequestStatus
from app.modules.search.repositories.search_request_repository import (
    SearchRequestRepository,
)

from ._helpers import (
    create_customer_profile,
    create_provider,
    create_user,
    make_provider_service,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_lead_service(db_session) -> LeadService:
    return LeadService(
        contact_view_repository=ContactViewRepository(db_session),
        outcome_tag_repository=OutcomeTagRepository(db_session),
        search_request_repository=SearchRequestRepository(db_session),
        category_repository=CategoryRepository(db_session),
        provider_service=make_provider_service(db_session),
    )


async def _create_contact_view(
    db_session,
    *,
    customer_id: uuid.UUID,
    provider_id: uuid.UUID,
    search_request_id: uuid.UUID | None = None,
    viewed_at: datetime | None = None,
) -> ContactView:
    contact_view = ContactView(
        customer_id=customer_id,
        provider_id=provider_id,
        search_request_id=search_request_id,
        viewed_at=viewed_at or datetime.now(UTC),
    )
    db_session.add(contact_view)
    await db_session.commit()
    await db_session.refresh(contact_view)
    return contact_view


async def _create_category(db_session, *, name: str = "Plumbing") -> Category:
    category = Category(
        name=name,
        name_ar=None,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
        sort_order=0,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


async def _create_search_request(
    db_session, *, customer_id: uuid.UUID, category_id: uuid.UUID | None
) -> SearchRequest:
    search_request = SearchRequest(
        customer_id=customer_id,
        category_id=category_id,
        status=SearchRequestStatus.MATCHED,
    )
    db_session.add(search_request)
    await db_session.commit()
    await db_session.refresh(search_request)
    return search_request


class TestOwnershipNoProvider:
    """AC4: a caller with no Provider at all has no leads to see."""

    @pytest.mark.anyio
    async def test_raises_provider_not_found_for_a_caller_with_no_provider(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000001")
        await create_customer_profile(db_session, customer_user)
        service = make_lead_service(db_session)

        with pytest.raises(ProviderNotFoundError):
            await service.list_my_leads(customer_user.id, page=1, page_size=20)


class TestOwnershipEmptyLeads:
    @pytest.mark.anyio
    async def test_returns_empty_list_and_zero_total_for_a_provider_with_no_leads(
        self, db_session
    ) -> None:
        provider_owner = await create_user(db_session, "602000002")
        await create_provider(db_session, user=provider_owner)
        service = make_lead_service(db_session)

        items, total_items = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert items == []
        assert total_items == 0


class TestOwnershipCrossProviderBoundary:
    """AC4: the direct, explicit ownership-boundary test -- a page of
    Contact Views belonging to a different provider is never returned."""

    @pytest.mark.anyio
    async def test_provider_a_never_sees_provider_bs_leads(self, db_session) -> None:
        customer_user = await create_user(db_session, "602000003")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_a_owner = await create_user(db_session, "602000004")
        provider_a = await create_provider(db_session, user=provider_a_owner)
        provider_b_owner = await create_user(db_session, "602000005")
        provider_b = await create_provider(db_session, user=provider_b_owner)

        contact_view_a = await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider_a.id
        )
        contact_view_b = await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider_b.id
        )
        service = make_lead_service(db_session)

        items_a, total_a = await service.list_my_leads(
            provider_a_owner.id, page=1, page_size=20
        )
        items_b, total_b = await service.list_my_leads(
            provider_b_owner.id, page=1, page_size=20
        )

        assert total_a == 1
        assert [item.id for item in items_a] == [contact_view_a.id]
        assert total_b == 1
        assert [item.id for item in items_b] == [contact_view_b.id]


class TestOutcomeStatusHired:
    """AC5, Decision 5: `hired=True` maps to `LeadOutcomeStatus.HIRED`."""

    @pytest.mark.anyio
    async def test_a_hired_outcome_tag_maps_to_hired_status(self, db_session) -> None:
        customer_user = await create_user(db_session, "602000006")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000007")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider.id
        )
        await OutcomeTagRepository(db_session).try_create(
            {"contact_view_id": contact_view.id, "hired": True}
        )
        await db_session.commit()
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].outcome_status == LeadOutcomeStatus.HIRED


class TestOutcomeStatusNotHired:
    """AC5, Decision 5: `hired=False` maps to `LeadOutcomeStatus.NOT_HIRED`."""

    @pytest.mark.anyio
    async def test_a_not_hired_outcome_tag_maps_to_not_hired_status(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000008")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000009")
        provider = await create_provider(db_session, user=provider_owner)
        contact_view = await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider.id
        )
        await OutcomeTagRepository(db_session).try_create(
            {"contact_view_id": contact_view.id, "hired": False}
        )
        await db_session.commit()
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].outcome_status == LeadOutcomeStatus.NOT_HIRED


class TestOutcomeStatusNotYetReported:
    """AC5, Decision 5: no `outcome_tags` row at all maps to
    `LeadOutcomeStatus.NOT_YET_REPORTED`."""

    @pytest.mark.anyio
    async def test_no_outcome_tag_row_maps_to_not_yet_reported_status(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000010")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000011")
        provider = await create_provider(db_session, user=provider_owner)
        await _create_contact_view(
            db_session, customer_id=customer_profile.id, provider_id=provider.id
        )
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].outcome_status == LeadOutcomeStatus.NOT_YET_REPORTED


class TestCategoryContextResolvedCase:
    """Decision 3: a `search_request_id` whose `category_id` resolves to
    a real category returns that category's real name."""

    @pytest.mark.anyio
    async def test_returns_the_real_category_name_when_fully_resolvable(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000012")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000013")
        provider = await create_provider(db_session, user=provider_owner)
        category = await _create_category(db_session, name="Electrical")
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id, category_id=category.id
        )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=search_request.id,
        )
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].category_name == "Electrical"


class TestCategoryContextNoSearchRequest:
    """Decision 3's first dead-end: no `search_request_id` at all (the
    structured Search Results path) -- `category_name` is `None`."""

    @pytest.mark.anyio
    async def test_returns_none_when_there_is_no_search_request_id(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000014")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000015")
        provider = await create_provider(db_session, user=provider_owner)
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=None,
        )
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].category_name is None


class TestCategoryContextSearchRequestWithNullCategory:
    """Decision 3's second, distinct dead-end: a `search_request_id` is
    present but its own `category_id` is `NULL` (e.g. a
    `routed_to_admin` session that never resolved a category) --
    `category_name` is still `None`, tested separately from the "no
    `search_request_id` at all" case."""

    @pytest.mark.anyio
    async def test_returns_none_when_the_search_requests_category_id_is_null(
        self, db_session
    ) -> None:
        customer_user = await create_user(db_session, "602000016")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000017")
        provider = await create_provider(db_session, user=provider_owner)
        search_request = await _create_search_request(
            db_session, customer_id=customer_profile.id, category_id=None
        )
        await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            search_request_id=search_request.id,
        )
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert len(items) == 1
        assert items[0].category_name is None


class TestOrdering:
    """AC2: most-recent-first across a multi-row fixture."""

    @pytest.mark.anyio
    async def test_returns_leads_most_recent_first(self, db_session) -> None:
        customer_user = await create_user(db_session, "602000018")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000019")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        oldest = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=2),
        )
        middle = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now - timedelta(days=1),
        )
        newest = await _create_contact_view(
            db_session,
            customer_id=customer_profile.id,
            provider_id=provider.id,
            viewed_at=now,
        )
        service = make_lead_service(db_session)

        items, _total = await service.list_my_leads(
            provider_owner.id, page=1, page_size=20
        )

        assert [item.id for item in items] == [newest.id, middle.id, oldest.id]


class TestPagination:
    """`total_items`/page-slicing correctness across a fixture with more
    rows than one page size."""

    @pytest.mark.anyio
    async def test_total_items_and_page_slicing_are_correct(self, db_session) -> None:
        customer_user = await create_user(db_session, "602000020")
        customer_profile = await create_customer_profile(db_session, customer_user)
        provider_owner = await create_user(db_session, "602000021")
        provider = await create_provider(db_session, user=provider_owner)
        now = datetime.now(UTC)

        created = []
        for offset_days in range(5):
            created.append(
                await _create_contact_view(
                    db_session,
                    customer_id=customer_profile.id,
                    provider_id=provider.id,
                    viewed_at=now - timedelta(days=offset_days),
                )
            )
        service = make_lead_service(db_session)

        page_one, total_page_one = await service.list_my_leads(
            provider_owner.id, page=1, page_size=2
        )
        page_two, total_page_two = await service.list_my_leads(
            provider_owner.id, page=2, page_size=2
        )
        page_three, total_page_three = await service.list_my_leads(
            provider_owner.id, page=3, page_size=2
        )

        assert total_page_one == total_page_two == total_page_three == 5
        assert [item.id for item in page_one] == [created[0].id, created[1].id]
        assert [item.id for item in page_two] == [created[2].id, created[3].id]
        assert [item.id for item in page_three] == [created[4].id]
