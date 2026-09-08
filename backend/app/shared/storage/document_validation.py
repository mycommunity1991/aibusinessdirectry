"""
Verification-document upload validation (VER-001, Decision 8,
`Plan_S05_VER-001.md`; `06_SECURITY.md` File Upload Security).

Deliberately a new, parallel module to `image_validation.py`, not a reuse
or in-place edit -- verification documents (Emirates ID scans, trade
licenses) need PDF support `image_validation.py` doesn't have, and AC3
explicitly requires a *specific, actionable* error per failure category,
the opposite of `image_validation.py`'s deliberately vague single error.
Only the underlying magic-byte signature checks (`file_signatures.py`)
are shared between the two.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import (
    VerificationDocumentInvalidTypeError,
    VerificationDocumentTooLargeError,
)
from app.modules.verification.models import DocumentType
from app.shared.storage.file_signatures import is_jpeg, is_pdf, is_png, is_webp

# `02_ARCHITECTURE.md`'s Dependency Rules explicitly permit "Infrastructure
# depends on Domain" -- `shared/storage` (infrastructure) importing the
# `DocumentType` value-enum from `modules/verification` (domain) is exactly
# this allowed direction, not a violation.

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

# Ordered (checker, safe extension, allowed declared `Content-Type` values)
# tuples -- the first match wins. The returned extension always comes from
# here (the *validated* detected type), never from the client's original
# filename (`06_SECURITY.md`: "Original filenames must never be trusted").
_DOCUMENT_SIGNATURES: list[tuple[Callable[[bytes], bool], str, frozenset[str]]] = [
    (is_jpeg, ".jpg", frozenset({"image/jpeg", "image/jpg"})),
    (is_png, ".png", frozenset({"image/png"})),
    (is_webp, ".webp", frozenset({"image/webp"})),
    (is_pdf, ".pdf", frozenset({"application/pdf"})),
]


async def validate_verification_document_upload(
    upload_file: UploadFile,
    *,
    document_type: DocumentType,
) -> tuple[bytes, str]:
    """
    Reads and validates an uploaded verification document (Emirates ID
    scan, trade license, etc.).

    `document_type` is accepted for interface symmetry with the caller
    (`VerificationService.preview_document`) and to leave room for a
    future per-type file-type restriction; today every `document_type`
    accepts the same allowed set (Decision 8, `Plan_S05_VER-001.md` --
    no AC asks for a narrower per-type allow-list), so it is not
    otherwise consulted here.

    Returns `(content, extension)` -- `extension` is the validated,
    detected type's safe extension (e.g. `.pdf`), never the client's
    original filename's extension.

    Raises a **distinct** exception per failure category (AC3's literal
    "specific, actionable error" requirement, the opposite of
    `image_validation.py`'s deliberately vague single error):
    - `VerificationDocumentTooLargeError` -- empty or over
      `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES`.
    - `VerificationDocumentInvalidTypeError` -- disallowed extension, or
      the content's magic bytes/declared `Content-Type` don't match any
      allowed signature (covers both "wrong extension" and "magic-byte
      mismatch").
    """
    content = await upload_file.read()

    if not content or len(content) > settings.MAX_VERIFICATION_DOCUMENT_SIZE_BYTES:
        raise VerificationDocumentTooLargeError()

    original_extension = Path(upload_file.filename or "").suffix.lower()
    if original_extension not in _ALLOWED_EXTENSIONS:
        raise VerificationDocumentInvalidTypeError()

    declared_content_type = (upload_file.content_type or "").lower()

    for is_match, safe_extension, allowed_content_types in _DOCUMENT_SIGNATURES:
        if is_match(content) and declared_content_type in allowed_content_types:
            return content, safe_extension

    raise VerificationDocumentInvalidTypeError()
