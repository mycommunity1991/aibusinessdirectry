"""
Unit tests for the Redis-backed fixed-window rate limiter
(`app.core.rate_limit`) — `_check_fixed_window` and `RateLimitDependency`.

Closes the one gap noted in `Walkthrough_S02_AUTH-001.md` FU-5: rate
limiting was added to the auth endpoints but never had dedicated tests.
Exercises the real Redis test instance (db index 15, `redis_client`
fixture in `conftest.py`) rather than mocking the client, matching this
project's established real-service testing philosophy (mirrors the real
Postgres `db_session`/`db_engine` fixtures).

These tests call `_check_fixed_window`/`RateLimitDependency` directly
rather than through a FastAPI `TestClient`, so they run entirely on
pytest-asyncio's own per-test event loop — no risk of the cross-loop
Redis-connection issue documented on the `redis_client` fixture (that
issue is specific to `TestClient`, which drives the ASGI app from its own
background event loop). End-to-end coverage of the actual endpoint wiring
(`dependencies=[Depends(...)]`) lives in
`tests/modules/identity/test_auth_endpoints.py::TestRateLimiting`.
"""

import asyncio

import pytest
from redis.asyncio import Redis
from starlette.requests import Request

from app.core.exceptions import RateLimitExceededError
from app.core.rate_limit import RateLimitDependency, _check_fixed_window


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _make_request(
    *,
    client_host: str | None = "1.2.3.4",
    path: str = "/api/v1/auth/request-otp",
    body: bytes = b"",
) -> Request:
    """
    Builds a minimal ASGI `Request` for exercising `RateLimitDependency`
    without a running app/`TestClient` — only the pieces
    `_resolve_identity` actually reads (`request.client`,
    `request.url.path`, `request.json()`) need to be real.
    """

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    scope: dict[str, object] = {
        "type": "http",
        "path": path,
        "headers": [],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope, receive)


class TestCheckFixedWindow:
    """Directly covers the `INCR`/`EXPIRE` counter primitive."""

    @pytest.mark.anyio
    async def test_allows_requests_under_the_limit(self, redis_client: Redis) -> None:
        for _ in range(3):
            await _check_fixed_window(
                redis_client, "unit:under-limit", limit=5, window_seconds=60
            )
        assert await redis_client.get("ratelimit:unit:under-limit") == "3"

    @pytest.mark.anyio
    async def test_allows_exactly_the_configured_limit(
        self, redis_client: Redis
    ) -> None:
        """The Nth request (equal to the limit) must still succeed — only
        the (N+1)th is rejected."""
        key = "unit:exact-limit"
        for _ in range(5):
            await _check_fixed_window(redis_client, key, limit=5, window_seconds=60)
        assert await redis_client.get(f"ratelimit:{key}") == "5"

    @pytest.mark.anyio
    async def test_raises_once_the_limit_is_exceeded(self, redis_client: Redis) -> None:
        key = "unit:over-limit"
        for _ in range(3):
            await _check_fixed_window(redis_client, key, limit=3, window_seconds=60)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await _check_fixed_window(redis_client, key, limit=3, window_seconds=60)

        # AC/06_SECURITY.md: 429 with a plain-language message, no
        # internal codes or stack traces.
        assert exc_info.value.status_code == 429
        assert (
            exc_info.value.message
            == "Too many requests. Please wait a moment and try again."
        )

    @pytest.mark.anyio
    async def test_different_keys_are_isolated(self, redis_client: Redis) -> None:
        for _ in range(3):
            await _check_fixed_window(
                redis_client, "unit:key-a", limit=3, window_seconds=60
            )
        with pytest.raises(RateLimitExceededError):
            await _check_fixed_window(
                redis_client, "unit:key-a", limit=3, window_seconds=60
            )

        # A different key's counter is entirely unaffected by key-a's
        # exhausted limit.
        await _check_fixed_window(
            redis_client, "unit:key-b", limit=3, window_seconds=60
        )
        assert await redis_client.get("ratelimit:unit:key-b") == "1"

    @pytest.mark.anyio
    async def test_counter_resets_after_the_window_expires(
        self, redis_client: Redis
    ) -> None:
        """Fast expiry-reset case: a short `window_seconds` override avoids
        sleeping through the real 60s auth window."""
        key = "unit:expiry"
        await _check_fixed_window(redis_client, key, limit=1, window_seconds=1)
        with pytest.raises(RateLimitExceededError):
            await _check_fixed_window(redis_client, key, limit=1, window_seconds=1)

        await asyncio.sleep(1.2)

        # The window has expired -- the counter restarts from zero rather
        # than staying rejected forever.
        await _check_fixed_window(redis_client, key, limit=1, window_seconds=1)
        assert await redis_client.get(f"ratelimit:{key}") == "1"


class TestRateLimitDependency:
    """Covers `RateLimitDependency.__call__`/`_resolve_identity` — the
    `key_by="ip"` vs `key_by="phone"` scoping behavior configured on the
    auth endpoints."""

    @pytest.mark.anyio
    async def test_ip_keyed_limit_blocks_after_the_configured_count(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=2, window_seconds=60, key_by="ip")
        for _ in range(2):
            await dependency(
                _make_request(client_host="9.9.9.9"), redis_client=redis_client
            )

        with pytest.raises(RateLimitExceededError):
            await dependency(
                _make_request(client_host="9.9.9.9"), redis_client=redis_client
            )

    @pytest.mark.anyio
    async def test_ip_keyed_limit_is_scoped_per_client(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=1, window_seconds=60, key_by="ip")
        await dependency(
            _make_request(client_host="1.1.1.1"), redis_client=redis_client
        )
        with pytest.raises(RateLimitExceededError):
            await dependency(
                _make_request(client_host="1.1.1.1"), redis_client=redis_client
            )

        # A different client IP has its own, independent counter — not
        # affected by 1.1.1.1's exhausted limit.
        await dependency(
            _make_request(client_host="2.2.2.2"), redis_client=redis_client
        )

    @pytest.mark.anyio
    async def test_ip_keyed_limit_defaults_to_unknown_when_client_is_absent(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=1, window_seconds=60, key_by="ip")
        await dependency(_make_request(client_host=None), redis_client=redis_client)
        with pytest.raises(RateLimitExceededError):
            await dependency(_make_request(client_host=None), redis_client=redis_client)

    @pytest.mark.anyio
    async def test_phone_keyed_limit_is_scoped_per_phone_number(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=1, window_seconds=60, key_by="phone")
        body_a = b'{"phone_country_code": "+971", "phone_number": "501111111"}'
        body_b = b'{"phone_country_code": "+971", "phone_number": "502222222"}'

        await dependency(
            _make_request(client_host="5.5.5.5", body=body_a), redis_client=redis_client
        )
        with pytest.raises(RateLimitExceededError):
            await dependency(
                _make_request(client_host="5.5.5.5", body=body_a),
                redis_client=redis_client,
            )

        # A different phone number — even from the same client IP — is
        # entirely unaffected by phone A's exhausted limit.
        await dependency(
            _make_request(client_host="5.5.5.5", body=body_b), redis_client=redis_client
        )

    @pytest.mark.anyio
    async def test_phone_keyed_limit_falls_back_to_ip_when_phone_fields_missing(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=1, window_seconds=60, key_by="phone")
        await dependency(
            _make_request(client_host="6.6.6.6", body=b"{}"), redis_client=redis_client
        )
        with pytest.raises(RateLimitExceededError):
            await dependency(
                _make_request(client_host="6.6.6.6", body=b"{}"),
                redis_client=redis_client,
            )

    @pytest.mark.anyio
    async def test_phone_keyed_limit_falls_back_to_ip_on_unparseable_body(
        self, redis_client: Redis
    ) -> None:
        dependency = RateLimitDependency(limit=1, window_seconds=60, key_by="phone")
        await dependency(
            _make_request(client_host="7.7.7.7", body=b"not-json"),
            redis_client=redis_client,
        )
        with pytest.raises(RateLimitExceededError):
            await dependency(
                _make_request(client_host="7.7.7.7", body=b"not-json"),
                redis_client=redis_client,
            )
