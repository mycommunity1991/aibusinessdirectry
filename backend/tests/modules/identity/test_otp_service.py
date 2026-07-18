"""
Unit tests for `OtpService` business logic (AC3, AC4, AC5, AC8, AC11).

Repository and SMS sender are mocked — these tests exercise service-layer
decisions only (code generation/hashing, expiry/attempt-cap logic), not
real database constraints (see `tests/models/test_identity_models.py` and
`tests/api/test_auth_endpoints.py` for real-DB coverage).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import OTP_CODE_LENGTH, OTP_MAX_ATTEMPTS
from app.core.exceptions import InvalidOtpError, OtpLockedError
from app.core.security import hash_otp_code, verify_otp_code
from app.modules.identity.models import OtpPurpose, OtpVerification
from app.modules.identity.services.otp_service import OtpService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_repository() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.get_active_for_phone = AsyncMock()
    return repo


@pytest.fixture
def mock_sms_sender() -> AsyncMock:
    sender = AsyncMock()
    sender.send = AsyncMock()
    return sender


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def otp_service(
    mock_repository: MagicMock, mock_sms_sender: AsyncMock, mock_session: MagicMock
) -> OtpService:
    return OtpService(
        repository=mock_repository, sms_sender=mock_sms_sender, session=mock_session
    )


def _make_otp(
    *, code: str = "123456", attempt_count: int = 0, verified: bool = False
) -> OtpVerification:
    otp = OtpVerification(
        phone_country_code="+971",
        phone_number="501234567",
        purpose=OtpPurpose.LOGIN,
        code_hash=hash_otp_code(code),
        attempt_count=attempt_count,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        verified_at=datetime.now(UTC) if verified else None,
    )
    return otp


@pytest.mark.anyio
async def test_request_otp_generates_and_hashes_a_6_digit_code(
    otp_service: OtpService, mock_repository: MagicMock, mock_sms_sender: AsyncMock
) -> None:
    await otp_service.request_otp("+971", "501234567", OtpPurpose.LOGIN)

    mock_repository.create.assert_awaited_once()
    created_values = mock_repository.create.await_args.args[0]
    assert created_values["phone_country_code"] == "+971"
    assert created_values["phone_number"] == "501234567"
    assert created_values["purpose"] == OtpPurpose.LOGIN
    assert "code" not in created_values  # plaintext code is never persisted

    mock_sms_sender.send.assert_awaited_once()
    _, sms_args, _ = mock_sms_sender.send.mock_calls[0]
    dispatched_code = sms_args[2]
    assert len(dispatched_code) == OTP_CODE_LENGTH
    assert dispatched_code.isdigit()
    # The hash stored must actually verify against the dispatched code.
    assert verify_otp_code(dispatched_code, created_values["code_hash"])


@pytest.mark.anyio
async def test_request_otp_sets_five_minute_expiry(
    otp_service: OtpService, mock_repository: MagicMock
) -> None:
    before = datetime.now(UTC)
    await otp_service.request_otp("+971", "501234567", OtpPurpose.LOGIN)
    after = datetime.now(UTC)

    created_values = mock_repository.create.await_args.args[0]
    expires_at = created_values["expires_at"]
    assert before + timedelta(minutes=5) <= expires_at <= after + timedelta(minutes=5)


@pytest.mark.anyio
async def test_verify_otp_success_marks_verified(
    otp_service: OtpService, mock_repository: MagicMock
) -> None:
    otp = _make_otp(code="123456")
    mock_repository.get_active_for_phone.return_value = otp

    result = await otp_service.verify_otp(
        "+971", "501234567", OtpPurpose.LOGIN, "123456"
    )

    assert result is otp
    mock_repository.update.assert_awaited_once()
    updated_obj, updated_values = mock_repository.update.await_args.args
    assert updated_obj is otp
    assert "verified_at" in updated_values


@pytest.mark.anyio
async def test_verify_otp_wrong_code_increments_attempt_and_raises(
    otp_service: OtpService, mock_repository: MagicMock, mock_session: MagicMock
) -> None:
    otp = _make_otp(code="123456", attempt_count=0)
    mock_repository.get_active_for_phone.return_value = otp

    with pytest.raises(InvalidOtpError):
        await otp_service.verify_otp("+971", "501234567", OtpPurpose.LOGIN, "000000")

    mock_repository.update.assert_awaited_once_with(otp, {"attempt_count": 1})
    mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_verify_otp_missing_active_row_raises_generic_error(
    otp_service: OtpService, mock_repository: MagicMock
) -> None:
    """Covers expired / already-used / never-requested — all indistinguishable
    from the caller's perspective (AC5, AC8, AC10)."""
    mock_repository.get_active_for_phone.return_value = None

    with pytest.raises(InvalidOtpError):
        await otp_service.verify_otp("+971", "501234567", OtpPurpose.LOGIN, "123456")

    mock_repository.update.assert_not_awaited()


@pytest.mark.anyio
async def test_verify_otp_already_at_attempt_cap_raises_locked_without_incrementing(
    otp_service: OtpService, mock_repository: MagicMock
) -> None:
    otp = _make_otp(code="123456", attempt_count=OTP_MAX_ATTEMPTS)
    mock_repository.get_active_for_phone.return_value = otp

    with pytest.raises(OtpLockedError):
        await otp_service.verify_otp("+971", "501234567", OtpPurpose.LOGIN, "123456")

    mock_repository.update.assert_not_awaited()


@pytest.mark.anyio
async def test_verify_otp_reaching_attempt_cap_locks_out(
    otp_service: OtpService, mock_repository: MagicMock
) -> None:
    otp = _make_otp(code="123456", attempt_count=OTP_MAX_ATTEMPTS - 1)
    mock_repository.get_active_for_phone.return_value = otp

    with pytest.raises(OtpLockedError):
        await otp_service.verify_otp("+971", "501234567", OtpPurpose.LOGIN, "000000")

    mock_repository.update.assert_awaited_once_with(
        otp, {"attempt_count": OTP_MAX_ATTEMPTS}
    )
