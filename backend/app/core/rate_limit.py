"""
Redis-backed fixed-window rate limiting for public-facing endpoints.

`05_API_GUIDELINES.md` "Rate Limiting" (e.g. Authentication: 10
requests/minute) and `06_SECURITY.md` "Rate Limiting" (Redis-based,
`REDIS_URL`). Implemented as a plain `INCR` + `EXPIRE` fixed-window
counter — simple, cheap, and sufficient for the limits this project
documents; a sliding-window/token-bucket algorithm is not required.
"""

from typing import Literal

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.exceptions import RateLimitExceededError
from app.core.redis import get_redis_client

_RATE_LIMIT_KEY_PREFIX = "ratelimit"

KeyStrategy = Literal["phone", "ip"]


async def _check_fixed_window(
    redis_client: Redis, key: str, limit: int, window_seconds: int
) -> None:
    """
    Increment the fixed-window counter for `key` (`INCR`), setting its
    expiry only on the first increment of each window (`EXPIRE`). Raises
    `RateLimitExceededError` once more than `limit` requests have been
    recorded for `key` within the current window.
    """
    full_key = f"{_RATE_LIMIT_KEY_PREFIX}:{key}"
    current = await redis_client.incr(full_key)
    if current == 1:
        await redis_client.expire(full_key, window_seconds)
    if current > limit:
        raise RateLimitExceededError()


class RateLimitDependency:
    """
    A FastAPI dependency enforcing a fixed-window Redis rate limit.

    Intended for use via `dependencies=[Depends(...)]` on a route (a
    side-effect-only check — it returns nothing and is not injected as a
    path-function parameter), matching FastAPI's callable-class dependency
    idiom.

    `key_by="phone"` keys the counter by the request body's
    `phone_country_code`/`phone_number` fields (falling back to the client
    IP if either is absent) — the meaningful key for SMS-bombing
    protection against a single number. `key_by="ip"` keys by client IP
    only, protecting against a single client hammering the endpoint
    across many different phone numbers, which a phone-keyed limit would
    not catch (each phone number gets its own independent counter).
    """

    def __init__(
        self, *, limit: int, window_seconds: int, key_by: KeyStrategy = "ip"
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_by = key_by

    async def __call__(
        self,
        request: Request,
        redis_client: Redis = Depends(get_redis_client),  # noqa: B008
    ) -> None:
        identity_part = await self._resolve_identity(request)
        key = f"{request.url.path}:{identity_part}"
        await _check_fixed_window(redis_client, key, self.limit, self.window_seconds)

    async def _resolve_identity(self, request: Request) -> str:
        client_host = request.client.host if request.client else "unknown"
        if self.key_by == "ip":
            return client_host

        try:
            body: dict[str, object] = await request.json()
        except Exception:
            body = {}

        phone_country_code = str(body.get("phone_country_code") or "")
        phone_number = str(body.get("phone_number") or "")
        if phone_country_code and phone_number:
            return f"{phone_country_code}{phone_number}"
        return client_host
