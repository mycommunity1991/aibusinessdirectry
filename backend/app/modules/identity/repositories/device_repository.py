import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Device, DevicePlatform
from app.repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    """
    Repository for the `identity.devices` table.

    Find-or-update key is `(user_id, platform, device_name)` -- the
    documented `devices` schema has no separate client-generated device
    ID column (Decision 2, `Plan_S02_AUTH-003.md`). Known, accepted
    limitation: two separate installs from the same user on the same
    platform with an identical (or absent) device name collapse into one
    `Device` row.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Device, session=session)

    async def find_or_create(
        self,
        user_id: uuid.UUID,
        platform: DevicePlatform,
        device_name: str | None,
    ) -> Device:
        """
        Finds the matching `Device` row for `(user_id, platform,
        device_name)`, updating its `last_seen_at`, or creates a new one
        if none exists (AC6). Always reflects the current login moment in
        `last_seen_at`, whether the row was just created or already
        existed.
        """
        stmt = select(Device).where(
            Device.user_id == user_id,
            Device.platform == platform,
            Device.device_name == device_name,
        )
        result = await self.session.execute(stmt)
        device = result.scalar_one_or_none()

        now = datetime.now(UTC)
        if device is None:
            device = Device(
                user_id=user_id,
                platform=platform,
                device_name=device_name,
                last_seen_at=now,
            )
            self.session.add(device)
        else:
            device.last_seen_at = now

        await self.session.flush()
        await self.session.refresh(device)
        return device
