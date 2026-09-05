"""
End-to-end integration tests for `POST /auth/request-otp`,
`POST /auth/verify-otp` (AC11: covers new-number registration,
existing-number login, expired code rejection, attempt-cap lockout, and
reused-code rejection), `POST /auth/google`/`POST /auth/apple`
(AUTH-002: AC3/AC4/AC5/AC6/AC9), and AUTH-003's `POST /auth/refresh`,
`GET /auth/sessions`, `DELETE /auth/sessions/{id}`,
`POST /auth/sessions/logout-all` (AC1-AC11).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import settings
from app.core.constants import (
    AUTH_RATE_LIMIT_PER_MINUTE,
    OTP_EXPIRY_MINUTES,
    OTP_MAX_ATTEMPTS,
    ROLE_CUSTOMER,
)
from app.core.redis import get_redis_client
from app.core.security import hash_otp_code
from app.database.session import get_db
from app.main import app
from app.modules.identity.dependencies import (
    APPLE_ISSUERS,
    APPLE_JWKS_URL,
    GOOGLE_ISSUERS,
    GOOGLE_JWKS_URL,
    get_apple_id_token_verifier,
    get_google_id_token_verifier,
    get_sms_sender,
)
from app.modules.identity.models import AuthProvider, OtpPurpose, OtpVerification, User
from app.modules.identity.services.id_token_verifier import JwksIdTokenVerifier
from app.modules.identity.services.seed_data import seed_roles
from app.modules.identity.services.sms_sender import SmsSender
from tests.support.id_token_factory import IdTokenFactory, JwksTestServer

PHONE_COUNTRY_CODE = "+971"
GOOGLE_ISSUER = "https://accounts.google.com"
APPLE_ISSUER = "https://appleid.apple.com"

# AUTH-003, AC6: every login-shaped request now requires a `device`
# field. A single default payload is reused by every test below that
# doesn't specifically exercise device-capture behavior.
DEFAULT_DEVICE = {"device_platform": "ios", "device_name": "Test Device"}


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
def google_id_token_factory() -> IdTokenFactory:
    return IdTokenFactory(kid="google-test-kid")


@pytest.fixture
def apple_id_token_factory() -> IdTokenFactory:
    return IdTokenFactory(kid="apple-test-kid")


@pytest.fixture
def google_jwks_server(google_id_token_factory: IdTokenFactory) -> JwksTestServer:
    return JwksTestServer(GOOGLE_JWKS_URL, [google_id_token_factory])


@pytest.fixture
def apple_jwks_server(apple_id_token_factory: IdTokenFactory) -> JwksTestServer:
    return JwksTestServer(APPLE_JWKS_URL, [apple_id_token_factory])


def _sign_google_token(factory: IdTokenFactory, **kwargs) -> str:
    return factory.sign(
        issuer=GOOGLE_ISSUER, audience=settings.GOOGLE_OAUTH_CLIENT_ID, **kwargs
    )


def _sign_apple_token(factory: IdTokenFactory, **kwargs) -> str:
    return factory.sign(
        issuer=APPLE_ISSUER,
        audience=settings.APPLE_OAUTH_CLIENT_IDS[0],
        **kwargs,
    )


@pytest.fixture
def client(
    db_session,
    sms_spy: SpySmsSender,
    redis_client,
    google_jwks_server: JwksTestServer,
    apple_jwks_server: JwksTestServer,
):
    from redis.asyncio import Redis

    from tests.conftest import TEST_REDIS_URL

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_sms_sender] = lambda: sms_spy
    app.dependency_overrides[get_redis_client] = lambda: Redis.from_url(
        TEST_REDIS_URL, decode_responses=True
    )
    # AUTH-002/AC8: the real `JwksIdTokenVerifier` code path is exercised
    # against a fake, in-memory JWKS transport -- no test ever calls the
    # real Google/Apple endpoints.
    app.dependency_overrides[get_google_id_token_verifier] = lambda: (
        JwksIdTokenVerifier(
            http_client=google_jwks_server.http_client(),
            jwks_url=GOOGLE_JWKS_URL,
            issuers=GOOGLE_ISSUERS,
            audiences=frozenset({settings.GOOGLE_OAUTH_CLIENT_ID}),
        )
    )
    app.dependency_overrides[get_apple_id_token_verifier] = lambda: JwksIdTokenVerifier(
        http_client=apple_jwks_server.http_client(),
        jwks_url=APPLE_JWKS_URL,
        issuers=APPLE_ISSUERS,
        audiences=frozenset(settings.APPLE_OAUTH_CLIENT_IDS),
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


def _verify_otp_json(phone_number: str, code: str, device: dict | None = None) -> dict:
    return {
        "phone_country_code": PHONE_COUNTRY_CODE,
        "phone_number": phone_number,
        "code": code,
        "device": device if device is not None else DEFAULT_DEVICE,
    }


def _verify_otp(
    client: TestClient, phone_number: str, code: str, device: dict | None = None
):
    return client.post(
        "/api/v1/auth/verify-otp", json=_verify_otp_json(phone_number, code, device)
    )


def _oauth_json(id_token: str, device: dict | None = None) -> dict:
    return {
        "id_token": id_token,
        "device": device if device is not None else DEFAULT_DEVICE,
    }


async def _login_and_get_tokens(
    client: TestClient,
    sms_spy: SpySmsSender,
    phone_number: str,
    device: dict | None = None,
) -> dict:
    """Runs the full OTP flow and returns the `data` payload of a
    successful `verify-otp` response (access_token/refresh_token/user)."""
    code = await _request_otp(client, sms_spy, phone_number)
    response = _verify_otp(client, phone_number, code, device)
    assert response.status_code == 200
    return response.json()["data"]


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

        response = _verify_otp(client, "502000001", code)

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["access_token"]
        assert body["refresh_token"]
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
        first_response = _verify_otp(client, "502000002", first_code)
        assert first_response.status_code == 200
        first_user_id = first_response.json()["data"]["user"]["id"]

        second_code = await _request_otp(client, sms_spy, "502000002")
        second_response = _verify_otp(client, "502000002", second_code)
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
        response = _verify_otp(client, "502000003", code)
        assert response.status_code == 200

        # `customer.customer_profiles` doesn't exist at all — this
        # migration only creates the `identity` schema. `to_regclass`
        # returns NULL for a relation that doesn't exist.
        schema_check = await db_session.execute(
            text("SELECT to_regclass('customer.customer_profiles') AS reg")
        )
        assert schema_check.scalar() is None

    @pytest.mark.anyio
    async def test_repeat_login_from_the_same_device_updates_not_duplicates_device(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AUTH-003, AC6: a device row is created on first login and
        updated (not duplicated) on a repeat login with the same device
        info."""
        await seed_roles(db_session)
        await db_session.commit()

        device = {"device_platform": "android", "device_name": "Pixel 8"}

        first_code = await _request_otp(client, sms_spy, "502000020")
        first_response = _verify_otp(client, "502000020", first_code, device)
        assert first_response.status_code == 200

        second_code = await _request_otp(client, sms_spy, "502000020")
        second_response = _verify_otp(client, "502000020", second_code, device)
        assert second_response.status_code == 200

        result = await db_session.execute(
            text(
                "SELECT count(*) FROM identity.devices d "
                "JOIN identity.users u ON u.id = d.user_id "
                "WHERE u.phone_number = :phone"
            ),
            {"phone": "502000020"},
        )
        assert result.scalar() == 1


class TestVerifyOtpFailureCases:
    @pytest.mark.anyio
    async def test_wrong_code_returns_generic_error_without_revealing_registration(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        """AC5/AC10: an incorrect code is rejected without revealing
        whether the phone number is registered."""
        await _request_otp(client, sms_spy, "502000004")

        response = _verify_otp(client, "502000004", "000000")
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
        response = _verify_otp(client, "502000099", "123456")
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

        response = _verify_otp(client, "502000005", "123456")
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
            response = _verify_otp(client, "502000006", "000000")
            assert response.status_code == 400

        locked_response = _verify_otp(client, "502000006", "000000")
        assert locked_response.status_code == 429

        # Even the correct code is now rejected — this OTP is dead.
        still_locked_response = _verify_otp(client, "502000006", code)
        assert still_locked_response.status_code == 429

    @pytest.mark.anyio
    async def test_reused_code_is_rejected(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC8: a used OTP code cannot be verified a second time."""
        await seed_roles(db_session)
        await db_session.commit()

        code = await _request_otp(client, sms_spy, "502000007")

        first_response = _verify_otp(client, "502000007", code)
        assert first_response.status_code == 200

        second_response = _verify_otp(client, "502000007", code)
        assert second_response.status_code == 400
        assert "didn't work" in second_response.json()["message"]


class TestRateLimiting:
    """
    FU-5 follow-up (`Walkthrough_S02_AUTH-001.md`): the Redis-backed
    fixed-window rate limiter wired onto both auth endpoints via
    `dependencies=[Depends(...)]`. Confirms the actual endpoint wiring —
    not just `RateLimitDependency` in isolation, which is covered
    separately in `tests/core/test_rate_limit.py` — enforces the
    configured `AUTH_RATE_LIMIT_PER_MINUTE` limit and returns a generic
    429 once exceeded.
    """

    @pytest.mark.anyio
    async def test_request_otp_allows_requests_up_to_the_configured_limit(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        """`request-otp` is phone-keyed (`05_API_GUIDELINES.md`:
        10/minute). The Nth request for a given number must still
        succeed — only the (N+1)th is rejected."""
        for _ in range(AUTH_RATE_LIMIT_PER_MINUTE):
            response = client.post(
                "/api/v1/auth/request-otp",
                json={
                    "phone_country_code": PHONE_COUNTRY_CODE,
                    "phone_number": "503000001",
                },
            )
            assert response.status_code == 200
        assert len(sms_spy.sent) == AUTH_RATE_LIMIT_PER_MINUTE

    @pytest.mark.anyio
    async def test_request_otp_rejects_the_request_exceeding_the_limit(
        self, client: TestClient, sms_spy: SpySmsSender
    ) -> None:
        for _ in range(AUTH_RATE_LIMIT_PER_MINUTE):
            response = client.post(
                "/api/v1/auth/request-otp",
                json={
                    "phone_country_code": PHONE_COUNTRY_CODE,
                    "phone_number": "503000002",
                },
            )
            assert response.status_code == 200

        limited_response = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "503000002",
            },
        )
        assert limited_response.status_code == 429
        body = limited_response.json()
        assert body["success"] is False
        # 06_SECURITY.md: a plain-language message, no internal codes or
        # stack traces.
        assert (
            body["message"] == "Too many requests. Please wait a moment and try again."
        )
        # The rate limiter runs before the endpoint's own logic, so no
        # further SMS is dispatched once the limit is hit.
        assert len(sms_spy.sent) == AUTH_RATE_LIMIT_PER_MINUTE

    @pytest.mark.anyio
    async def test_request_otp_limit_is_scoped_per_phone_number(
        self, client: TestClient
    ) -> None:
        """A different phone number is unaffected by another number's
        exhausted limit -- confirms `key_by="phone"` scoping."""
        for _ in range(AUTH_RATE_LIMIT_PER_MINUTE):
            response = client.post(
                "/api/v1/auth/request-otp",
                json={
                    "phone_country_code": PHONE_COUNTRY_CODE,
                    "phone_number": "503000003",
                },
            )
            assert response.status_code == 200

        exhausted_number_response = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "503000003",
            },
        )
        assert exhausted_number_response.status_code == 429

        other_number_response = client.post(
            "/api/v1/auth/request-otp",
            json={
                "phone_country_code": PHONE_COUNTRY_CODE,
                "phone_number": "503000004",
            },
        )
        assert other_number_response.status_code == 200

    @pytest.mark.anyio
    async def test_verify_otp_rejects_the_request_exceeding_the_limit(
        self, client: TestClient
    ) -> None:
        """`verify-otp` is IP-keyed -- defense in depth against a single
        client hammering the endpoint across many different phone
        numbers, which a phone-keyed limit would not catch. A distinct,
        never-requested phone number is used per call below so the
        separate per-OTP attempt-cap lockout (`OtpLockedError`, also a
        429 but with a different message) never fires first and this
        test cleanly isolates the rate limiter itself."""
        for i in range(AUTH_RATE_LIMIT_PER_MINUTE):
            response = _verify_otp(client, f"50399{i:04d}", "000000")
            assert response.status_code == 400
            assert "didn't work" in response.json()["message"]

        limited_response = _verify_otp(client, "503999999", "000000")
        assert limited_response.status_code == 429
        assert (
            limited_response.json()["message"]
            == "Too many requests. Please wait a moment and try again."
        )


class TestGoogleSignIn:
    """AUTH-002: `POST /auth/google` (AC2, AC3, AC4, AC6)."""

    @pytest.mark.anyio
    async def test_new_subject_creates_user_with_customer_role(
        self,
        client: TestClient,
        db_session,
        google_id_token_factory: IdTokenFactory,
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        token = _sign_google_token(
            google_id_token_factory, subject="google-sub-001", email="new@example.com"
        )
        response = client.post("/api/v1/auth/google", json=_oauth_json(token))

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["user"]["roles"] == [ROLE_CUSTOMER]

        result = await db_session.execute(
            select(User).where(User.external_auth_subject == "google-sub-001")
        )
        users = result.scalars().all()
        assert len(users) == 1
        assert users[0].auth_provider == "google"
        assert users[0].email == "new@example.com"

    @pytest.mark.anyio
    async def test_existing_subject_authenticates_without_duplicate(
        self,
        client: TestClient,
        db_session,
        google_id_token_factory: IdTokenFactory,
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        token = _sign_google_token(google_id_token_factory, subject="google-sub-002")
        first_response = client.post("/api/v1/auth/google", json=_oauth_json(token))
        assert first_response.status_code == 200
        first_user_id = first_response.json()["data"]["user"]["id"]

        second_token = _sign_google_token(
            google_id_token_factory, subject="google-sub-002"
        )
        second_response = client.post(
            "/api/v1/auth/google", json=_oauth_json(second_token)
        )
        assert second_response.status_code == 200
        second_user_id = second_response.json()["data"]["user"]["id"]

        assert first_user_id == second_user_id
        result = await db_session.execute(
            select(User).where(User.external_auth_subject == "google-sub-002")
        )
        assert len(result.scalars().all()) == 1

    @pytest.mark.anyio
    async def test_tampered_token_returns_generic_401(
        self, client: TestClient, google_id_token_factory: IdTokenFactory
    ) -> None:
        """AC6: no validation detail is leaked in the response."""
        token = _sign_google_token(google_id_token_factory)
        tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

        response = client.post("/api/v1/auth/google", json=_oauth_json(tampered))

        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "We couldn't verify your sign-in. Please try again."
        assert "signature" not in body["message"].lower()

    @pytest.mark.anyio
    async def test_expired_token_returns_generic_401(
        self, client: TestClient, google_id_token_factory: IdTokenFactory
    ) -> None:
        token = _sign_google_token(
            google_id_token_factory, expires_delta=timedelta(minutes=-5)
        )

        response = client.post("/api/v1/auth/google", json=_oauth_json(token))

        assert response.status_code == 401
        assert (
            response.json()["message"]
            == "We couldn't verify your sign-in. Please try again."
        )

    @pytest.mark.anyio
    async def test_wrong_audience_token_returns_generic_401(
        self, client: TestClient, google_id_token_factory: IdTokenFactory
    ) -> None:
        token = google_id_token_factory.sign(
            issuer=GOOGLE_ISSUER, audience="some-other-app"
        )

        response = client.post("/api/v1/auth/google", json=_oauth_json(token))

        assert response.status_code == 401
        assert (
            response.json()["message"]
            == "We couldn't verify your sign-in. Please try again."
        )


class TestAppleSignIn:
    """AUTH-002: `POST /auth/apple` (AC2, AC3, AC4, AC6)."""

    @pytest.mark.anyio
    async def test_new_subject_creates_user_with_customer_role(
        self,
        client: TestClient,
        db_session,
        apple_id_token_factory: IdTokenFactory,
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        token = _sign_apple_token(
            apple_id_token_factory,
            subject="apple-sub-001",
            email="applenew@example.com",
            email_verified="true",
        )
        response = client.post("/api/v1/auth/apple", json=_oauth_json(token))

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["user"]["roles"] == [ROLE_CUSTOMER]

        result = await db_session.execute(
            select(User).where(User.external_auth_subject == "apple-sub-001")
        )
        users = result.scalars().all()
        assert len(users) == 1
        assert users[0].auth_provider == "apple"
        assert users[0].email == "applenew@example.com"

    @pytest.mark.anyio
    async def test_existing_subject_authenticates_without_duplicate(
        self,
        client: TestClient,
        db_session,
        apple_id_token_factory: IdTokenFactory,
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        token = _sign_apple_token(apple_id_token_factory, subject="apple-sub-002")
        first_response = client.post("/api/v1/auth/apple", json=_oauth_json(token))
        assert first_response.status_code == 200
        first_user_id = first_response.json()["data"]["user"]["id"]

        second_token = _sign_apple_token(
            apple_id_token_factory, subject="apple-sub-002"
        )
        second_response = client.post(
            "/api/v1/auth/apple", json=_oauth_json(second_token)
        )
        assert second_response.status_code == 200
        second_user_id = second_response.json()["data"]["user"]["id"]

        assert first_user_id == second_user_id

    @pytest.mark.anyio
    async def test_email_omitted_on_relogin_does_not_overwrite_existing_email(
        self,
        client: TestClient,
        db_session,
        apple_id_token_factory: IdTokenFactory,
    ) -> None:
        """Apple only guarantees email on the first authorization."""
        await seed_roles(db_session)
        await db_session.commit()

        first_token = _sign_apple_token(
            apple_id_token_factory,
            subject="apple-sub-003",
            email="original@example.com",
        )
        first_response = client.post(
            "/api/v1/auth/apple", json=_oauth_json(first_token)
        )
        assert first_response.status_code == 200

        second_token = _sign_apple_token(
            apple_id_token_factory, subject="apple-sub-003", email=None
        )
        second_response = client.post(
            "/api/v1/auth/apple", json=_oauth_json(second_token)
        )
        assert second_response.status_code == 200

        result = await db_session.execute(
            select(User).where(User.external_auth_subject == "apple-sub-003")
        )
        user = result.scalar_one()
        assert user.email == "original@example.com"

    @pytest.mark.anyio
    async def test_tampered_token_returns_generic_401(
        self, client: TestClient, apple_id_token_factory: IdTokenFactory
    ) -> None:
        token = _sign_apple_token(apple_id_token_factory)
        tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

        response = client.post("/api/v1/auth/apple", json=_oauth_json(tampered))

        assert response.status_code == 401
        assert (
            response.json()["message"]
            == "We couldn't verify your sign-in. Please try again."
        )


class TestOauthCrossProviderSameEmail:
    """
    AC9: an explicit integration-level check that a different provider
    presenting the same email as an existing account creates a second,
    independent `identity.users` row -- never a merge/link (AC5).
    """

    @pytest.mark.anyio
    async def test_same_email_different_provider_creates_two_distinct_users(
        self,
        client: TestClient,
        db_session,
        google_id_token_factory: IdTokenFactory,
        apple_id_token_factory: IdTokenFactory,
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        shared_email = "shared-across-providers@example.com"

        google_token = _sign_google_token(
            google_id_token_factory,
            subject="google-shared-sub",
            email=shared_email,
        )
        google_response = client.post(
            "/api/v1/auth/google", json=_oauth_json(google_token)
        )
        assert google_response.status_code == 200
        google_user_id = google_response.json()["data"]["user"]["id"]

        apple_token = _sign_apple_token(
            apple_id_token_factory,
            subject="apple-shared-sub",
            email=shared_email,
        )
        apple_response = client.post(
            "/api/v1/auth/apple", json=_oauth_json(apple_token)
        )
        assert apple_response.status_code == 200
        apple_user_id = apple_response.json()["data"]["user"]["id"]

        assert google_user_id != apple_user_id

        # Explicit direct-SQL check (AC9), independent of the API
        # responses above: exactly two distinct rows in `identity.users`
        # share this email, one per provider, neither merged nor linked.
        result = await db_session.execute(
            text(
                "SELECT id, auth_provider FROM identity.users "
                "WHERE email = :email ORDER BY auth_provider"
            ),
            {"email": shared_email},
        )
        rows = result.all()
        assert len(rows) == 2
        provider_by_id = {str(row.id): row.auth_provider for row in rows}
        assert set(provider_by_id.values()) == {"google", "apple"}
        assert len(set(provider_by_id.keys())) == 2


class TestRefreshEndpoint:
    """AUTH-003: `POST /auth/refresh` (AC4, AC5, AC11's rotation case)."""

    @pytest.mark.anyio
    async def test_refresh_rotates_and_returns_a_new_pair(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        await seed_roles(db_session)
        await db_session.commit()

        login_data = await _login_and_get_tokens(client, sms_spy, "506000001")

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )

        assert response.status_code == 200
        body = response.json()["data"]
        assert body["access_token"]
        assert body["refresh_token"]
        # AC4: the refresh token is always rotated. The access token's
        # `jti` (session id) is unchanged by design (Decision 1,
        # `Plan_S02_AUTH-003.md`) -- if `sub`/`roles` are also unchanged
        # and both calls land in the same wall-clock second (JWT
        # timestamps are second-precision), the reissued access token can
        # be byte-identical to the previous one, so it is deliberately
        # not asserted to differ here.
        assert body["refresh_token"] != login_data["refresh_token"]

    @pytest.mark.anyio
    async def test_reusing_an_already_rotated_refresh_token_fails(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC5 / AC11: an already-used (rotated-away) refresh token is
        rejected."""
        await seed_roles(db_session)
        await db_session.commit()

        login_data = await _login_and_get_tokens(client, sms_spy, "506000002")

        first_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert first_refresh.status_code == 200

        second_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert second_refresh.status_code == 401
        assert "session could not be refreshed" in second_refresh.json()["message"]

    @pytest.mark.anyio
    async def test_refresh_with_an_unknown_token_fails(
        self, client: TestClient
    ) -> None:
        """AC5: a refresh token that was never issued is rejected."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "never-issued-token-value"},
        )
        assert response.status_code == 401


class TestSessionsEndpoints:
    """
    AUTH-003: `GET /auth/sessions`, `DELETE /auth/sessions/{id}`,
    `POST /auth/sessions/logout-all` (AC7, AC8, AC9, AC10, AC11).
    """

    @pytest.mark.anyio
    async def test_list_sessions_requires_authentication(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/auth/sessions")
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_list_sessions_shows_device_info_and_flags_current(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC7."""
        await seed_roles(db_session)
        await db_session.commit()

        login_data = await _login_and_get_tokens(
            client,
            sms_spy,
            "506000010",
            device={"device_platform": "ios", "device_name": "My iPhone"},
        )
        headers = {"Authorization": f"Bearer {login_data['access_token']}"}

        response = client.get("/api/v1/auth/sessions", headers=headers)

        assert response.status_code == 200
        sessions = response.json()["data"]
        assert len(sessions) == 1
        assert sessions[0]["device_name"] == "My iPhone"
        assert sessions[0]["platform"] == "ios"
        assert sessions[0]["is_current"] is True

    @pytest.mark.anyio
    async def test_delete_session_then_refresh_with_its_token_fails(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC8 / AC11: revoke-then-refresh-fails."""
        await seed_roles(db_session)
        await db_session.commit()

        login_data = await _login_and_get_tokens(client, sms_spy, "506000011")
        headers = {"Authorization": f"Bearer {login_data['access_token']}"}

        sessions_resp = client.get("/api/v1/auth/sessions", headers=headers)
        session_id = sessions_resp.json()["data"][0]["id"]

        delete_resp = client.delete(
            f"/api/v1/auth/sessions/{session_id}", headers=headers
        )
        assert delete_resp.status_code == 200

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert refresh_resp.status_code == 401

    @pytest.mark.anyio
    async def test_logout_all_revokes_every_session(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC9 (no keep_current)."""
        await seed_roles(db_session)
        await db_session.commit()

        first_login = await _login_and_get_tokens(client, sms_spy, "506000012")
        code = await _request_otp(client, sms_spy, "506000012")
        second_response = _verify_otp(client, "506000012", code)
        second_login = second_response.json()["data"]

        headers = {"Authorization": f"Bearer {second_login['access_token']}"}
        logout_resp = client.post(
            "/api/v1/auth/sessions/logout-all", json={}, headers=headers
        )
        assert logout_resp.status_code == 200

        for refresh_token_value in (
            first_login["refresh_token"],
            second_login["refresh_token"],
        ):
            refresh_resp = client.post(
                "/api/v1/auth/refresh", json={"refresh_token": refresh_token_value}
            )
            assert refresh_resp.status_code == 401

    @pytest.mark.anyio
    async def test_logout_all_can_keep_the_current_session(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC9 (keep_current=True) -- a distinct, separately labeled
        action from a single-session DELETE."""
        await seed_roles(db_session)
        await db_session.commit()

        first_login = await _login_and_get_tokens(client, sms_spy, "506000013")
        code = await _request_otp(client, sms_spy, "506000013")
        second_response = _verify_otp(client, "506000013", code)
        second_login = second_response.json()["data"]

        headers = {"Authorization": f"Bearer {second_login['access_token']}"}
        logout_resp = client.post(
            "/api/v1/auth/sessions/logout-all",
            json={"keep_current": True},
            headers=headers,
        )
        assert logout_resp.status_code == 200

        # The first session's token is revoked...
        first_refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_login["refresh_token"]},
        )
        assert first_refresh_resp.status_code == 401

        # ...but the second (current) session's token still works.
        second_refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": second_login["refresh_token"]},
        )
        assert second_refresh_resp.status_code == 200

    @pytest.mark.anyio
    async def test_user_cannot_list_or_revoke_another_users_session(
        self, client: TestClient, sms_spy: SpySmsSender, db_session
    ) -> None:
        """AC10 / AC11: explicit ownership-boundary test."""
        await seed_roles(db_session)
        await db_session.commit()

        user_a_login = await _login_and_get_tokens(client, sms_spy, "506000014")
        user_a_headers = {"Authorization": f"Bearer {user_a_login['access_token']}"}
        user_a_sessions = client.get(
            "/api/v1/auth/sessions", headers=user_a_headers
        ).json()["data"]
        user_a_session_id = user_a_sessions[0]["id"]

        user_b_login = await _login_and_get_tokens(client, sms_spy, "506000015")
        user_b_headers = {"Authorization": f"Bearer {user_b_login['access_token']}"}

        # User B's own session list never contains User A's session.
        user_b_sessions = client.get(
            "/api/v1/auth/sessions", headers=user_b_headers
        ).json()["data"]
        assert all(s["id"] != user_a_session_id for s in user_b_sessions)

        # User B cannot revoke User A's session -- 404, revealing nothing.
        cross_delete_resp = client.delete(
            f"/api/v1/auth/sessions/{user_a_session_id}", headers=user_b_headers
        )
        assert cross_delete_resp.status_code == 404

        # User A's session (and its refresh token) is untouched.
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user_a_login["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
