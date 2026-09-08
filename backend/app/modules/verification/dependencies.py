"""Dependency-injection providers for the Verification module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.repositories.verification_document_repository import (
    VerificationDocumentRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)
from app.modules.verification.services.document_ocr_service import (
    DocumentOcrService,
    StubDocumentOcrService,
)
from app.modules.verification.services.verification_service import VerificationService
from app.shared.storage.interfaces import FileStorage
from app.shared.storage.local_file_storage import LocalFileStorage


def get_verification_record_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationRecordRepository:
    """Provides a `VerificationRecordRepository` bound to the
    request-scoped DB session."""
    return VerificationRecordRepository(db)


def get_verification_document_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationDocumentRepository:
    """Provides a `VerificationDocumentRepository` bound to the
    request-scoped DB session."""
    return VerificationDocumentRepository(db)


def get_verification_file_storage() -> FileStorage:
    """
    Provides the **private** `FileStorage` implementation for
    verification documents (VER-001, Decision 7, `Plan_S05_VER-001.md`)
    -- a genuinely separate root (`VERIFICATION_UPLOAD_DIR`) and
    `public_url_prefix=None`, so `save()` never returns a `/media/...`
    URL. Deliberately distinct from `provider.dependencies.get_file_
    storage()` (the existing public, portfolio-facing provider), which
    remains completely unchanged.
    """
    return LocalFileStorage(
        base_directory=settings.VERIFICATION_UPLOAD_DIR,
        public_url_prefix=None,
    )


def get_document_ocr_service() -> DocumentOcrService:
    """
    Provides the `DocumentOcrService` implementation (Decision 6) --
    `StubDocumentOcrService` today. `VerificationService` depends on the
    protocol, never this concrete class, so a future real OCR
    implementation needs only a change here.
    """
    return StubDocumentOcrService()


def get_verification_service(
    verification_record_repository: Annotated[
        VerificationRecordRepository, Depends(get_verification_record_repository)
    ],
    verification_document_repository: Annotated[
        VerificationDocumentRepository, Depends(get_verification_document_repository)
    ],
    verification_file_storage: Annotated[
        FileStorage, Depends(get_verification_file_storage)
    ],
    document_ocr_service: Annotated[
        DocumentOcrService, Depends(get_document_ocr_service)
    ],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> VerificationService:
    """
    Provides a `VerificationService` bound to the request-scoped DB
    session.

    Imports `get_provider_service` from `app.modules.provider.
    dependencies` (Decision 9, `Plan_S05_VER-001.md`) -- the same
    one-directional cross-module shape ADR-014/ADR-016 already
    established twice.
    """
    return VerificationService(
        provider_service=provider_service,
        verification_record_repository=verification_record_repository,
        verification_document_repository=verification_document_repository,
        verification_file_storage=verification_file_storage,
        document_ocr_service=document_ocr_service,
    )
