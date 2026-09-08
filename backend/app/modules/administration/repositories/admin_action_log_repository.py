from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.administration.models import AdminActionLog
from app.repositories.base_repository import BaseRepository


class AdminActionLogRepository(BaseRepository[AdminActionLog]):
    """
    Repository for the `administration.admin_action_log` table
    (VER-002). No custom methods beyond the inherited `create` --
    `AdminActionLogService` exposes the one explicit write path this
    module needs.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=AdminActionLog, session=session)
