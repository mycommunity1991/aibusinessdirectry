"""
`LocalFileStorage` (PRO-002, Decision 2, `Plan_S04_PRO-002.md`; extended
VER-001, Decision 7, `Plan_S05_VER-001.md`).

Writes uploaded files to a git-ignored local directory. Two independent
roots exist today: `UPLOAD_DIR` (default `uploads/`, public, served back
to clients via a `StaticFiles` mount at `/media` -- `app/main.py`) for
portfolio photos, and `VERIFICATION_UPLOAD_DIR` (default
`uploads_private/verification`, **never** mounted as static files) for
verification documents. Explicitly interim -- no AWS credentials/bucket
exist in this codebase or dev environment (`12_TECH_STACK.md` names AWS
as the approved cloud provider architecturally, but nothing has been
provisioned yet). Blocking filesystem calls are offloaded via
`asyncio.to_thread` so they never block the event loop.

`public_url_prefix` (VER-001, Decision 7): defaults to `"/media"`,
preserving the existing portfolio (`get_file_storage()`) wiring's exact
prior behavior -- zero regression for PRO-002. When constructed with
`public_url_prefix=None` (the new `get_verification_file_storage()`
wiring), `save()` returns a bare storage-relative reference instead of a
public URL -- a reference only ever meaningful to this backend itself,
never handed to a client as a clickable link.
"""

import asyncio
from pathlib import Path


class LocalFileStorage:
    """Concrete `FileStorage` implementation backed by the local filesystem."""

    def __init__(
        self,
        base_directory: str,
        public_url_prefix: str | None = "/media",
    ) -> None:
        self._base_directory = Path(base_directory)
        self._public_url_prefix = public_url_prefix

    async def save(self, content: bytes, *, filename: str, subdirectory: str) -> str:
        """
        Writes `content` to `{base_directory}/{subdirectory}/{filename}`.

        Returns the served, relative URL path
        `{public_url_prefix}/{subdirectory}/{filename}` when
        `public_url_prefix` is set (the default, portfolio-photo
        behavior); returns the bare, storage-relative reference
        `{subdirectory}/{filename}` when `public_url_prefix is None`
        (verification documents, Decision 7 -- never a public URL).
        """
        target_dir = self._base_directory / subdirectory
        target_path = target_dir / filename

        def _write() -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)

        await asyncio.to_thread(_write)

        relative_reference = f"{subdirectory}/{filename}"
        if self._public_url_prefix is None:
            return relative_reference
        return f"{self._public_url_prefix}/{relative_reference}"

    async def delete(self, url_path: str) -> None:
        """Removes the file at `url_path`, if present."""
        target_path = self._base_directory / self._relative_path(url_path)

        def _delete() -> None:
            target_path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)

    async def read(self, url_path: str) -> bytes:
        """Reads back the raw bytes at `url_path` (VER-001, Decision 7)."""
        target_path = self._base_directory / self._relative_path(url_path)

        def _read() -> bytes:
            return target_path.read_bytes()

        return await asyncio.to_thread(_read)

    def _relative_path(self, url_path: str) -> str:
        """
        Strips this instance's `public_url_prefix` (if any) from
        `url_path` to get the path relative to `base_directory` -- a
        small generalization of the previous hardcoded
        `removeprefix("/media/")` (Decision 7).
        """
        prefix = f"{self._public_url_prefix}/" if self._public_url_prefix else ""
        return url_path.removeprefix(prefix)
