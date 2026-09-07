"""
Saved-address management for a Customer (CUS-002).

Depends on `CustomerService` (same-module dependency, not cross-module)
rather than a raw `CustomerProfileRepository` -- `get_my_profile` is
already get-or-create (CUS-001, Decision 4), so a pre-CUS-001 account
that has never called `GET`/`PATCH /customers/me` still gets a
`customer_profiles` row lazily provisioned here, and can add its first
address without a spurious 404/500 (Decision 4, `Plan_S03_CUS-002.md`).
"""

import uuid
from typing import Any

from app.core.authorization import ensure_owner_or_not_found
from app.core.exceptions import SavedAddressNotFoundError
from app.modules.customer.models import SavedAddress
from app.modules.customer.repositories.saved_address_repository import (
    SavedAddressRepository,
)
from app.modules.customer.services.customer_service import CustomerService


class SavedAddressService:
    """Orchestrates listing, creating, updating, and soft-deleting a
    customer's saved addresses, including default-address uniqueness."""

    def __init__(
        self,
        saved_address_repository: SavedAddressRepository,
        customer_service: CustomerService,
    ) -> None:
        self.saved_address_repository = saved_address_repository
        self.customer_service = customer_service

    async def list_my_addresses(self, user_id: uuid.UUID) -> list[SavedAddress]:
        """Lists the caller's own active addresses (AC6)."""
        profile, _preferences = await self.customer_service.get_my_profile(user_id)
        return list(await self.saved_address_repository.list_for_customer(profile.id))

    async def create_address(
        self, user_id: uuid.UUID, *, fields: dict[str, Any]
    ) -> SavedAddress:
        """
        Creates a new address for the caller (AC1). If `is_default` is
        set, every other active address's `is_default` is unset first,
        in the same flush (Decision 2, AC2/AC9) -- never a separate
        commit, so two rows can never both be marked default within one
        committed transaction.
        """
        profile, _preferences = await self.customer_service.get_my_profile(user_id)

        if fields.get("is_default"):
            await self.saved_address_repository.unset_other_defaults(profile.id)

        return await self.saved_address_repository.create(
            {**fields, "customer_id": profile.id}
        )

    async def update_address(
        self,
        user_id: uuid.UUID,
        address_id: uuid.UUID,
        *,
        fields: dict[str, Any],
    ) -> SavedAddress:
        """
        Partially updates one of the caller's own addresses (AC6).
        Ownership enforced via `ensure_owner_or_not_found` -- a missing
        address and one owned by a different customer both raise the
        same `SavedAddressNotFoundError` (AC8), never a 403.

        If `is_default` is being set to `True`, every other active
        address's `is_default` is unset first, in the same flush as the
        update itself (Decision 2, AC2/AC9).
        """
        profile, _preferences = await self.customer_service.get_my_profile(user_id)
        address = await self.saved_address_repository.get_active_by_id(address_id)
        ensure_owner_or_not_found(
            address.customer_id if address is not None else None,
            profile.id,
            not_found_exc=SavedAddressNotFoundError(),
        )
        assert address is not None  # narrows for type-checkers; guaranteed above

        if fields.get("is_default") is True:
            await self.saved_address_repository.unset_other_defaults(
                profile.id, except_address_id=address.id
            )

        return await self.saved_address_repository.update(address, fields)

    async def delete_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        """
        Soft-deletes one of the caller's own addresses (AC6/AC7).
        Ownership enforced identically to `update_address` (AC8).

        Never auto-promotes another address to default when the deleted
        one was the default (Decision 3) -- the customer is left with no
        default address; deciding whether/how to choose a new one is a
        mobile-side concern (AC7).
        """
        profile, _preferences = await self.customer_service.get_my_profile(user_id)
        address = await self.saved_address_repository.get_active_by_id(address_id)
        ensure_owner_or_not_found(
            address.customer_id if address is not None else None,
            profile.id,
            not_found_exc=SavedAddressNotFoundError(),
        )
        assert address is not None  # narrows for type-checkers; guaranteed above

        await self.saved_address_repository.soft_delete(address)
