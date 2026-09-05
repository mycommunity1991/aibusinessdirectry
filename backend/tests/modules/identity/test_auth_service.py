"""
Unit tests for `AuthService` orchestration (AC6, AC7, AC12).

`OtpService`/repositories are mocked so these tests isolate the
find-or-create-User orchestration logic. See
`tests/api/test_auth_endpoints.py` for end-to-end coverage against a real
database, including AC12 (no `customer_profiles`/`customer_preferences`
row).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import ROLE_CUSTOMER
from app.modules.identity.models import (
    AuthProvider,
    LanguageCode,
    Role,
    User,
    UserStatus,
)
from app.modules.identity.services.auth_service import AuthService
from app.modules.identity.services.id_token_verifier import IdentityClaims


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_phone = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_role_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_name = AsyncMock()
    return repo


@pytest.fixture
def mock_otp_service() -> AsyncMock:
    service = AsyncMock()
    service.verify_otp = AsyncMock()
    return service


@pytest.fixture
def auth_service(
    mock_session: MagicMock,
    mock_user_repository: MagicMock,
    mock_role_repository: MagicMock,
    mock_otp_service: AsyncMock,
) -> AuthService:
    return AuthService(
        session=mock_session,
        user_repository=mock_user_repository,
        role_repository=mock_role_repository,
        otp_service=mock_otp_service,
    )


def _scalars_result(values: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.anyio
async def test_verify_otp_and_authenticate_creates_user_and_assigns_customer_role(
    auth_service: AuthService,
    mock_user_repository: MagicMock,
    mock_role_repository: MagicMock,
    mock_session: MagicMock,
) -> None:
    """AC6: a verified OTP for an unrecognized number creates a new User
    with auth_provider=mobile_otp and assigns the customer role."""
    mock_user_repository.get_by_phone.return_value = None
    created_user = User(
        id=uuid.uuid4(),
        phone_country_code="+971",
        phone_number="501234567",
        auth_provider=AuthProvider.MOBILE_OTP,
        status=UserStatus.ACTIVE,
        preferred_language=LanguageCode.EN,
    )
    mock_user_repository.create.return_value = created_user
    customer_role = Role(id=uuid.uuid4(), name=ROLE_CUSTOMER)
    mock_role_repository.get_by_name.return_value = customer_role
    mock_session.execute.return_value = _scalars_result([ROLE_CUSTOMER])

    user, token, roles = await auth_service.verify_otp_and_authenticate(
        "+971", "501234567", "123456"
    )

    mock_user_repository.create.assert_awaited_once()
    created_values = mock_user_repository.create.await_args.args[0]
    assert created_values["auth_provider"] == AuthProvider.MOBILE_OTP
    assert created_values["phone_country_code"] == "+971"
    assert created_values["phone_number"] == "501234567"

    mock_role_repository.get_by_name.assert_awaited_once_with(ROLE_CUSTOMER)
    mock_session.add.assert_called_once()  # the UserRole row
    assert user is created_user
    assert token
    assert roles == [ROLE_CUSTOMER]


@pytest.mark.anyio
async def test_verify_otp_and_authenticate_existing_user_does_not_duplicate(
    auth_service: AuthService,
    mock_user_repository: MagicMock,
    mock_role_repository: MagicMock,
    mock_session: MagicMock,
) -> None:
    """AC7: a verified OTP for an existing phone number authenticates that
    User without creating a duplicate."""
    existing_user = User(
        id=uuid.uuid4(),
        phone_country_code="+971",
        phone_number="501234567",
        auth_provider=AuthProvider.MOBILE_OTP,
        status=UserStatus.ACTIVE,
        preferred_language=LanguageCode.EN,
    )
    mock_user_repository.get_by_phone.return_value = existing_user
    mock_session.execute.return_value = _scalars_result([ROLE_CUSTOMER])

    user, token, roles = await auth_service.verify_otp_and_authenticate(
        "+971", "501234567", "123456"
    )

    mock_user_repository.create.assert_not_awaited()
    mock_role_repository.get_by_name.assert_not_awaited()
    mock_session.add.assert_not_called()  # no new UserRole row
    assert user is existing_user
    assert token


@pytest.mark.anyio
async def test_verify_otp_and_authenticate_uses_login_purpose_for_otp(
    auth_service: AuthService,
    mock_otp_service: AsyncMock,
    mock_user_repository: MagicMock,
    mock_session: MagicMock,
) -> None:
    """Decision 7: no client-supplied registration-vs-login distinction —
    always OtpPurpose.LOGIN."""
    from app.modules.identity.models import OtpPurpose

    mock_user_repository.get_by_phone.return_value = User(
        id=uuid.uuid4(),
        phone_country_code="+971",
        phone_number="501234567",
        auth_provider=AuthProvider.MOBILE_OTP,
        status=UserStatus.ACTIVE,
        preferred_language=LanguageCode.EN,
    )
    mock_session.execute.return_value = _scalars_result([])

    await auth_service.verify_otp_and_authenticate("+971", "501234567", "123456")

    mock_otp_service.verify_otp.assert_awaited_once_with(
        "+971", "501234567", OtpPurpose.LOGIN, "123456"
    )


@pytest.mark.anyio
async def test_request_otp_delegates_to_otp_service_with_login_purpose(
    auth_service: AuthService, mock_otp_service: AsyncMock
) -> None:
    from app.modules.identity.models import OtpPurpose

    await auth_service.request_otp("+971", "501234567")

    mock_otp_service.request_otp.assert_awaited_once_with(
        "+971", "501234567", OtpPurpose.LOGIN
    )


class TestAuthenticateWithOauth:
    """
    Unit tests for `AuthService.authenticate_with_oauth` (AUTH-002).
    `claims` are assumed already server-verified by `OAuthService` --
    these tests isolate the find-or-create-User orchestration only. See
    `tests/modules/identity/test_auth_endpoints.py` for end-to-end
    coverage, including the AC9 two-distinct-users check.
    """

    @pytest.mark.anyio
    async def test_new_pair_creates_user_and_assigns_customer_role(
        self,
        auth_service: AuthService,
        mock_user_repository: MagicMock,
        mock_role_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """AC3: a new (provider, subject) pair creates a new User and
        assigns the customer role."""
        mock_user_repository.get_by_provider_and_subject = AsyncMock(return_value=None)
        created_user = User(
            id=uuid.uuid4(),
            auth_provider=AuthProvider.GOOGLE,
            external_auth_subject="google-sub-1",
            email="person@example.com",
            status=UserStatus.ACTIVE,
            preferred_language=LanguageCode.EN,
        )
        mock_user_repository.create.return_value = created_user
        customer_role = Role(id=uuid.uuid4(), name=ROLE_CUSTOMER)
        mock_role_repository.get_by_name.return_value = customer_role
        mock_session.execute.return_value = _scalars_result([ROLE_CUSTOMER])

        claims = IdentityClaims(
            subject="google-sub-1", email="person@example.com", email_verified=True
        )
        user, token, roles = await auth_service.authenticate_with_oauth(
            AuthProvider.GOOGLE, claims
        )

        mock_user_repository.create.assert_awaited_once()
        created_values = mock_user_repository.create.await_args.args[0]
        assert created_values["auth_provider"] == AuthProvider.GOOGLE
        assert created_values["external_auth_subject"] == "google-sub-1"
        assert created_values["email"] == "person@example.com"
        assert created_values["email_verified_at"] is not None

        mock_role_repository.get_by_name.assert_awaited_once_with(ROLE_CUSTOMER)
        mock_session.add.assert_called_once()  # the UserRole row
        assert user is created_user
        assert token
        assert roles == [ROLE_CUSTOMER]

    @pytest.mark.anyio
    async def test_existing_pair_authenticates_without_duplicating(
        self,
        auth_service: AuthService,
        mock_user_repository: MagicMock,
        mock_role_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """AC4: an existing (provider, subject) pair authenticates the
        existing User without creating a duplicate."""
        existing_user = User(
            id=uuid.uuid4(),
            auth_provider=AuthProvider.GOOGLE,
            external_auth_subject="google-sub-1",
            email="person@example.com",
            status=UserStatus.ACTIVE,
            preferred_language=LanguageCode.EN,
        )
        mock_user_repository.get_by_provider_and_subject = AsyncMock(
            return_value=existing_user
        )
        mock_session.execute.return_value = _scalars_result([ROLE_CUSTOMER])

        claims = IdentityClaims(
            subject="google-sub-1", email="person@example.com", email_verified=True
        )
        user, token, _roles = await auth_service.authenticate_with_oauth(
            AuthProvider.GOOGLE, claims
        )

        mock_user_repository.create.assert_not_awaited()
        mock_role_repository.get_by_name.assert_not_awaited()
        mock_session.add.assert_not_called()  # no new UserRole row
        assert user is existing_user
        assert user.last_login_at is not None
        assert token

    @pytest.mark.anyio
    async def test_email_is_not_overwritten_on_a_login_where_claims_omit_it(
        self,
        auth_service: AuthService,
        mock_user_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Decision 11: Apple only guarantees email on first authorization
        -- a subsequent login must never null out (or otherwise change)
        a previously-captured email."""
        existing_user = User(
            id=uuid.uuid4(),
            auth_provider=AuthProvider.APPLE,
            external_auth_subject="apple-sub-1",
            email="original@example.com",
            status=UserStatus.ACTIVE,
            preferred_language=LanguageCode.EN,
        )
        mock_user_repository.get_by_provider_and_subject = AsyncMock(
            return_value=existing_user
        )
        mock_session.execute.return_value = _scalars_result([])

        claims_without_email = IdentityClaims(
            subject="apple-sub-1", email=None, email_verified=False
        )
        user, _token, _roles = await auth_service.authenticate_with_oauth(
            AuthProvider.APPLE, claims_without_email
        )

        assert user.email == "original@example.com"

    @pytest.mark.anyio
    async def test_looks_up_users_by_provider_and_subject_not_email(
        self,
        auth_service: AuthService,
        mock_user_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """AC5 (unit-level companion to the endpoint-level check): the
        find step is keyed on (auth_provider, external_auth_subject),
        never on email."""
        mock_user_repository.get_by_provider_and_subject = AsyncMock(
            return_value=User(
                id=uuid.uuid4(),
                auth_provider=AuthProvider.APPLE,
                external_auth_subject="apple-sub-1",
                status=UserStatus.ACTIVE,
                preferred_language=LanguageCode.EN,
            )
        )
        mock_session.execute.return_value = _scalars_result([])

        claims = IdentityClaims(
            subject="apple-sub-1", email="shared@example.com", email_verified=True
        )
        await auth_service.authenticate_with_oauth(AuthProvider.APPLE, claims)

        mock_user_repository.get_by_provider_and_subject.assert_awaited_once_with(
            AuthProvider.APPLE, "apple-sub-1"
        )
