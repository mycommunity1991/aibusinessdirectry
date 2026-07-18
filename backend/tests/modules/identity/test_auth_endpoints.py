"""
End-to-end integration tests for `POST /auth/request-otp` and
`POST /auth/verify-otp`, exercised against the real FastAPI app with a
real Postgres session (AC11: covers new-number registration,
existing-number login, expired code rejection, attempt-cap lockout, and
reused-code rejection).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.constants import OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS, ROLE_CUSTOMER
from app.core.redis import get_redis_client
from app.core.security import hash_otp_code
from app.database.session import get_db
from app.main import app
from app.modules.identity.dependencies import get_sms_sender
from app.modules.identity.models import AuthProvider, OtpPurpose, OtpVerification, User
from app.modules.identity.services.seed_data import seed_roles
from app.modules.identity.services.sms_sender import SmsSender

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
def client(db_session, sms_spy: SpySmsSender, redis_client):
    from redis.asyncio import Redis

    from tests.conftest import TEST_REDIS_URL

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_sms_sender] = lambda: sms_spy
    app.dependency_overrides[get_redis_client] = lambda: Redis.from_url(
        TEST_REDIS_URL, decode_responses=True
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


async def _request_otp(
    client: TestClient, sms_spy: SpySmsSender, phone_number: str
) -> str:
    response = client.post(
        "/api/v1/auth/request-otp",
        json={
            "phone_country_code": PHONE_COUNTRY_CODE,
            "phone_number": phone_number,
        },
    )
    assert response.status_code == 200
    return sms_spy.last_code


class TestRequestOtp:
    @pytest.mark.anyio
    async def test_request_otp_returns_generic_ack(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        response = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "501000001",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "verification code has been sent" in body["message"]
        assert len(sms_spy.sent) == 1
        # FU-2: the client can size its resend countdown from the actual
        # server-configured expiry instead of a hardcoded duplicate.
        assert body["data"]["expires_in_seconds"] == OTP_EXPIRY_MINUTES * 60

    @pytest.mark.anyio
    async def test_request_otp_ack_is_identical_for_registered_and_unregistered_numbers(
        self, client: TestClient, db_session
    ) -> None:
        """No enumeration signal: the same acknowledgement is returned
        whether or not the number is already registered."""
        db_session.add(
            User(
                phone_country_code=PHONE_COUNTRY_CODE,
                phone_number="501000002",
                auth_provider=AuthProvider.MOBILE_OTP,
            )
        )
        await db_session.commit()

        registered_resp = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "501000002",
            },
        )
        unregistered_resp = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "501000003",
            },
        )

        assert registered_resp.status_code == unregistered_resp.status_code == 200
        assert registered_resp.json()["message"] == unregistered_resp.json()["message"]
        # The expires_in_seconds value is a fixed, server-configured
        # constant — identical regardless of registration status, so it
        # carries no enumeration signal either.
        assert registered_resp.json()["data"] == unregistered_resp.json()["data"]


class TestVerifyOtpRegistrationAndLogin:
    @pytest.mark.anyio
    async def test_new_number_registers_user_with_customer_role(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC6: a verified OTP for an unrecognized phone number creates a
        new User with auth_provider=mobile_otp and assigns the customer
        role via user_roles."""
        await seed_roles(db_session)
        await db_session.commit()

        code = await _request_otp(client, sms_spy, "502000001")

        response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000001",
                "code": code,
            },
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["access_token"]
        assert body["token_type"] == "bearer"
        assert body["user"]["phone_number"] == "502000001"
        assert body["user"]["roles"] == [ROLE_CUSTOMER]

        result = await db_session.execute(
            select(User).where(User.phone_number == "502000001")
        )
        users = result.scalars().all()
        assert len(users) == 1
        assert users[0].auth_provider == "mobile_otp"

    @pytest.mark.anyio
    async def test_existing_number_authenticates_without_duplicate(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC7: a verified OTP for an existing phone number authenticates
        that User without creating a duplicate."""
        await seed_roles(db_session)
        await db_session.commit()

        first_code = await _request_otp(client, sms_spy, "502000002")
        first_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000002",
                "code": first_code,
            },
        )
        assert first_response.status_code == 200
        first_user_id = first_response.json()["data"]["user"]["id"]

        second_code = await _request_otp(client, sms_spy, "502000002")
        second_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000002",
                "code": second_code,
            },
        )
        assert second_response.status_code == 200
        second_user_id = second_response.json()["data"]["user"]["id"]

        assert first_user_id == second_user_id

        result = await db_session.execute(
            select(User).where(User.phone_number == "502000002")
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.anyio
    async def test_no_customer_profile_row_is_created(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC12: registering via mobile OTP must not create a
        customer_profiles/customer_preferences row. Those tables belong to
        the Customer domain (CUS-001) and are not created by this
        (identity-only) migration at all."""
        await seed_roles(db_session)
        await db_session.commit()

        code = await _request_otp(client, sms_spy, "502000003")
        response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000003",
                "code": code,
            },
        )
        assert response.status_code == 200

        # `customer.customer_profiles` doesn't exist at all — this
        # migration only creates the `identity` schema. `to_regclass`
        # returns NULL for a relation that doesn't exist.
        schema_check = await db_session.execute(
            text("SELECT to_regclass('customer.customer_profiles') AS reg")
        )
        assert schema_check.scalar() is None


class TestVerifyOtpFailureCases:
    @pytest.mark.anyio
    async def test_wrong_code_returns_generic_error_without_revealing_registration(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        """AC5/AC10: an incorrect code is rejected without revealing
        whether the phone number is registered."""
        await _request_otp(client, sms_spy, "502000004")

        response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000004",
                "code": "000000",
            },
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert "didn't work" in body["message"]
        assert "not found" not in body["message"].lower()
        assert "not registered" not in body["message"].lower()

    @pytest.mark.anyio
    async def test_verify_otp_for_never_requested_number_returns_same_generic_error(
        self, client: TestClient
    ) -> None:
        """No OTP was ever requested for this number — the response must
        be indistinguishable from a wrong-code response."""
        response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000099",
                "code": "123456",
            },
        )
        assert response.status_code == 400
        assert "didn't work" in response.json()["message"]

    @pytest.mark.anyio
    async def test_expired_code_is_rejected(
        self, client: TestClient, db_session
    ) -> None:
        """AC11: expired code rejection."""
        db_session.add(
            OtpVerification(
                phone_country_code=PHONE_COUNTRY_CODE,
                phone_number="502000005",
                purpose=OtpPurpose.LOGIN,
                code_hash=hash_otp_code("123456"),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        await db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000005",
                "code": "123456",
            },
        )
        assert response.status_code == 400
        assert "didn't work" in response.json()["message"]

    @pytest.mark.anyio
    async def test_attempt_cap_lockout_after_five_wrong_attempts(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        """AC5/AC11: the attempt counter is capped at 5 attempts before
        lockout."""
        code = await _request_otp(client, sms_spy, "502000006")

        for _ in range(OTP_MAX_ATTEMPTS - 1):
            response = client.post(
                "/api/v1/auth/verify-otp",
                json={
                    "phone_country_code": PHONE_COUNTRY_CODE,
                    "phone_number": "502000006",
                    "code": "000000",
                },
            )
            assert response.status_code == 400

        locked_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000006",
                "code": "000000",
            },
        )
        assert locked_response.status_code == 429

        # Even the correct code is now rejected — this OTP is dead.
        still_locked_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000006",
                "code": code,
            },
        )
        assert still_locked_response.status_code == 429

    @pytest.mark.anyio
    async def test_reused_code_is_rejected(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC8: a used OTP code cannot be verified a second time."""
        await seed_roles(db_session)
        await db_session.commit()

        code = await _request_otp(client, sms_spy, "502000007")

        first_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000007",
                "code": code,
            },
        )
        assert first_response.status_code == 200

        second_response = client.post(
            "/api/v1/auth/verify-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "502000007",
                "code": code,
            },
        )
        assert second_response.status_code == 400
        assert "didn't work" in second_response.json()["message"]
