"""
`FileStorage` protocol (PRO-002, Decision 2, `Plan_S04_PRO-002.md`).

A small, generic file-storage abstraction so `PortfolioService` depends
on a protocol, never a concrete storage backend directly. Today's only
implementation is `LocalFileStorage` (`local_file_storage.py`); a future
story can add `S3FileStorage` (once real AWS credentials/bucket
provisioning exist in this environment, per `12_TECH_STACK.md`) by
adding one new class and one dependency-wiring change, with zero changes
to `PortfolioService` itself.
"""

from typing import Protocol


class FileStorage(Protocol):
    """Storage-backend-agnostic file save/delete operations."""

    async def save(self, content: bytes, *, filename: str, subdirectory: str) -> str:
        """
        Persists `content` under a generated `filename` within
        `subdirectory`, and returns a served, relative URL path (e.g.
        `/media/portfolios/{provider_id}/{filename}`) -- never an
        absolute filesystem path (`06_SECURITY.md`: "never expose...
        server paths").
        """
        ...

    async def delete(self, url_path: str) -> None:
        """
        Removes the file previously returned by `save()`'s URL path.
        Deliberately unused by this story's `DELETE
        /providers/me/portfolio/{portfolio_id}` (Decision 5,
        `Plan_S04_PRO-002.md`: soft-delete only, file left in place) --
        provided for a future administrative/retention job.
        """
        ...
