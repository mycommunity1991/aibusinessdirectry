"""
Unit tests for `CustomerService` (CUS-001).

Repositories are mocked so these tests isolate the provisioning/get-or-
create/partial-update orchestration logic. See
`tests/modules/customer/test_customer_endpoints.py` for end-to-end
coverage against a real database (AC1/AC4/AC7), and
`tests/modules/identity/test_auth_endpoints.py` for the AC2/AC8 same-
transaction atomicity proof.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.customer.models import (
    CustomerPreferences,
    CustomerProfile,
    NotificationChannel,
)
from app.modules.customer.services.customer_service import (
    DEFAULT_DISPLAY_NAME,
    CustomerService,
)
from app.modules.identity.models import LanguageCode


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_profile_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_preferences_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_customer_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def customer_service(
    mock_profile_repository: MagicMock, mock_preferences_repository: MagicMock
) -> CustomerService:
    return CustomerService(
        profile_repository=mock_profile_repository,
        preferences_repository=mock_preferences_repository,
    )


def _profile(user_id: uuid.UUID | None = None, **kwargs) -> CustomerProfile:
    return CustomerProfile(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        display_name=kwargs.pop("display_name", DEFAULT_DISPLAY_NAME),
        avatar_url=kwargs.pop("avatar_url", None),
    )


def _preferences(customer_id: uuid.UUID, **kwargs) -> CustomerPreferences:
    return CustomerPreferences(
        id=uuid.uuid4(),
        customer_id=customer_id,
        notification_channel=kwargs.pop(
            "notification_channel", NotificationChannel.WHATSAPP
        ),
        language=kwargs.pop("language", LanguageCode.EN),
    )


class TestProvisionDefaultProfile:
    """AC2/AC3/AC8."""

    @pytest.mark.anyio
    async def test_creates_both_rows_with_whatsapp_and_english_fallback(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        """AC3: notification_channel is always whatsapp; a missing
        Accept-Language header falls back to English."""
        user_id = uuid.uuid4()
        created_profile = _profile(user_id=user_id)
        mock_profile_repository.create.return_value = created_profile
        created_preferences = _preferences(created_profile.id)
        mock_preferences_repository.create.return_value = created_preferences

        profile, preferences = await customer_service.provision_default_profile(
            user_id, accept_language_header=None
        )

        mock_profile_repository.create.assert_awaited_once_with(
            {
                "user_id": user_id,
                "display_name": DEFAULT_DISPLAY_NAME,
                "avatar_url": None,
            }
        )
        preferences_call = mock_preferences_repository.create.await_args.args[0]
        assert preferences_call["customer_id"] == created_profile.id
        assert preferences_call["notification_channel"] == NotificationChannel.WHATSAPP
        assert preferences_call["language"] == LanguageCode.EN
        assert profile is created_profile
        assert preferences is created_preferences

    @pytest.mark.anyio
    async def test_arabic_accept_language_header_resolves_to_arabic(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        """AC3: a supported `Accept-Language` header resolves to that language."""
        user_id = uuid.uuid4()
        created_profile = _profile(user_id=user_id)
        mock_profile_repository.create.return_value = created_profile
        mock_preferences_repository.create.return_value = _preferences(
            created_profile.id
        )

        await customer_service.provision_default_profile(
            user_id, accept_language_header="ar-AE,ar;q=0.9,en;q=0.8"
        )

        preferences_call = mock_preferences_repository.create.await_args.args[0]
        assert preferences_call["language"] == LanguageCode.AR
        # AC3: notification_channel is unconditionally whatsapp, regardless
        # of the language header.
        assert preferences_call["notification_channel"] == NotificationChannel.WHATSAPP

    @pytest.mark.anyio
    async def test_garbage_accept_language_header_falls_back_to_english(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        created_profile = _profile(user_id=user_id)
        mock_profile_repository.create.return_value = created_profile
        mock_preferences_repository.create.return_value = _preferences(
            created_profile.id
        )

        await customer_service.provision_default_profile(
            user_id, accept_language_header="zz-ZZ,fr;q=0.9"
        )

        preferences_call = mock_preferences_repository.create.await_args.args[0]
        assert preferences_call["language"] == LanguageCode.EN


class TestGetMyProfile:
    """Decision 4: get-or-create for legacy (pre-CUS-001) accounts."""

    @pytest.mark.anyio
    async def test_lazily_provisions_a_default_profile_for_a_legacy_user(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        """A caller with no existing `customer_profiles` row (a Sprint-2
        account) gets one lazily created with English-fallback defaults,
        rather than a 404."""
        user_id = uuid.uuid4()
        mock_profile_repository.get_by_user_id.return_value = None
        created_profile = _profile(user_id=user_id)
        mock_profile_repository.create.return_value = created_profile
        created_preferences = _preferences(created_profile.id)
        mock_preferences_repository.create.return_value = created_preferences

        profile, preferences = await customer_service.get_my_profile(user_id)

        mock_profile_repository.create.assert_awaited_once()
        assert profile is created_profile
        assert preferences is created_preferences

    @pytest.mark.anyio
    async def test_returns_existing_profile_and_preferences_without_creating(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        existing_profile = _profile(user_id=user_id, display_name="Existing Name")
        mock_profile_repository.get_by_user_id.return_value = existing_profile
        existing_preferences = _preferences(
            existing_profile.id, language=LanguageCode.AR
        )
        mock_preferences_repository.get_by_customer_id.return_value = (
            existing_preferences
        )

        profile, preferences = await customer_service.get_my_profile(user_id)

        mock_profile_repository.create.assert_not_awaited()
        mock_preferences_repository.create.assert_not_awaited()
        assert profile is existing_profile
        assert preferences is existing_preferences


class TestUpdateMyProfile:
    """AC4: partial-update semantics -- only provided fields change."""

    @pytest.mark.anyio
    async def test_only_updates_the_provided_fields(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        existing_profile = _profile(user_id=user_id, display_name="Old Name")
        mock_profile_repository.get_by_user_id.return_value = existing_profile
        existing_preferences = _preferences(existing_profile.id)
        mock_preferences_repository.get_by_customer_id.return_value = (
            existing_preferences
        )
        updated_profile = _profile(
            user_id=user_id, display_name="New Name", avatar_url=None
        )
        mock_profile_repository.update.return_value = updated_profile

        profile, preferences = await customer_service.update_my_profile(
            user_id, fields={"display_name": "New Name"}
        )

        mock_profile_repository.update.assert_awaited_once_with(
            existing_profile, {"display_name": "New Name"}
        )
        mock_preferences_repository.update.assert_not_awaited()
        assert profile is updated_profile
        assert preferences is existing_preferences

    @pytest.mark.anyio
    async def test_updating_only_language_leaves_display_name_untouched(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        existing_profile = _profile(user_id=user_id)
        mock_profile_repository.get_by_user_id.return_value = existing_profile
        existing_preferences = _preferences(existing_profile.id)
        mock_preferences_repository.get_by_customer_id.return_value = (
            existing_preferences
        )
        updated_preferences = _preferences(
            existing_profile.id, language=LanguageCode.AR
        )
        mock_preferences_repository.update.return_value = updated_preferences

        profile, preferences = await customer_service.update_my_profile(
            user_id, fields={"language": LanguageCode.AR}
        )

        mock_preferences_repository.update.assert_awaited_once_with(
            existing_preferences, {"language": LanguageCode.AR}
        )
        mock_profile_repository.update.assert_not_awaited()
        assert profile is existing_profile
        assert preferences is updated_preferences

    @pytest.mark.anyio
    async def test_empty_fields_updates_nothing(
        self,
        customer_service: CustomerService,
        mock_profile_repository: MagicMock,
        mock_preferences_repository: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        existing_profile = _profile(user_id=user_id)
        mock_profile_repository.get_by_user_id.return_value = existing_profile
        existing_preferences = _preferences(existing_profile.id)
        mock_preferences_repository.get_by_customer_id.return_value = (
            existing_preferences
        )

        profile, preferences = await customer_service.update_my_profile(
            user_id, fields={}
        )

        mock_profile_repository.update.assert_not_awaited()
        mock_preferences_repository.update.assert_not_awaited()
        assert profile is existing_profile
        assert preferences is existing_preferences


class TestResolveDefaultLanguage:
    """Unit-level direct coverage of the header-parsing logic (AC3)."""

    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            (None, LanguageCode.EN),
            ("", LanguageCode.EN),
            ("ar", LanguageCode.AR),
            ("ar-AE,ar;q=0.9,en;q=0.8", LanguageCode.AR),
            ("en-US,en;q=0.9,ar;q=0.8", LanguageCode.EN),
            ("fr-FR,fr;q=0.9", LanguageCode.EN),
            ("garbage-header;;;", LanguageCode.EN),
        ],
    )
    def test_resolves_expected_language(
        self, header: str | None, expected: LanguageCode
    ) -> None:
        assert CustomerService._resolve_default_language(header) == expected
