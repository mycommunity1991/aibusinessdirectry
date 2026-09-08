from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """
    Repository for the `notification.notifications` table (VER-002). No
    custom methods -- `NotificationService` exposes the one explicit
    write path this module needs today. A future "read my notifications"
    inbox story would add a `list_for_user` method here.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Notification, session=session)
