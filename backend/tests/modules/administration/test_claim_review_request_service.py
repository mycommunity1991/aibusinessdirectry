"""
Integration tests for `ClaimReviewRequestService`/
`ClaimReviewRequestRepository` (CLM-001, Decision 9,
`Plan_S06_CLM-001.md`), exercised against a real Postgres database (see
`tests/conftest.py`'s `db_session` fixture) -- mirrors
`test_admin_action_log_service.py`'s pattern.
"""

import uuid

from app.modules.administration.repositories.claim_review_request_repository import (
    ClaimReviewRequestRepository,
)
from app.modules.administration.services.claim_review_request_service import (
    ClaimReviewRequestService,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.provider.models import ListingSource, Provider, VerificationStatus


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_unclaimed_provider(db_session, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": None,
        "provider_type": "business",
        "display_name": "Acme Cafe",
        "slug": f"acme-cafe-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "google_place_id": f"ChIJ_{uuid.uuid4().hex[:10]}",
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


def _service(db_session) -> ClaimReviewRequestService:
    return ClaimReviewRequestService(ClaimReviewRequestRepository(db_session))


class TestCreate:
    async def test_create_persists_an_open_request(self, db_session) -> None:
        claimant = await _make_user(db_session, "900000001")
        provider = await _make_unclaimed_provider(db_session)
        service = _service(db_session)

        request = await service.create(
            provider_id=provider.id,
            claimant_user_id=claimant.id,
            reason="otp_failed",
        )
        await db_session.commit()

        assert request.id is not None
        assert request.status == "open"
        assert request.reason == "otp_failed"
        assert request.provider_id == provider.id
        assert request.claimant_user_id == claimant.id
        assert request.reviewed_by is None
        assert request.reviewed_at is None


class TestListOpen:
    async def test_only_open_requests_are_listed(self, db_session) -> None:
        claimant = await _make_user(db_session, "900000002")
        admin = await _make_user(db_session, "900000003")
        provider_a = await _make_unclaimed_provider(db_session)
        provider_b = await _make_unclaimed_provider(db_session)
        service = _service(db_session)

        open_request = await service.create(
            provider_id=provider_a.id,
            claimant_user_id=claimant.id,
            reason="otp_failed",
        )
        resolved_request = await service.create(
            provider_id=provider_b.id,
            claimant_user_id=claimant.id,
            reason="no_public_number",
        )
        await service.resolve(
            resolved_request.id,
            admin_user_id=admin.id,
            resolution="rejected",
            resolution_notes="Not this one.",
        )
        await db_session.commit()

        requests, total = await service.list_open(page=1, page_size=10)

        assert total == 1
        assert [r.id for r in requests] == [open_request.id]

    async def test_oldest_first_ordering(self, db_session) -> None:
        claimant = await _make_user(db_session, "900000004")
        provider_a = await _make_unclaimed_provider(db_session)
        provider_b = await _make_unclaimed_provider(db_session)
        service = _service(db_session)

        first = await service.create(
            provider_id=provider_a.id, claimant_user_id=claimant.id, reason="otp_failed"
        )
        second = await service.create(
            provider_id=provider_b.id,
            claimant_user_id=claimant.id,
            reason="no_public_number",
        )
        await db_session.commit()

        requests, total = await service.list_open(page=1, page_size=10)

        assert total == 2
        assert [r.id for r in requests] == [first.id, second.id]


class TestResolve:
    async def test_resolve_sets_resolution_reviewer_and_timestamp(
        self, db_session
    ) -> None:
        claimant = await _make_user(db_session, "900000005")
        admin = await _make_user(db_session, "900000006")
        provider = await _make_unclaimed_provider(db_session)
        service = _service(db_session)
        request = await service.create(
            provider_id=provider.id, claimant_user_id=claimant.id, reason="otp_failed"
        )

        resolved = await service.resolve(
            request.id,
            admin_user_id=admin.id,
            resolution="approved",
            resolution_notes="Looks right.",
        )
        await db_session.commit()

        assert resolved.status == "resolved"
        assert resolved.resolution == "approved"
        assert resolved.resolution_notes == "Looks right."
        assert resolved.reviewed_by == admin.id
        assert resolved.reviewed_at is not None

    async def test_get_by_id_returns_none_for_a_nonexistent_id(
        self, db_session
    ) -> None:
        service = _service(db_session)

        result = await service.get_by_id(uuid.uuid4())

        assert result is None
