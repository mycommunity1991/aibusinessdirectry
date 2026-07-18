"""
Integration tests for the identity domain models (AUTH-001), exercised
against a real Postgres database so that native enums and partial unique
/ CHECK constraints are actually enforced (see `tests/conftest.py`
`db_session` fixture).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.identity.models import (
    AuthProvider,
    Device,
    DevicePlatform,
    LanguageCode,
    OtpPurpose,
    OtpVerification,
    Permission,
    Role,
    User,
    UserStatus,
)

# Note: these tests use real `pytest_asyncio`-managed async fixtures
# (`db_session`/`db_engine` in `tests/conftest.py`), so they rely on this
# project's `asyncio_mode = "auto"` pytest-asyncio configuration rather
# than the `anyio` marker/fixture pattern used by the purely-mocked tests
# elsewhere in the suite (mixing the two plugins' event-loop management
# for the same async fixture is unreliable).


class TestUserDefaultsAndIdentifiers:
    async def test_create_user_with_phone_only_succeeds(self, db_session):
        user = User(
            phone_country_code="+971",
            phone_number="501234567",
            auth_provider=AuthProvider.MOBILE_OTP,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.status == UserStatus.ACTIVE
        assert user.preferred_language == LanguageCode.EN
        assert user.is_active is True
        assert user.version == 1
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_missing_identifier_violates_check_constraint(self, db_session):
        user = User(auth_provider=AuthProvider.EMAIL_PASSWORD)
        db_session.add(user)

        with pytest.raises(IntegrityError, match="chk_users_has_identifier"):
            await db_session.commit()
        await db_session.rollback()

    async def test_duplicate_email_violates_unique_constraint(self, db_session):
        db_session.add(
            User(email="dup@example.com", auth_provider=AuthProvider.EMAIL_PASSWORD)
        )
        await db_session.commit()

        db_session.add(
            User(email="dup@example.com", auth_provider=AuthProvider.EMAIL_PASSWORD)
        )
        with pytest.raises(IntegrityError, match="uq_users_email"):
            await db_session.commit()
        await db_session.rollback()

    async def test_duplicate_phone_violates_unique_constraint(self, db_session):
        db_session.add(
            User(
                phone_country_code="+971",
                phone_number="501111111",
                auth_provider=AuthProvider.MOBILE_OTP,
            )
        )
        await db_session.commit()

        db_session.add(
            User(
                phone_country_code="+971",
                phone_number="501111111",
                auth_provider=AuthProvider.MOBILE_OTP,
            )
        )
        with pytest.raises(IntegrityError, match="uq_users_phone"):
            await db_session.commit()
        await db_session.rollback()

    async def test_two_null_phone_users_do_not_collide(self, db_session):
        """The partial unique index only applies WHERE phone_number IS NOT
        NULL — two email-only users must not collide with each other."""
        db_session.add(
            User(email="a@example.com", auth_provider=AuthProvider.EMAIL_PASSWORD)
        )
        db_session.add(
            User(email="b@example.com", auth_provider=AuthProvider.EMAIL_PASSWORD)
        )
        await db_session.commit()


class TestRoleAndPermissionUniqueness:
    async def test_duplicate_role_name_violates_unique_constraint(self, db_session):
        db_session.add(Role(name="customer"))
        await db_session.commit()

        db_session.add(Role(name="customer"))
        with pytest.raises(IntegrityError, match="uq_roles_name"):
            await db_session.commit()
        await db_session.rollback()

    async def test_duplicate_permission_code_violates_unique_constraint(
        self, db_session
    ):
        db_session.add(Permission(code="provider.verify"))
        await db_session.commit()

        db_session.add(Permission(code="provider.verify"))
        with pytest.raises(IntegrityError, match="uq_permissions_code"):
            await db_session.commit()
        await db_session.rollback()


class TestDeviceAndOtpVerification:
    async def test_device_requires_existing_user(self, db_session):
        user = User(
            phone_country_code="+971",
            phone_number="502222222",
            auth_provider=AuthProvider.MOBILE_OTP,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        device = Device(user_id=user.id, platform=DevicePlatform.IOS)
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        assert device.is_trusted is False
        assert device.id is not None

    async def test_otp_verification_allows_null_user_id(self, db_session):
        otp = OtpVerification(
            user_id=None,
            phone_country_code="+971",
            phone_number="503333333",
            purpose=OtpPurpose.LOGIN,
            code_hash="not-a-real-hash",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db_session.add(otp)
        await db_session.commit()
        await db_session.refresh(otp)

        assert otp.attempt_count == 0
        assert otp.verified_at is None


class TestEnumValues:
    """Enum validity — the persisted Postgres enum labels must exactly
    match `docs/AI/04_DATABASE.md` Enum Types."""

    def test_user_status_values(self):
        assert {member.value for member in UserStatus} == {
            "active",
            "suspended",
            "deleted",
        }

    def test_auth_provider_values(self):
        assert {member.value for member in AuthProvider} == {
            "google",
            "apple",
            "mobile_otp",
            "email_password",
        }

    def test_device_platform_values(self):
        assert {member.value for member in DevicePlatform} == {"ios", "android"}

    def test_language_code_values(self):
        assert {member.value for member in LanguageCode} == {"en", "ar"}

    def test_otp_purpose_values(self):
        assert {member.value for member in OtpPurpose} == {
            "registration",
            "login",
            "arrival_verification",
            "claim_listing",
        }
