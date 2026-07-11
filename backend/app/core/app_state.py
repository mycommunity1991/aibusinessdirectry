from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class AppState:
    db_engine: AsyncEngine | None = None
    redis_client: Any | None = None
    background_workers: Any | None = None
