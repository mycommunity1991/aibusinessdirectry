"""
Verification submission -- preview, submit, status, document download
(VER-001).

Depends on `provider`'s existing `ProviderService.get_my_provider`
(Decision 9, `Plan_S05_VER-001.md`) -- a pure read, no write path into
any `provider`-schema table anywhere in this module (Decision 2). Also
depends on the `DocumentOcrService` Protocol (Decision 6) and the
private `FileStorage` instance (Decision 7) -- never the public,
portfolio-facing one.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile

from app.core.authorization import ensure_owner_or_not_found
from app.core.config import settings
from app.core.exceptions import (
    ProviderNotFoundError,
    VerificationDocumentNotFoundError,
    VerificationDocumentRequiredError,
    VerificationSubmissionNotAllowedError,
)
from app.modules.provider.models import Provider, ProviderType, VerificationStatus
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.models import (
    DocumentType,
    VerificationDocument,
    VerificationRecord,
    VerificationType,
)
from app.modules.verification.repositories.verification_document_repository import (
    VerificationDocumentRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)
from app.modules.verification.services.document_ocr_service import (
    DocumentOcrResult,
    DocumentOcrService,
)
from app.shared.storage.document_validation import validate_verification_document_upload
from app.shared.storage.interfaces import FileStorage

_PENDING_SUBDIRECTORY = "pending"
_PERMANENT_SUBDIRECTORY_ROOT = "verification"
# Bounded, small set -- mirrors `document_validation.py`'s own allowed
# extensions. Used only to *locate* an already-validated pending file at
# submit time (the extension isn't otherwise carried between the two
# calls); never used to accept a new, unvalidated extension.
_KNOWN_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".pdf")


class VerificationService:
    """Orchestrates a provider's document preview, submission, status
    lookup, and authenticated document download."""

    def __init__(
        self,
        provider_service: ProviderService,
        verification_record_repository: VerificationRecordRepository,
        verification_document_repository: VerificationDocumentRepository,
        verification_file_storage: FileStorage,
        document_ocr_service: DocumentOcrService,
    ) -> None:
        self.provider_service = provider_service
        self.verification_record_repository = verification_record_repository
        self.verification_document_repository = verification_document_repository
        self.verification_file_storage = verification_file_storage
        self.document_ocr_service = document_ocr_service

    async def preview_document(
        self,
        user_id: uuid.UUID,
        *,
        upload: UploadFile,
        document_type: DocumentType,
    ) -> DocumentOcrResult:
        """
        Validates the upload (Decision 8), runs the OCR stub (Decision
        6), and stashes the file at the caller's deterministic pending
        slot (Decision 7) -- `pending/{provider_id}{extension}`, always
        overwriting whatever was previously pending for this provider.
        Writes **no** database row (Decision 4).

        Clears every other known-extension pending slot first: since the
        extension isn't otherwise carried between `preview_document` and
        `submit` (see `_find_pending_file`), a second preview with a
        *different* file type (e.g. `.jpg` then `.pdf`) would otherwise
        leave the first file on disk, orphaned and ambiguous -- a later
        `submit` could pick up the stale file instead of the one the
        caller most recently previewed and confirmed. At most one
        pending file per provider exists at any time.
        """
        provider = await self._get_provider_or_404(user_id)

        content, extension = await validate_verification_document_upload(
            upload, document_type=document_type
        )
        ocr_result = await self.document_ocr_service.extract(
            content, document_type=document_type
        )

        for known_extension in _KNOWN_EXTENSIONS:
            if known_extension != extension:
                await self.verification_file_storage.delete(
                    f"{_PENDING_SUBDIRECTORY}/{provider.id}{known_extension}"
                )

        await self.verification_file_storage.save(
            content,
            filename=f"{provider.id}{extension}",
            subdirectory=_PENDING_SUBDIRECTORY,
        )

        return ocr_result

    async def submit(
        self,
        user_id: uuid.UUID,
        *,
        document_type: DocumentType | None,
        confirmed_fields: dict[str, Any] | None,
    ) -> VerificationRecord:
        """
        Resolves `verification_type`/document requirement from the
        caller's `provider_type` + config (Decision 3), rejects (409) if
        an active cycle already exists (Decision 4/AC7), and -- in one
        flush sequence -- creates the new `verification_records` row
        plus, if a document was involved, promotes the pending file to
        its permanent location and creates the matching
        `verification_documents` row. `ocr_extracted_data` is always the
        caller's **submitted** `confirmed_fields` (AC8), never the OCR
        stub's raw preview output.
        """
        provider = await self._get_provider_or_404(user_id)
        verification_type, document_required = self._resolve_requirements(provider)

        latest = await self.verification_record_repository.get_latest_for_provider(
            provider.id
        )
        if latest is not None and latest.status != VerificationStatus.REJECTED:
            raise VerificationSubmissionNotAllowedError()

        if document_required and document_type is None:
            raise VerificationDocumentRequiredError()
        if (
            provider.provider_type == ProviderType.FREELANCER
            and document_type is not None
            and document_type != DocumentType.EMIRATES_ID
        ):
            raise VerificationDocumentRequiredError()

        pending_file: tuple[bytes, str] | None = None
        if document_type is not None:
            pending_file = await self._find_pending_file(provider.id)
            if pending_file is None:
                raise VerificationDocumentRequiredError()

        record = await self.verification_record_repository.create(
            {
                "provider_id": provider.id,
                "verification_type": verification_type,
                "status": VerificationStatus.PENDING,
                "submitted_at": datetime.now(UTC),
            }
        )

        if pending_file is not None and document_type is not None:
            content, extension = pending_file
            generated_filename = f"{uuid.uuid4().hex}{extension}"
            file_url = await self.verification_file_storage.save(
                content,
                filename=generated_filename,
                subdirectory=(
                    f"{_PERMANENT_SUBDIRECTORY_ROOT}/{provider.id}/{record.id}"
                ),
            )
            await self.verification_file_storage.delete(
                f"{_PENDING_SUBDIRECTORY}/{provider.id}{extension}"
            )
            await self.verification_document_repository.create(
                {
                    "verification_record_id": record.id,
                    "document_type": document_type,
                    "file_url": file_url,
                    "ocr_extracted_data": confirmed_fields,
                }
            )

        return record

    async def get_my_current_status(
        self, user_id: uuid.UUID
    ) -> VerificationRecord | None:
        """
        The caller's latest verification cycle, or `None` (-> 404 at the
        API layer). Reads `verification_records` directly (Decision 2),
        never `providers.verification_status`.
        """
        provider = await self._get_provider_or_404(user_id)
        return await self.verification_record_repository.get_latest_for_provider(
            provider.id
        )

    async def get_documents_for_record(
        self, verification_record_id: uuid.UUID
    ) -> list[VerificationDocument]:
        """Lists a verification cycle's documents -- used by the API
        layer to build `GET /providers/me/verification`'s response."""
        return list(
            await self.verification_document_repository.list_for_record(
                verification_record_id
            )
        )

    async def get_document_bytes(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[bytes, DocumentType]:
        """
        Streams one of the caller's own document's raw bytes.
        `ensure_owner_or_not_found` (via the document -> parent record ->
        `provider_id` chain) is load-bearing here (ADR-015) -- the one
        genuinely `{id}`-addressable route in this module.
        """
        provider = await self._get_provider_or_404(user_id)

        document = await self.verification_document_repository.get_by_id(document_id)
        record = (
            await self.verification_record_repository.get_by_id(
                document.verification_record_id
            )
            if document is not None
            else None
        )
        ensure_owner_or_not_found(
            record.provider_id if record is not None else None,
            provider.id,
            not_found_exc=VerificationDocumentNotFoundError(),
        )
        assert document is not None  # narrows for type-checkers; guaranteed above

        content = await self.verification_file_storage.read(document.file_url)
        return content, document.document_type

    async def _get_provider_or_404(self, user_id: uuid.UUID) -> Provider:
        provider = await self.provider_service.get_my_provider(user_id)
        if provider is None:
            raise ProviderNotFoundError()
        return provider

    @staticmethod
    def _resolve_requirements(provider: Provider) -> tuple[VerificationType, bool]:
        """
        Derives `verification_type` and whether a document is required,
        from `provider.provider_type` + settings (Decision 3). Freelancer
        is never config-driven -- always `freelancer_id`, always
        required.
        """
        if provider.provider_type == ProviderType.FREELANCER:
            return VerificationType.FREELANCER_ID, True

        return (
            VerificationType(settings.BUSINESS_VERIFICATION_TYPE),
            settings.BUSINESS_VERIFICATION_DOCUMENT_REQUIRED,
        )

    async def _find_pending_file(
        self, provider_id: uuid.UUID
    ) -> tuple[bytes, str] | None:
        """
        Locates the caller's pending-slot file (Decision 7) by trying
        each allowed extension in turn -- the extension isn't otherwise
        known at submit time, since it isn't passed back and forth
        between `preview_document` and `submit`.
        """
        for extension in _KNOWN_EXTENSIONS:
            try:
                content = await self.verification_file_storage.read(
                    f"{_PENDING_SUBDIRECTORY}/{provider_id}{extension}"
                )
            except OSError:
                continue
            return content, extension
        return None
