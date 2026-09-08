"""
Admin-only verification review endpoints (VER-002) -- mounted at
`/admin/verification`, a new prefix alongside the existing
`/providers/me/verification` mount (untouched by this module).

`require_role(ROLE_ADMIN)` alone is every route's entire authorization
boundary (Decision 6, `Plan_S05_VER-002.md`) -- a genuinely new,
ownerless authorization shape distinct from every other `{id}`-
addressable route in this codebase: an Admin has no "own" verification
record to scope to, since every record belongs to some *other* user's
Provider.
"""

import math
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import API_PREFIX, API_V1, ROLE_ADMIN
from app.database.session import get_db
from app.modules.provider.models import Provider
from app.modules.verification.dependencies import get_admin_verification_service
from app.modules.verification.models import VerificationDocument, VerificationRecord
from app.modules.verification.schemas import (
    AdminVerificationRecordResponse,
    RejectVerificationRequest,
    VerificationDocumentResponse,
)
from app.modules.verification.services.admin_verification_service import (
    AdminVerificationService,
)
from app.shared.schemas.response import (
    CollectionResponse,
    PaginationMeta,
    SuccessResponse,
)
from app.shared.storage.file_signatures import is_jpeg, is_pdf, is_png, is_webp

router = APIRouter(tags=["Admin Verification"])

_ADMIN_DOWNLOAD_URL_PREFIX = f"{API_PREFIX}{API_V1}/admin/verification/documents"
_DEFAULT_PAGE_SIZE = 20


def _content_type_for(content: bytes) -> str:
    """Infers a `Content-Type` from the document's own validated magic
    bytes -- mirrors `verification/api.py`'s identical helper."""
    if is_jpeg(content):
        return "image/jpeg"
    if is_png(content):
        return "image/png"
    if is_webp(content):
        return "image/webp"
    if is_pdf(content):
        return "application/pdf"
    return "application/octet-stream"


def _to_admin_document_response(
    document: VerificationDocument,
) -> VerificationDocumentResponse:
    return VerificationDocumentResponse(
        id=document.id,
        document_type=document.document_type,
        ocr_extracted_data=document.ocr_extracted_data,
        file_download_url=f"{_ADMIN_DOWNLOAD_URL_PREFIX}/{document.id}/file",
    )


def _to_admin_record_response(
    record: VerificationRecord,
    provider: Provider,
    documents: list[VerificationDocument],
) -> AdminVerificationRecordResponse:
    return AdminVerificationRecordResponse(
        id=record.id,
        provider_id=record.provider_id,
        provider_display_name=provider.display_name,
        provider_type=provider.provider_type,
        verification_type=record.verification_type,
        status=record.status,
        submitted_at=record.submitted_at,
        reviewed_at=record.reviewed_at,
        rejection_reason=record.rejection_reason,
        documents=[_to_admin_document_response(document) for document in documents],
    )


@router.get(
    "/records",
    response_model=CollectionResponse[AdminVerificationRecordResponse],
    responses={
        200: {"description": "One page of the pending review queue."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
    },
    summary="List Verification Records Pending Review",
    description=(
        "Lists `pending`/`under_review` verification records (AC1), "
        "oldest `submitted_at` first, with each record's Provider "
        "context and documents. Paginated (this codebase's first real "
        "use of `CollectionResponse`/`PaginationMeta`) -- a genuinely "
        "shared, platform-wide, unbounded-growth collection. "
        "`require_role(ROLE_ADMIN)` is the entire authorization "
        "boundary (AC7); no ownership check applies."
    ),
)
async def list_verification_records(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_verification_service: AdminVerificationService = Depends(  # noqa: B008
        get_admin_verification_service
    ),
) -> CollectionResponse[AdminVerificationRecordResponse]:
    """Returns one page of the pending/under_review review queue."""
    (
        records,
        providers_by_id,
        documents_by_record_id,
        total,
    ) = await admin_verification_service.list_pending_for_review(
        page=page, page_size=page_size
    )
    data = [
        _to_admin_record_response(
            record,
            providers_by_id[record.provider_id],
            documents_by_record_id[record.id],
        )
        for record in records
    ]
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    await db.commit()
    return CollectionResponse[AdminVerificationRecordResponse](
        success=True,
        message="Verification records retrieved.",
        data=data,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/records/{record_id}/approve",
    response_model=SuccessResponse[AdminVerificationRecordResponse],
    responses={
        200: {"description": "The verification record was approved."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The verification record does not exist."},
        409: {
            "description": (
                "The record has already been approved or rejected by an earlier action."
            ),
        },
    },
    summary="Approve A Verification Record",
    description=(
        "Approves a `pending`/`under_review` record (AC2), atomically: "
        "the record's own status transition, the `providers` cache "
        "update (`is_discoverable=true` for both Freelancer and "
        "Business Providers, Decision 5), the `admin_action_log` write "
        "(AC6), and the notification send (AC5)."
    ),
)
async def approve_verification_record(
    record_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_verification_service: AdminVerificationService = Depends(  # noqa: B008
        get_admin_verification_service
    ),
) -> SuccessResponse[AdminVerificationRecordResponse]:
    """Approves the given verification record."""
    record = await admin_verification_service.approve(
        current_user.id, record_id=record_id
    )
    provider = await admin_verification_service.get_provider(record.provider_id)
    documents = await admin_verification_service.get_documents_for_record(record.id)
    response_data = _to_admin_record_response(record, provider, documents)
    await db.commit()
    return SuccessResponse[AdminVerificationRecordResponse](
        success=True,
        message="Verification approved.",
        data=response_data,
    )


@router.post(
    "/records/{record_id}/reject",
    response_model=SuccessResponse[AdminVerificationRecordResponse],
    responses={
        200: {"description": "The verification record was rejected."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The verification record does not exist."},
        409: {
            "description": (
                "The record has already been approved or rejected by an earlier action."
            ),
        },
        422: {"description": "`rejection_reason` is missing or empty."},
    },
    summary="Reject A Verification Record",
    description=(
        "Rejects a `pending`/`under_review` record with a required "
        "`rejection_reason` (AC3). `is_discoverable` is never set "
        "`true` here, unconditionally, for either Provider subtype."
    ),
)
async def reject_verification_record(
    record_id: uuid.UUID,
    payload: RejectVerificationRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_verification_service: AdminVerificationService = Depends(  # noqa: B008
        get_admin_verification_service
    ),
) -> SuccessResponse[AdminVerificationRecordResponse]:
    """Rejects the given verification record."""
    record = await admin_verification_service.reject(
        current_user.id,
        record_id=record_id,
        rejection_reason=payload.rejection_reason,
    )
    provider = await admin_verification_service.get_provider(record.provider_id)
    documents = await admin_verification_service.get_documents_for_record(record.id)
    response_data = _to_admin_record_response(record, provider, documents)
    await db.commit()
    return SuccessResponse[AdminVerificationRecordResponse](
        success=True,
        message="Verification rejected.",
        data=response_data,
    )


@router.get(
    "/documents/{document_id}/file",
    responses={
        200: {"description": "The raw file bytes of the requested document."},
        401: {"description": "Authentication required."},
        403: {"description": "The caller does not hold the Admin role."},
        404: {"description": "The document does not exist."},
    },
    summary="Download A Verification Document As An Admin",
    description=(
        "Streams a verification document's raw bytes for an Admin "
        "caller. A new **sibling** to the existing owner-only `GET "
        "/providers/me/verification/documents/{document_id}/file` -- "
        "not a modification of it. Deliberately has **no** ownership "
        "check of any kind (Decision 6): `require_role(ROLE_ADMIN)` is "
        "this route's entire authorization boundary, so an Admin can "
        "correctly fetch a document belonging to any provider."
    ),
)
async def download_verification_document_as_admin(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role(ROLE_ADMIN)),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin_verification_service: AdminVerificationService = Depends(  # noqa: B008
        get_admin_verification_service
    ),
) -> Response:
    """Streams the given document's raw bytes -- no ownership check."""
    (
        content,
        _document_type,
    ) = await admin_verification_service.get_document_bytes_for_admin(document_id)
    await db.commit()
    return Response(content=content, media_type=_content_type_for(content))
