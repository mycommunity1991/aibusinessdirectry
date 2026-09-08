"""
Unit tests for `validate_verification_document_upload` (VER-001,
Decision 8, `Plan_S05_VER-001.md`; `06_SECURITY.md` File Upload
Security).

AC3: each failure category raises its own, distinct, specific
exception -- never one generic, non-revealing message (the opposite of
`image_validation.py`'s deliberate vagueness).
"""

import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import (
    VerificationDocumentInvalidTypeError,
    VerificationDocumentTooLargeError,
)
from app.modules.verification.models import DocumentType
from app.shared.storage.document_validation import (
    validate_verification_document_upload,
)

_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32
_PDF_BYTES = b"%PDF-1.4\n" + b"\x00" * 32
_TEXT_BYTES = b"this is definitely not a document, just plain text padding." * 4


def _upload_file(
    content: bytes, *, filename: str, content_type: str | None
) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type else Headers({})
    return UploadFile(file=io.BytesIO(content), filename=filename, headers=headers)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestValidDocuments:
    """Correct extension + declared MIME type + matching magic bytes."""

    @pytest.mark.anyio
    async def test_valid_jpeg_passes(self) -> None:
        upload = _upload_file(_JPEG_BYTES, filename="id.jpg", content_type="image/jpeg")

        content, extension = await validate_verification_document_upload(
            upload, document_type=DocumentType.EMIRATES_ID
        )

        assert content == _JPEG_BYTES
        assert extension == ".jpg"

    @pytest.mark.anyio
    async def test_valid_png_passes(self) -> None:
        upload = _upload_file(_PNG_BYTES, filename="id.png", content_type="image/png")

        content, extension = await validate_verification_document_upload(
            upload, document_type=DocumentType.EMIRATES_ID
        )

        assert content == _PNG_BYTES
        assert extension == ".png"

    @pytest.mark.anyio
    async def test_valid_webp_passes(self) -> None:
        upload = _upload_file(
            _WEBP_BYTES, filename="id.webp", content_type="image/webp"
        )

        content, extension = await validate_verification_document_upload(
            upload, document_type=DocumentType.EMIRATES_ID
        )

        assert content == _WEBP_BYTES
        assert extension == ".webp"

    @pytest.mark.anyio
    async def test_valid_pdf_passes(self) -> None:
        """A trade license is plausibly a PDF, not a photo (Decision 8)."""
        upload = _upload_file(
            _PDF_BYTES, filename="trade-license.pdf", content_type="application/pdf"
        )

        content, extension = await validate_verification_document_upload(
            upload, document_type=DocumentType.TRADE_LICENSE
        )

        assert content == _PDF_BYTES
        assert extension == ".pdf"


class TestOversizedUpload:
    @pytest.mark.anyio
    async def test_oversized_upload_raises_the_size_specific_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "MAX_VERIFICATION_DOCUMENT_SIZE_BYTES", 10)
        upload = _upload_file(_JPEG_BYTES, filename="id.jpg", content_type="image/jpeg")

        with pytest.raises(VerificationDocumentTooLargeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.EMIRATES_ID
            )

    @pytest.mark.anyio
    async def test_empty_content_raises_the_size_specific_error(self) -> None:
        upload = _upload_file(b"", filename="id.jpg", content_type="image/jpeg")

        with pytest.raises(VerificationDocumentTooLargeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.EMIRATES_ID
            )


class TestDisallowedExtension:
    @pytest.mark.anyio
    async def test_disallowed_extension_raises_the_type_specific_error(self) -> None:
        upload = _upload_file(
            _JPEG_BYTES, filename="id.docx", content_type="image/jpeg"
        )

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.EMIRATES_ID
            )

    @pytest.mark.anyio
    async def test_missing_filename_raises_the_type_specific_error(self) -> None:
        upload = _upload_file(_JPEG_BYTES, filename="", content_type="image/jpeg")

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.EMIRATES_ID
            )


class TestMagicByteMismatch:
    @pytest.mark.anyio
    async def test_text_file_renamed_to_pdf_raises_the_type_specific_error(
        self,
    ) -> None:
        upload = _upload_file(
            _TEXT_BYTES,
            filename="not-a-license.pdf",
            content_type="application/pdf",
        )

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.TRADE_LICENSE
            )

    @pytest.mark.anyio
    async def test_png_bytes_declared_as_jpeg_raises_the_type_specific_error(
        self,
    ) -> None:
        upload = _upload_file(_PNG_BYTES, filename="id.jpg", content_type="image/jpeg")

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await validate_verification_document_upload(
                upload, document_type=DocumentType.EMIRATES_ID
            )


class TestErrorCategoriesAreDistinct:
    """AC3: size and type failures raise genuinely different exceptions,
    not one generic message."""

    def test_size_and_type_errors_are_different_exception_classes(self) -> None:
        too_large = VerificationDocumentTooLargeError
        invalid_type = VerificationDocumentInvalidTypeError
        assert too_large is not invalid_type
        assert not issubclass(
            VerificationDocumentTooLargeError, VerificationDocumentInvalidTypeError
        )
        assert not issubclass(
            VerificationDocumentInvalidTypeError, VerificationDocumentTooLargeError
        )
