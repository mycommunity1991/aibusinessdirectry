import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer.models import SavedAddress
from app.repositories.base_repository import BaseRepository


class SavedAddressRepository(BaseRepository[SavedAddress]):
    """
    Repository for the `customer.saved_addresses` table (CUS-002).

    `BaseRepository.delete()` hard-deletes -- deliberately not used here.
    `soft_delete()` is this codebase's first genuine soft-delete
    repository method (Decision 3, `Plan_S03_CUS-002.md`): every list/get
    query below filters `is_active` so a soft-deleted row is invisible to
    the customer going forward, while the row itself survives per
    `04_DATABASE.md`'s "permanent deletion is an administrative
    operation" rule.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=SavedAddress, session=session)

    async def list_for_customer(self, customer_id: uuid.UUID) -> Sequence[SavedAddress]:
        """Lists every active (non-soft-deleted) address owned by a
        customer (AC6), most-recently-created first."""
        stmt = (
            select(SavedAddress)
            .where(
                SavedAddress.customer_id == customer_id,
                SavedAddress.is_active.is_(True),
            )
            .order_by(SavedAddress.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_id(self, address_id: uuid.UUID) -> SavedAddress | None:
        """
        Retrieves an address by id only if it has not been soft-deleted.
        Used before the caller's ownership check (AC8) -- a soft-deleted
        row is treated identically to a never-existing one, mirroring
        `SessionRepository.get_active_by_id`'s pattern.
        """
        stmt = select(SavedAddress).where(
            SavedAddress.id == address_id, SavedAddress.is_active.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def unset_other_defaults(
        self,
        customer_id: uuid.UUID,
        *,
        except_address_id: uuid.UUID | None = None,
    ) -> None:
        """
        Bulk-unsets `is_default` for every other active address belonging
        to a customer (Decision 2, AC2/AC9's "default-address
        uniqueness"). Flush only -- never commits; the caller
        (`SavedAddressService`) executes this in the same flush as the
        write that sets the new default, so both changes ride the same
        endpoint transaction and a crash mid-operation can never leave
        two rows both marked default within one committed transaction.
        """
        stmt = update(SavedAddress).where(
            SavedAddress.customer_id == customer_id,
            SavedAddress.is_default.is_(True),
        )
        if except_address_id is not None:
            stmt = stmt.where(SavedAddress.id != except_address_id)
        stmt = stmt.values(is_default=False)
        await self.session.execute(stmt)
        await self.session.flush()

    async def soft_delete(self, address: SavedAddress) -> None:
        """
        Soft-deletes an address (Decision 3): sets `deleted_at`/
        `is_active`, flush only. Never a hard `session.delete()` -- per
        `04_DATABASE.md`'s Soft Delete rule, permanent deletion is an
        administrative operation, not something a customer-facing DELETE
        endpoint performs.
        """
        address.deleted_at = datetime.now(UTC)
        address.is_active = False
        self.session.add(address)
        await self.session.flush()
