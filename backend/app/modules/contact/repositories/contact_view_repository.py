from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contact.models import ContactView
from app.repositories.base_repository import BaseRepository


class ContactViewRepository(BaseRepository[ContactView]):
    """
    Repository for the `contact.contact_views` table (CON-001). No
    custom methods -- `ContactService` exposes the one explicit write
    path this module needs today (`create`, inherited from
    `BaseRepository`); no dedup/uniqueness lookup is ever performed
    (Decision 5, `Plan_S08_CON-001.md` -- every Contact tap creates a
    new row).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ContactView, session=session)
