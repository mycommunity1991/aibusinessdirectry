"""
Shared, dependency-free magic-byte content sniffers (VER-001, Decision 8,
`Plan_S05_VER-001.md`).

Extracted out of `image_validation.py` (PRO-002) so both the portfolio-
photo validator and this story's new `document_validation.py` share the
same underlying signature checks, without coupling the two validation
*policies* (allowed types, size limits, exception types) together --
only the true common primitive (byte-signature sniffing) is shared. This
is a behavior-preserving extraction: `_is_jpeg`/`_is_png`/`_is_webp`'s
logic is unchanged from `image_validation.py`'s original inline
definitions. `_is_pdf` is new, added for this story's trade-license/
Emirates-ID-scan document support.
"""


def is_jpeg(content: bytes) -> bool:
    return content.startswith(b"\xff\xd8\xff")


def is_png(content: bytes) -> bool:
    return content.startswith(b"\x89PNG\r\n\x1a\n")


def is_webp(content: bytes) -> bool:
    return content[:4] == b"RIFF" and content[8:12] == b"WEBP"


def is_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-")
