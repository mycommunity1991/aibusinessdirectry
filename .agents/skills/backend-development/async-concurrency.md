# Rule: Async & Concurrency

## Async-First Execution
* **Event Loop Blocking:** Never use blocking I/O functions (e.g., `time.sleep()`, synchronous `requests`, synchronous file I/O) inside an `async def` function. This will halt the entire FastAPI event loop.
* **Proper Sleeping:** Always use `await asyncio.sleep()` for delays.
* **HTTP Clients:** Use asynchronous HTTP clients (like `httpx` or `aiohttp`) for external API calls. Never use the synchronous `requests` library.

## CPU-Bound Tasks
* **Thread Pools:** If you must perform a heavy CPU-bound task (e.g., image processing, heavy cryptography), offload it to a thread pool or process pool using `asyncio.to_thread()` or `run_in_executor()`. Do not run it directly in the main event loop.

## Background Tasks
* **FastAPI BackgroundTasks:** Use FastAPI's built-in `BackgroundTasks` only for lightweight, fire-and-forget operations (e.g., sending a quick metric). 
* **Worker Queues:** For critical or heavy background processing (e.g., sending batch emails, report generation), use a proper distributed task queue (like Celery or ARQ) backed by Redis.