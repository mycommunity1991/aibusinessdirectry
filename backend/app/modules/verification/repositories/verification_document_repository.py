import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.verification.models import VerificationDocument
from app.repositories.base_repository import BaseRepository


class VerificationDocumentRepository(BaseRepository[VerificationDocument]):
    """
    Repository for the `verification.verification_documents` table
    (VER-001). `get_by_id` (used by `VerificationService.get_document_
    bytes`) is inherited unchanged from `BaseRepository` -- ownership is
    enforced one layer up, via the document -> parent record ->
    `provider_id` chain (`ensure_owner_or_not_found`, ADR-015).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=VerificationDocument, session=session)

    async def list_for_record(
        self, verification_record_id: uuid.UUID
    ) -> Sequence[VerificationDocument]:
        """Lists every document attached to one verification cycle --
        used to build `GET /providers/me/verification`'s response."""
        stmt = select(VerificationDocument).where(
            VerificationDocument.verification_record_id == verification_record_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
