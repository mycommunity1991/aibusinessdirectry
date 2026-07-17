# Rule: Caching & Redis Patterns

## Redis Usage Standards
* **Async Client:** Strictly use an asynchronous Redis client (e.g., `redis.asyncio`) to prevent blocking the FastAPI event loop.
* **Namespace Isolation:** Prefix all Redis keys with their owning module and entity to prevent collisions (e.g., `auth:session:user_123`, `search:request_456:matches`).

## Caching Strategies
* **When to Cache:** Cache only heavily read, rarely updated data (e.g., public provider profiles, category taxonomy, configuration lists). Do not cache highly transactional data that requires strict consistency unless using explicit distributed locking.
* **Cache Invalidation:** Every cached item must have a clear invalidation strategy. Prefer event-driven invalidation (deleting the cache key when the source data updates) combined with a fallback Time-To-Live (TTL).
* **Zero Infinite TTLs:** Never store a cache key without a TTL. Every piece of cached data must eventually expire to prevent memory leaks and stale data persistence.

## Rate Limiting & Distributed State
* **API Rate Limiting:** Implement rate limiting at the API layer using Redis to track request counts against IP addresses or User IDs over time windows.
* **Distributed Locks:** If a background task or critical mutation must not run concurrently across multiple server instances, use Redis-based distributed locks (e.g., Redlock) to enforce single-threaded execution globally.