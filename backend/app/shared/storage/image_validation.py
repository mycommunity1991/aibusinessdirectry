"""
Portfolio-photo upload validation (PRO-002, Decision 2,
`Plan_S04_PRO-002.md`; `06_SECURITY.md` File Upload Security).

Validates size, the original filename's extension (allow-list only --
never used to build the stored filename/path), and a dependency-free
magic-byte MIME sniff of the actual content -- deliberately not adding
Pillow or another imaging library, since no AC requires thumbnailing or
re-encoding, only validation.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import InvalidPortfolioUploadError

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _is_jpeg(content: bytes) -> bool:
    return content.startswith(b"\xff\xd8\xff")


def _is_png(content: bytes) -> bool:
    return content.startswith(b"\x89PNG\r\n\x1a\n")


def _is_webp(content: bytes) -> bool:
    return content[:4] == b"RIFF" and content[8:12] == b"WEBP"


# Ordered (checker, safe extension, allowed declared `Content-Type` values)
# tuples -- the first match wins. The returned extension always comes from
# here (the *validated* detected type), never from the client's original
# filename (`06_SECURITY.md`: "Original filenames must never be trusted").
_IMAGE_SIGNATURES: list[tuple[Callable[[bytes], bool], str, frozenset[str]]] = [
    (_is_jpeg, ".jpg", frozenset({"image/jpeg", "image/jpg"})),
    (_is_png, ".png", frozenset({"image/png"})),
    (_is_webp, ".webp", frozenset({"image/webp"})),
]


async def validate_image_upload(upload_file: UploadFile) -> tuple[bytes, str]:
    """
    Reads and validates an uploaded portfolio photo.

    Returns `(content, extension)` -- `extension` is the validated,
    detected type's safe extension (e.g. `.jpg`), never the client's
    original filename's extension.

    Raises `InvalidPortfolioUploadError` (422) on any failure -- size,
    extension, or MIME/magic-byte mismatch -- deliberately generic
    (mirrors `InvalidOtpError`'s non-revealing pattern) so the message
    never states exactly which check failed.
    """
    content = await upload_file.read()

    if not content or len(content) > settings.MAX_PORTFOLIO_PHOTO_SIZE_BYTES:
        raise InvalidPortfolioUploadError()

    original_extension = Path(upload_file.filename or "").suffix.lower()
    if original_extension not in _ALLOWED_EXTENSIONS:
        raise InvalidPortfolioUploadError()

    declared_content_type = (upload_file.content_type or "").lower()

    for is_match, safe_extension, allowed_content_types in _IMAGE_SIGNATURES:
        if is_match(content) and declared_content_type in allowed_content_types:
            return content, safe_extension

    raise InvalidPortfolioUploadError()
