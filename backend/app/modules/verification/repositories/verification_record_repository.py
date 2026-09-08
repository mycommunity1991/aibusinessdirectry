import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.verification.models import VerificationRecord
from app.repositories.base_repository import BaseRepository


class VerificationRecordRepository(BaseRepository[VerificationRecord]):
    """Repository for the `verification.verification_records` table (VER-001)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=VerificationRecord, session=session)

    async def get_latest_for_provider(
        self, provider_id: uuid.UUID
    ) -> VerificationRecord | None:
        """
        Returns a provider's single latest verification cycle, ordered by
        `submitted_at` descending -- used by both `GET
        /providers/me/verification` (AC6, reads this directly, never
        `providers.verification_status`, Decision 2) and
        `VerificationService.submit`'s resubmission-eligibility check
        (Decision 4/AC7).
        """
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.provider_id == provider_id)
            .order_by(VerificationRecord.submitted_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
