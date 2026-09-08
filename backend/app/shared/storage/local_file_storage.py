"""
`LocalFileStorage` (PRO-002, Decision 2, `Plan_S04_PRO-002.md`).

Writes uploaded files to a git-ignored local directory (`UPLOAD_DIR`
setting, default `uploads/`), served back to clients via a
`StaticFiles` mount at `/media` (`app/main.py`). Explicitly interim --
no AWS credentials/bucket exist in this codebase or dev environment
(`12_TECH_STACK.md` names AWS as the approved cloud provider
architecturally, but nothing has been provisioned yet). Blocking
filesystem calls are offloaded via `asyncio.to_thread` so they never
block the event loop.
"""

import asyncio
from pathlib import Path


class LocalFileStorage:
    """Concrete `FileStorage` implementation backed by the local filesystem."""

    def __init__(self, base_directory: str) -> None:
        self._base_directory = Path(base_directory)

    async def save(self, content: bytes, *, filename: str, subdirectory: str) -> str:
        """
        Writes `content` to `{base_directory}/{subdirectory}/{filename}`
        and returns the served, relative URL path
        `/media/{subdirectory}/{filename}`.
        """
        target_dir = self._base_directory / subdirectory
        target_path = target_dir / filename

        def _write() -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)

        await asyncio.to_thread(_write)
        return f"/media/{subdirectory}/{filename}"

    async def delete(self, url_path: str) -> None:
        """Removes the file at `url_path` (relative to `/media`), if present."""
        relative = url_path.removeprefix("/media/")
        target_path = self._base_directory / relative

        def _delete() -> None:
            target_path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)
