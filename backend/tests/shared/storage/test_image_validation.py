"""
Unit tests for `validate_image_upload` (PRO-002, Decision 2,
`Plan_S04_PRO-002.md`; `06_SECURITY.md` File Upload Security).
"""

import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import InvalidPortfolioUploadError
from app.shared.storage.image_validation import validate_image_upload

_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32
_TEXT_BYTES = b"this is definitely not an image, just plain text padding." * 4


def _upload_file(
    content: bytes, *, filename: str, content_type: str | None
) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type else Headers({})
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=headers)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestValidImages:
    """Correct extension + declared MIME type + matching magic bytes."""

    @pytest.mark.anyio
    async def test_valid_jpeg_passes(self) -> None:
        upload = _upload_file(
            _JPEG_BYTES, filename="photo.jpg", content_type="image/jpeg"
        )

        content, extension = await validate_image_upload(upload)

        assert content == _JPEG_BYTES
        assert extension == ".jpg"

    @pytest.mark.anyio
    async def test_valid_png_passes(self) -> None:
        upload = _upload_file(
            _PNG_BYTES, filename="photo.png", content_type="image/png"
        )

        content, extension = await validate_image_upload(upload)

        assert content == _PNG_BYTES
        assert extension == ".png"

    @pytest.mark.anyio
    async def test_valid_webp_passes(self) -> None:
        upload = _upload_file(
            _WEBP_BYTES, filename="photo.webp", content_type="image/webp"
        )

        content, extension = await validate_image_upload(upload)

        assert content == _WEBP_BYTES
        assert extension == ".webp"


class TestMagicByteMismatch:
    """AC2: a `.jpg`-named/declared file whose actual bytes are not a
    real image (or are a different image type) must be rejected."""

    @pytest.mark.anyio
    async def test_text_file_renamed_to_jpg_is_rejected(self) -> None:
        upload = _upload_file(
            _TEXT_BYTES, filename="not-a-photo.jpg", content_type="image/jpeg"
        )

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)

    @pytest.mark.anyio
    async def test_png_bytes_declared_as_jpeg_is_rejected(self) -> None:
        """Extension/declared-type say JPEG, actual content is PNG --
        the magic-byte sniff must not be fooled by the declared type."""
        upload = _upload_file(
            _PNG_BYTES, filename="photo.jpg", content_type="image/jpeg"
        )

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)


class TestOversizedUpload:
    @pytest.mark.anyio
    async def test_oversized_upload_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_PORTFOLIO_PHOTO_SIZE_BYTES", 10)
        upload = _upload_file(
            _JPEG_BYTES, filename="photo.jpg", content_type="image/jpeg"
        )

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)


class TestDisallowedExtension:
    @pytest.mark.anyio
    async def test_svg_extension_is_rejected_regardless_of_content(self) -> None:
        upload = _upload_file(
            _JPEG_BYTES, filename="photo.svg", content_type="image/svg+xml"
        )

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)

    @pytest.mark.anyio
    async def test_exe_extension_is_rejected_regardless_of_content(self) -> None:
        upload = _upload_file(
            _JPEG_BYTES, filename="photo.exe", content_type="application/octet-stream"
        )

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)

    @pytest.mark.anyio
    async def test_missing_filename_is_rejected(self) -> None:
        upload = _upload_file(_JPEG_BYTES, filename="", content_type="image/jpeg")

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)


class TestEmptyUpload:
    @pytest.mark.anyio
    async def test_empty_content_is_rejected(self) -> None:
        upload = _upload_file(b"", filename="photo.jpg", content_type="image/jpeg")

        with pytest.raises(InvalidPortfolioUploadError):
            await validate_image_upload(upload)
