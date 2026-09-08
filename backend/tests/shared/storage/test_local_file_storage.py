"""
Tests for `LocalFileStorage` (PRO-002, Decision 2, `Plan_S04_PRO-002.md`;
extended VER-001, Decision 7, `Plan_S05_VER-001.md`).

Covers the new `public_url_prefix`/`read()` behavior, plus a regression
guard confirming the existing portfolio-shaped (`public_url_prefix=
"/media"`, the default) behavior is completely unchanged -- zero
regression for PRO-002.
"""

from pathlib import Path

import pytest

from app.shared.storage.local_file_storage import LocalFileStorage

_CONTENT = b"some file bytes"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestPublicBehaviorUnchanged:
    """Regression guard (Decision 7): the default `public_url_prefix=
    "/media"` -- PRO-002's exact existing behavior -- is untouched."""

    @pytest.mark.anyio
    async def test_default_constructor_produces_a_media_url(
        self, tmp_path: Path
    ) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path))

        url = await storage.save(
            _CONTENT, filename="photo.jpg", subdirectory="portfolios/abc"
        )

        assert url == "/media/portfolios/abc/photo.jpg"
        assert (tmp_path / "portfolios/abc/photo.jpg").read_bytes() == _CONTENT

    @pytest.mark.anyio
    async def test_explicit_media_prefix_matches_the_default(
        self, tmp_path: Path
    ) -> None:
        storage = LocalFileStorage(
            base_directory=str(tmp_path), public_url_prefix="/media"
        )

        url = await storage.save(
            _CONTENT, filename="photo.jpg", subdirectory="portfolios/abc"
        )

        assert url == "/media/portfolios/abc/photo.jpg"

    @pytest.mark.anyio
    async def test_delete_with_the_public_prefix_removes_the_file(
        self, tmp_path: Path
    ) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path))
        url = await storage.save(
            _CONTENT, filename="photo.jpg", subdirectory="portfolios/abc"
        )
        assert (tmp_path / "portfolios/abc/photo.jpg").exists()

        await storage.delete(url)

        assert not (tmp_path / "portfolios/abc/photo.jpg").exists()


class TestPrivateBehavior:
    """VER-001, Decision 7: `public_url_prefix=None` never produces a
    `/media/...` URL, and `read()` round-trips what `save()` wrote."""

    @pytest.mark.anyio
    async def test_save_with_no_prefix_returns_a_bare_relative_reference(
        self, tmp_path: Path
    ) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path), public_url_prefix=None)

        reference = await storage.save(
            _CONTENT, filename="id.jpg", subdirectory="pending"
        )

        assert reference == "pending/id.jpg"
        assert "/media/" not in reference
        assert not reference.startswith("/")

    @pytest.mark.anyio
    async def test_read_round_trips_what_save_wrote(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path), public_url_prefix=None)
        reference = await storage.save(
            _CONTENT, filename="id.jpg", subdirectory="pending"
        )

        read_back = await storage.read(reference)

        assert read_back == _CONTENT

    @pytest.mark.anyio
    async def test_delete_with_no_prefix_removes_the_file(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path), public_url_prefix=None)
        reference = await storage.save(
            _CONTENT, filename="id.jpg", subdirectory="pending"
        )
        assert (tmp_path / "pending/id.jpg").exists()

        await storage.delete(reference)

        assert not (tmp_path / "pending/id.jpg").exists()

    @pytest.mark.anyio
    async def test_reading_a_missing_file_raises_os_error(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(base_directory=str(tmp_path), public_url_prefix=None)

        with pytest.raises(OSError):
            await storage.read("pending/does-not-exist.jpg")

    @pytest.mark.anyio
    async def test_saving_the_same_reference_twice_overwrites(
        self, tmp_path: Path
    ) -> None:
        """The pending-slot mechanic (VER-001, Decision 7) depends on a
        second `save()` to the same path overwriting the first."""
        storage = LocalFileStorage(base_directory=str(tmp_path), public_url_prefix=None)
        await storage.save(b"first", filename="id.jpg", subdirectory="pending")

        await storage.save(b"second", filename="id.jpg", subdirectory="pending")

        assert (tmp_path / "pending/id.jpg").read_bytes() == b"second"
