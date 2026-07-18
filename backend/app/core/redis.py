"""
Redis client used for caching and rate limiting.

`06_SECURITY.md` "Rate Limiting" — Redis-based, configured via `REDIS_URL`.
Mirrors the module-level engine pattern in `app.database.database` — the
client is created once at import time; `redis.asyncio.Redis` connections
are lazy, so no I/O happens until the first command is issued.
"""

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings

redis_client: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis_client(request: Request) -> Redis:
    """FastAPI dependency providing the app-wide Redis client."""
    client: Redis = request.app.state.services.redis_client
    return client
