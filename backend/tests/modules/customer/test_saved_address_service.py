"""
Unit tests for `SavedAddressService` (CUS-002).

Repositories/`CustomerService` are mocked so these tests isolate the
default-uniqueness (AC2/AC9) and ownership-boundary (AC8/AC9)
orchestration logic. See `test_saved_address_endpoints.py` for
end-to-end coverage against a real database.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import SavedAddressNotFoundError
from app.modules.customer.models import CustomerProfile, SavedAddress
from app.modules.customer.services.saved_address_service import SavedAddressService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_saved_address_repository() -> MagicMock:
    repo = MagicMock()
    repo.list_for_customer = AsyncMock()
    repo.get_active_by_id = AsyncMock()
    repo.unset_other_defaults = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    return repo


@pytest.fixture
def mock_customer_service() -> MagicMock:
    service = MagicMock()
    service.get_my_profile = AsyncMock()
    return service


@pytest.fixture
def saved_address_service(
    mock_saved_address_repository: MagicMock, mock_customer_service: MagicMock
) -> SavedAddressService:
    return SavedAddressService(
        saved_address_repository=mock_saved_address_repository,
        customer_service=mock_customer_service,
    )


def _profile(profile_id: uuid.UUID | None = None) -> CustomerProfile:
    return CustomerProfile(
        id=profile_id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Test Customer",
        avatar_url=None,
    )


def _address(
    address_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    is_default: bool = False,
) -> SavedAddress:
    return SavedAddress(
        id=address_id or uuid.uuid4(),
        customer_id=customer_id or uuid.uuid4(),
        label="Home",
        address_line="Villa 12, Al Wasl Road",
        city="Dubai",
        region="Dubai",
        country_code="AE",
        latitude=25.2048,
        longitude=55.2708,
        is_default=is_default,
    )


class TestListMyAddresses:
    @pytest.mark.anyio
    async def test_lists_only_the_callers_own_addresses(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        expected = [_address(customer_id=profile.id)]
        mock_saved_address_repository.list_for_customer.return_value = expected

        result = await saved_address_service.list_my_addresses(profile.user_id)

        mock_saved_address_repository.list_for_customer.assert_awaited_once_with(
            profile.id
        )
        assert result == expected


class TestCreateAddress:
    """AC1, and AC2/AC9's "default-address uniqueness" -- create-time path."""

    @pytest.mark.anyio
    async def test_creates_address_without_touching_defaults_when_not_default(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        created = _address(customer_id=profile.id)
        mock_saved_address_repository.create.return_value = created

        result = await saved_address_service.create_address(
            profile.user_id, fields={"address_line": "Some Street"}
        )

        mock_saved_address_repository.unset_other_defaults.assert_not_awaited()
        mock_saved_address_repository.create.assert_awaited_once_with(
            {"address_line": "Some Street", "customer_id": profile.id}
        )
        assert result is created

    @pytest.mark.anyio
    async def test_setting_is_default_true_unsets_other_defaults_first(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        """AC2: creating a new default address unsets any prior default,
        in the same flush as the create -- never a separate commit."""
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        created = _address(customer_id=profile.id, is_default=True)
        mock_saved_address_repository.create.return_value = created

        await saved_address_service.create_address(
            profile.user_id,
            fields={"address_line": "New Default Street", "is_default": True},
        )

        mock_saved_address_repository.unset_other_defaults.assert_awaited_once_with(
            profile.id
        )
        mock_saved_address_repository.create.assert_awaited_once_with(
            {
                "address_line": "New Default Street",
                "is_default": True,
                "customer_id": profile.id,
            }
        )

    @pytest.mark.anyio
    async def test_legacy_account_with_no_profile_yet_can_still_create_an_address(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        """Decision 4: `get_my_profile` is get-or-create, so a
        pre-CUS-001 account with no `customer_profiles` row yet does not
        404/500 when adding its first address."""
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        mock_saved_address_repository.create.return_value = _address(
            customer_id=profile.id
        )

        await saved_address_service.create_address(
            profile.user_id, fields={"address_line": "First Address"}
        )

        mock_customer_service.get_my_profile.assert_awaited_once_with(profile.user_id)


class TestUpdateAddress:
    """AC6 (partial update), AC2/AC9 (update-time default-uniqueness
    path), AC8/AC9 (ownership boundary)."""

    @pytest.mark.anyio
    async def test_only_updates_the_provided_fields(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        existing = _address(customer_id=profile.id)
        mock_saved_address_repository.get_active_by_id.return_value = existing
        updated = _address(address_id=existing.id, customer_id=profile.id)
        mock_saved_address_repository.update.return_value = updated

        result = await saved_address_service.update_address(
            profile.user_id, existing.id, fields={"city": "Abu Dhabi"}
        )

        mock_saved_address_repository.unset_other_defaults.assert_not_awaited()
        mock_saved_address_repository.update.assert_awaited_once_with(
            existing, {"city": "Abu Dhabi"}
        )
        assert result is updated

    @pytest.mark.anyio
    async def test_setting_is_default_true_unsets_other_defaults_except_itself(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        """AC2: flipping a currently-non-default address to default
        unsets the prior default first, excluding itself from that
        bulk-unset."""
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        existing = _address(customer_id=profile.id, is_default=False)
        mock_saved_address_repository.get_active_by_id.return_value = existing
        updated = _address(
            address_id=existing.id, customer_id=profile.id, is_default=True
        )
        mock_saved_address_repository.update.return_value = updated

        await saved_address_service.update_address(
            profile.user_id, existing.id, fields={"is_default": True}
        )

        mock_saved_address_repository.unset_other_defaults.assert_awaited_once_with(
            profile.id, except_address_id=existing.id
        )
        mock_saved_address_repository.update.assert_awaited_once_with(
            existing, {"is_default": True}
        )

    @pytest.mark.anyio
    async def test_raises_not_found_when_address_does_not_exist(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        mock_saved_address_repository.get_active_by_id.return_value = None

        with pytest.raises(SavedAddressNotFoundError):
            await saved_address_service.update_address(
                profile.user_id, uuid.uuid4(), fields={"city": "Sharjah"}
            )

        mock_saved_address_repository.update.assert_not_awaited()

    @pytest.mark.anyio
    async def test_raises_not_found_when_address_belongs_to_another_customer(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        """AC8/AC9: a 404, never a 403, on cross-customer access -- and
        the update must never be applied."""
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        someone_elses_address = _address(customer_id=uuid.uuid4())
        mock_saved_address_repository.get_active_by_id.return_value = (
            someone_elses_address
        )

        with pytest.raises(SavedAddressNotFoundError):
            await saved_address_service.update_address(
                profile.user_id,
                someone_elses_address.id,
                fields={"city": "Sharjah"},
            )

        mock_saved_address_repository.update.assert_not_awaited()
        mock_saved_address_repository.unset_other_defaults.assert_not_awaited()


class TestDeleteAddress:
    """AC6/AC7 (soft delete, no auto-promotion), AC8/AC9 (ownership boundary)."""

    @pytest.mark.anyio
    async def test_soft_deletes_a_non_default_address_leaving_default_untouched(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        existing = _address(customer_id=profile.id, is_default=False)
        mock_saved_address_repository.get_active_by_id.return_value = existing

        await saved_address_service.delete_address(profile.user_id, existing.id)

        mock_saved_address_repository.soft_delete.assert_awaited_once_with(existing)

    @pytest.mark.anyio
    async def test_deleting_the_default_does_not_auto_promote_another(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        """Decision 3: the backend never picks a new default on the
        customer's behalf -- it only soft-deletes."""
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        existing_default = _address(customer_id=profile.id, is_default=True)
        mock_saved_address_repository.get_active_by_id.return_value = existing_default

        await saved_address_service.delete_address(profile.user_id, existing_default.id)

        mock_saved_address_repository.soft_delete.assert_awaited_once_with(
            existing_default
        )
        mock_saved_address_repository.unset_other_defaults.assert_not_awaited()
        mock_saved_address_repository.update.assert_not_awaited()

    @pytest.mark.anyio
    async def test_raises_not_found_when_address_belongs_to_another_customer(
        self,
        saved_address_service: SavedAddressService,
        mock_saved_address_repository: MagicMock,
        mock_customer_service: MagicMock,
    ) -> None:
        profile = _profile()
        mock_customer_service.get_my_profile.return_value = (profile, MagicMock())
        someone_elses_address = _address(customer_id=uuid.uuid4())
        mock_saved_address_repository.get_active_by_id.return_value = (
            someone_elses_address
        )

        with pytest.raises(SavedAddressNotFoundError):
            await saved_address_service.delete_address(
                profile.user_id, someone_elses_address.id
            )

        mock_saved_address_repository.soft_delete.assert_not_awaited()
