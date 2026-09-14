"""
Real-database integration test for `ProviderRepository.
get_by_id_for_update` (REV-002, Backend Proposed Changes item 8,
`Plan_S09_REV-002.md`) -- confirms the raw `SELECT ... FOR UPDATE`
returns the correct row for an existing provider, and `None` for a
nonexistent one. The genuine race-safety proof of the lock this method
acquires lives in `tests/modules/review/test_review_service.py`'s
`TestRecalculationCorrectness.
test_two_concurrent_reviews_for_the_same_provider_both_count` (a plain
single-session round trip cannot itself demonstrate blocking behavior).
"""

import uuid

import pytest

from app.modules.provider.repositories.provider_repository import ProviderRepository


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _create_provider(db_session):
    from app.modules.provider.models import (
        ListingSource,
        Provider,
        ProviderType,
        VerificationStatus,
    )

    provider = Provider(
        user_id=None,
        provider_type=ProviderType.BUSINESS,
        display_name="Test Provider For Locking",
        slug=f"test-provider-locking-{uuid.uuid4().hex[:8]}",
        listing_source=ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        is_claimed=False,
        verification_status=VerificationStatus.APPROVED,
        is_discoverable=True,
        review_count=0,
        country_code="AE",
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


class TestGetByIdForUpdate:
    @pytest.mark.anyio
    async def test_returns_the_correct_row(self, db_session) -> None:
        provider = await _create_provider(db_session)
        repository = ProviderRepository(db_session)

        result = await repository.get_by_id_for_update(provider.id)

        assert result is not None
        assert result.id == provider.id
        assert result.display_name == "Test Provider For Locking"

    @pytest.mark.anyio
    async def test_returns_none_for_a_nonexistent_id(self, db_session) -> None:
        repository = ProviderRepository(db_session)

        result = await repository.get_by_id_for_update(uuid.uuid4())

        assert result is None
