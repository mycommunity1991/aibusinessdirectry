"""
End-to-end regression coverage for CLM-001 AC5's literal requirement:
"routes the listing through the same Verification gate a self-registered
Business would go through" (`Plan_S06_CLM-001.md`).

This exercises the REAL, unmodified VER-001 `POST /providers/me/
verification` endpoint immediately after a real claim (OTP request ->
OTP verify), with the import job's own matching `verification_records`
row (Decision 2) present exactly as `scripts/import_google_places.py`
creates it -- neither `test_claim_api.py` nor `test_claim_service.py`
exercise this cross-module interaction, since both mock/omit the
`verification_records` row entirely.

Regression coverage for a real bug found during tester's independent
CLM-001 verification pass: `ClaimService._finalize_claim` resets
`providers.verification_status`/`is_discoverable` (the cached columns)
via `apply_verification_outcome`, but never touched the
`verification.verification_records` table -- so the import-time
synthetic `status=approved` row (Decision 2) remained the provider's
`latest` record, and `VerificationService.submit()`'s resubmission-
eligibility guard (`latest is not None and latest.status !=
VerificationStatus.REJECTED`) treated that stale `approved` row as an
"active" cycle, rejecting the claimant's very first submission attempt
with 409 `VerificationSubmissionNotAllowedError`.

**Fixed** by excluding a system-generated, never-human-reviewed
`APPROVED` record (`status=APPROVED AND reviewed_by IS NULL` -- the
exact, exclusive signature of this synthetic import-time row; every
real admin approval always sets `reviewed_by`) from
`VerificationRecordRepository.get_latest_for_provider`'s query. A
freshly claimed listing now behaves identically to a freshly
self-registered Business (`latest is None` until it actually submits)
for both this eligibility check and `GET /providers/me/verification`'s
status display -- the literal mechanism of AC5's "routes through the
same Verification gate a self-registered Business would go through."
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.core.constants import ROLE_CUSTOMER
from app.core.redis import get_redis_client
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.identity.dependencies import get_sms_sender
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.services.sms_sender import SmsSender
from app.modules.provider.models import (
    BusinessProfile,
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.verification.dependencies import get_verification_file_storage
from app.modules.verification.models import VerificationRecord, VerificationType
from app.shared.storage.local_file_storage import LocalFileStorage

PHONE_COUNTRY_CODE = "+971"


class SpySmsSender(SmsSender):
    """Test double capturing dispatched OTP codes instead of sending SMS."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, phone_country_code: str, phone_number: str, code: str) -> None:
        self.sent.append((phone_country_code, phone_number, code))

    @property
    def last_code(self) -> str:
        return self.sent[-1][2]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sms_spy() -> SpySmsSender:
    return SpySmsSender()


@pytest.fixture
def client(db_session, sms_spy: SpySmsSender, redis_client, tmp_path):
    from tests.conftest import TEST_REDIS_URL

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_sms_sender] = lambda: sms_spy
    app.dependency_overrides[get_redis_client] = lambda: Redis.from_url(
        TEST_REDIS_URL, decode_responses=True
    )
    app.dependency_overrides[get_verification_file_storage] = lambda: LocalFileStorage(
        base_directory=str(tmp_path), public_url_prefix=None
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _headers(user_id: uuid.UUID, roles: list[str]) -> dict[str, str]:
    token = create_access_token(
        subject=str(user_id), roles=roles, jti=str(uuid.uuid4())
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_unclaimed_provider_with_import_time_verification_record(
    db_session,
) -> Provider:
    """
    Mirrors exactly what `scripts/import_google_places.import_places`
    creates for every fresh import (Decision 2): the `providers` row
    AND its matching, system-generated `verification_records` row
    (`status=approved`, `reviewed_by=None`) -- reproduced directly here
    rather than running the whole import script, to isolate this test's
    one concern.
    """
    payload: dict[str, object] = {
        "user_id": None,
        "provider_type": ProviderType.BUSINESS,
        "display_name": "AC5 Gate Test Plumbing LLC",
        "slug": f"ac5-gate-test-{uuid.uuid4().hex[:8]}",
        "phone_country_code": "+971",
        "phone_number": "43339999",
        "listing_source": ListingSource.GOOGLE_SEEDED_UNCLAIMED,
        "is_claimed": False,
        "google_place_id": f"ChIJ_ac5gate_{uuid.uuid4().hex[:10]}",
        "verification_status": VerificationStatus.APPROVED,
        "is_discoverable": True,
        "review_count": 0,
        "country_code": "AE",
    }
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    db_session.add(
        BusinessProfile(
            provider_id=provider.id,
            address_line="Shop 1, AC5 Gate Street, Dubai",
            city="Dubai",
            region="Dubai",
            latitude=25.2,
            longitude=55.27,
        )
    )
    db_session.add(
        VerificationRecord(
            provider_id=provider.id,
            verification_type=VerificationType.BUSINESS_LIGHTWEIGHT,
            status=VerificationStatus.APPROVED,
            submitted_at=datetime.now(UTC),
            reviewed_at=datetime.now(UTC),
            reviewed_by=None,
        )
    )
    await db_session.commit()
    return provider


class TestClaimedListingReachesTheRealVerificationGate:
    """
    AC5's literal wording: a claimed listing must be able to go through
    the *same* Verification gate a self-registered Business would --
    i.e. the claimant must be able to successfully call the real,
    unmodified `POST /providers/me/verification` and have it resolve to
    their newly-claimed provider.
    """

    async def test_claimant_can_submit_verification_after_claiming(
        self, client: TestClient, db_session, sms_spy: SpySmsSender
    ) -> None:
        claimant = await _create_user(db_session, "603000001")
        provider = (
            await _create_unclaimed_provider_with_import_time_verification_record(
                db_session
            )
        )

        otp_response = client.post(
            f"/api/v1/claims/{provider.id}/request-otp",
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )
        assert otp_response.status_code == 200, otp_response.text
        code = sms_spy.last_code

        verify_response = client.post(
            f"/api/v1/claims/{provider.id}/verify-otp",
            json={"code": code},
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )
        assert verify_response.status_code == 200, verify_response.text
        claim_data = verify_response.json()["data"]
        assert claim_data["is_claimed"] is True
        assert claim_data["verification_status"] == "pending"

        # THE AC5 CLAIM UNDER TEST: this must succeed (201), exactly as
        # it would for a brand-new self-registered Business with no
        # prior verification_records row at all.
        submit_response = client.post(
            "/api/v1/providers/me/verification",
            json={},
            headers=_headers(claimant.id, [ROLE_CUSTOMER]),
        )
        assert submit_response.status_code == 201, (
            "AC5 requires a claimed listing to reach the same "
            "Verification gate a self-registered Business would -- "
            f"got {submit_response.status_code}: {submit_response.text}. "
            "Root cause: ClaimService._finalize_claim resets "
            "providers.verification_status/is_discoverable but never "
            "touches the import-time verification_records row (Decision "
            "2), so VerificationService.submit()'s resubmission guard "
            "treats the stale synthetic 'approved' record as still "
            "active and rejects the claimant's first submission."
        )
