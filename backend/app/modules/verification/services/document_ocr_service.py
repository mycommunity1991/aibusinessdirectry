"""
OCR extraction, stubbed (VER-001, Decision 6, `Plan_S05_VER-001.md`).

No OCR pipeline, external OCR SDK, or Ejari/Emirates-ID integration
exists anywhere in this codebase (confirmed by a repo-wide search at
planning time). This module builds the correct swappable *shape* for one
to be plugged in later -- the same pattern ADR-017 already established
for `FileStorage` -- rather than guessing at or partially reverse-
engineering a vendor integration that isn't present.

`StubDocumentOcrService` is the only implementation this story ships: it
**always** returns every field as `None`/`confidence=0.0`, regardless of
the file's actual content -- a genuine stub, not a "best-effort" one.
`VerificationService` depends on the `DocumentOcrService` Protocol, never
this concrete class, wired via `get_document_ocr_service()`
(`dependencies.py`) -- a future story can add a real implementation with
one new class and one wiring-line change.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.modules.verification.models import DocumentType


@dataclass(frozen=True)
class DocumentOcrResult:
    """
    Candidate fields an OCR pass extracted from a document -- always
    presented to the caller as provisional ("what we read -- please
    confirm"), never as already-verified fact (AC4).
    """

    full_name: str | None
    id_number: str | None
    expiry_date: date | None
    confidence: float


class DocumentOcrService(Protocol):
    """Swappable OCR-extraction abstraction (Decision 6)."""

    async def extract(
        self, content: bytes, *, document_type: DocumentType
    ) -> DocumentOcrResult:
        """Extracts candidate fields from a document's raw bytes."""
        ...


class StubDocumentOcrService:
    """
    The only `DocumentOcrService` implementation this story ships.

    Always returns an all-empty `DocumentOcrResult` regardless of the
    actual file content -- never attempts real text extraction, regex
    heuristics, or a third-party OCR call. Honest about the fact that
    nothing was actually read yet (Decision 6's mobile-UX note): the
    confirmation screen's fields are present and editable, just empty.
    """

    async def extract(
        self, content: bytes, *, document_type: DocumentType
    ) -> DocumentOcrResult:
        return DocumentOcrResult(
            full_name=None, id_number=None, expiry_date=None, confidence=0.0
        )
