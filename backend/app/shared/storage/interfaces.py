"""
`FileStorage` protocol (PRO-002, Decision 2, `Plan_S04_PRO-002.md`;
extended VER-001, Decision 7, `Plan_S05_VER-001.md`).

A small, generic file-storage abstraction so `PortfolioService`/
`VerificationService` depend on a protocol, never a concrete storage
backend directly. Today's only implementation is `LocalFileStorage`
(`local_file_storage.py`); a future story can add `S3FileStorage` (once
real AWS credentials/bucket provisioning exist in this environment, per
`12_TECH_STACK.md`) by adding one new class and one dependency-wiring
change, with zero changes to `PortfolioService`/`VerificationService`
themselves.
"""

from typing import Protocol


class FileStorage(Protocol):
    """Storage-backend-agnostic file save/delete/read operations."""

    async def save(self, content: bytes, *, filename: str, subdirectory: str) -> str:
        """
        Persists `content` under a generated `filename` within
        `subdirectory`, and returns a reference to it -- a served,
        relative URL path (e.g. `/media/portfolios/{provider_id}/
        {filename}`) for a public-facing implementation, or a bare
        storage-relative reference (e.g. `verification/{provider_id}/
        {filename}`) for a private one (VER-001, Decision 7) -- never an
        absolute filesystem path either way (`06_SECURITY.md`: "never
        expose... server paths").
        """
        ...

    async def delete(self, url_path: str) -> None:
        """
        Removes the file previously returned by `save()`'s reference.
        Deliberately unused by `PortfolioService`'s `DELETE
        /providers/me/portfolio/{portfolio_id}` (Decision 5,
        `Plan_S04_PRO-002.md`: soft-delete only, file left in place) --
        provided for a future administrative/retention job. Used by
        `VerificationService` to clear the pending-slot file after a
        successful submit (VER-001, Decision 7).
        """
        ...

    async def read(self, url_path: str) -> bytes:
        """
        Reads back the raw bytes of the file previously returned by
        `save()`'s reference (VER-001, Decision 7). Additive -- added for
        `VerificationService`'s authenticated document-download and
        pending-slot-promotion needs; `PortfolioService` never calls this.
        """
        ...
