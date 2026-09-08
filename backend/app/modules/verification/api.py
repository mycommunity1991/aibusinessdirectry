import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.core.constants import API_PREFIX, API_V1
from app.core.exceptions import VerificationRecordNotFoundError
from app.database.session import get_db
from app.modules.verification.dependencies import get_verification_service
from app.modules.verification.models import (
    DocumentType,
    VerificationDocument,
    VerificationRecord,
)
from app.modules.verification.schemas import (
    SubmitVerificationRequest,
    VerificationDocumentResponse,
    VerificationPreviewResponse,
    VerificationRecordResponse,
)
from app.modules.verification.services.document_ocr_service import DocumentOcrResult
from app.modules.verification.services.verification_service import VerificationService
from app.shared.schemas.response import SuccessResponse
from app.shared.storage.file_signatures import is_jpeg, is_pdf, is_png, is_webp

router = APIRouter(tags=["Verification"])

_DOWNLOAD_URL_PREFIX = f"{API_PREFIX}{API_V1}/providers/me/verification/documents"


def _content_type_for(content: bytes) -> str:
    """
    Infers a `Content-Type` from the document's own validated magic
    bytes (never from a client-supplied, spoofable value) -- there is no
    need to separately persist the original extension since the same
    signature checks `document_validation.py` already used at upload
    time are reused here.
    """
    if is_jpeg(content):
        return "image/jpeg"
    if is_png(content):
        return "image/png"
    if is_webp(content):
        return "image/webp"
    if is_pdf(content):
        return "application/pdf"
    return "application/octet-stream"


def _to_preview_response(
    document_type: DocumentType, ocr_result: DocumentOcrResult
) -> VerificationPreviewResponse:
    return VerificationPreviewResponse(
        document_type=document_type,
        full_name=ocr_result.full_name,
        id_number=ocr_result.id_number,
        expiry_date=ocr_result.expiry_date,
        confidence=ocr_result.confidence,
    )


def _to_document_response(
    document: VerificationDocument,
) -> VerificationDocumentResponse:
    return VerificationDocumentResponse(
        id=document.id,
        document_type=document.document_type,
        ocr_extracted_data=document.ocr_extracted_data,
        file_download_url=f"{_DOWNLOAD_URL_PREFIX}/{document.id}/file",
    )


def _to_record_response(
    record: VerificationRecord, documents: list[VerificationDocument]
) -> VerificationRecordResponse:
    return VerificationRecordResponse(
        id=record.id,
        verification_type=record.verification_type,
        status=record.status,
        submitted_at=record.submitted_at,
        reviewed_at=record.reviewed_at,
        rejection_reason=record.rejection_reason,
        documents=[_to_document_response(document) for document in documents],
    )


@router.post(
    "/documents/preview",
    response_model=SuccessResponse[VerificationPreviewResponse],
    responses={
        200: {"description": "The document was validated and stashed for review."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        422: {"description": "The uploaded document failed validation."},
    },
    summary="Preview A Verification Document",
    description=(
        "Validates an uploaded verification document (Emirates ID scan, "
        "trade license, etc. -- VER-001, AC3), runs the (stubbed, "
        "Decision 6) OCR pass, and stashes the file at the caller's "
        "private, deterministic pending slot (Decision 7) -- overwriting "
        "any previously-previewed file for this provider. Writes **no** "
        "database row (Decision 4); the returned fields are always "
        "empty/`None` today (the OCR pipeline is stubbed) and must be "
        "presented as editable, provisional data, not fact (AC4)."
    ),
)
async def preview_verification_document(
    file: UploadFile = File(...),  # noqa: B008
    document_type: DocumentType = Form(...),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    verification_service: VerificationService = Depends(  # noqa: B008
        get_verification_service
    ),
) -> SuccessResponse[VerificationPreviewResponse]:
    """Validate an uploaded document and stash it at the caller's pending slot."""
    ocr_result = await verification_service.preview_document(
        current_user.id, upload=file, document_type=document_type
    )
    response_data = _to_preview_response(document_type, ocr_result)
    await db.commit()
    return SuccessResponse[VerificationPreviewResponse](
        success=True,
        message="Document validated.",
        data=response_data,
    )


@router.post(
    "",
    response_model=SuccessResponse[VerificationRecordResponse],
    status_code=201,
    responses={
        201: {"description": "The verification submission was created."},
        401: {"description": "Authentication required."},
        404: {"description": "The caller has not created a provider listing yet."},
        409: {
            "description": (
                "The caller already has an active (pending/under_review/"
                "approved) verification cycle."
            ),
        },
        422: {
            "description": (
                "A document is required (Freelancer, always; Business, per "
                "config) but no pending-slot file was found, or the "
                "submitted `document_type` doesn't satisfy the requirement."
            ),
        },
    },
    summary="Submit My Verification",
    description=(
        "Creates a new `verification_records` row (`status=pending`, "
        "AC5) from the caller's own `provider_type` + config (Decision "
        "3/AC2), and, if a document was previewed, promotes the pending "
        "file to its permanent, cycle-specific location (Decision 7). "
        "`ocr_extracted_data` is always the caller's **submitted** "
        "`confirmed_fields` -- never the OCR stub's raw preview output "
        "(AC8). Always **creates** a new row, never updates an existing "
        "one, so resubmission after a rejection preserves history by "
        "construction (AC7). Never reads or writes "
        "`providers.verification_status`/`is_discoverable` (AC5/Decision "
        "2). No `status`/`reviewed_*`/`rejection_reason` field exists on "
        "this request at all (AC6)."
    ),
)
async def submit_verification(
    payload: SubmitVerificationRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    verification_service: VerificationService = Depends(  # noqa: B008
        get_verification_service
    ),
) -> SuccessResponse[VerificationRecordResponse]:
    """Submit a new verification cycle for the caller."""
    confirmed_fields = (
        payload.confirmed_fields.model_dump(mode="json")
        if payload.confirmed_fields is not None
        else None
    )
    record = await verification_service.submit(
        current_user.id,
        document_type=payload.document_type,
        confirmed_fields=confirmed_fields,
    )
    documents = await verification_service.get_documents_for_record(record.id)
    response_data = _to_record_response(record, documents)
    await db.commit()
    return SuccessResponse[VerificationRecordResponse](
        success=True,
        message="Verification submitted.",
        data=response_data,
    )


@router.get(
    "",
    response_model=SuccessResponse[VerificationRecordResponse],
    responses={
        200: {"description": "The caller's own latest verification cycle."},
        401: {"description": "Authentication required."},
        404: {
            "description": (
                "The caller has not created a provider listing yet, or has "
                "never submitted a verification cycle."
            ),
        },
    },
    summary="Get My Verification Status",
    description=(
        "Returns the caller's own single latest `verification_records` "
        "row plus its documents (AC6), ordered by `submitted_at` "
        "descending. Reads `verification_records` directly -- **never** "
        "`providers.verification_status` (Decision 2), so a fresh "
        "resubmission is never masked by a stale cached status."
    ),
)
async def get_my_verification_status(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    verification_service: VerificationService = Depends(  # noqa: B008
        get_verification_service
    ),
) -> SuccessResponse[VerificationRecordResponse]:
    """Return the caller's own latest verification cycle, or 404."""
    record = await verification_service.get_my_current_status(current_user.id)
    if record is None:
        raise VerificationRecordNotFoundError()

    documents = await verification_service.get_documents_for_record(record.id)
    response_data = _to_record_response(record, documents)
    await db.commit()
    return SuccessResponse[VerificationRecordResponse](
        success=True,
        message="Verification status retrieved.",
        data=response_data,
    )


@router.get(
    "/documents/{document_id}/file",
    responses={
        200: {"description": "The raw file bytes of the caller's own document."},
        401: {"description": "Authentication required."},
        404: {
            "description": (
                "The document either doesn't exist or is not owned by the "
                "caller -- both collapse into the same 404."
            ),
        },
    },
    summary="Download My Verification Document",
    description=(
        "Streams one of the caller's own verification document's raw "
        "bytes (Decision 7) -- **never** served through the public "
        "`/media` mount. Genuinely `{id}`-addressable, so "
        "`ensure_owner_or_not_found` (via the document -> parent record "
        "-> `provider_id` chain) is load-bearing here (ADR-015)."
    ),
)
async def download_verification_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    verification_service: VerificationService = Depends(  # noqa: B008
        get_verification_service
    ),
) -> Response:
    """Stream one of the caller's own document's raw bytes."""
    content, _document_type = await verification_service.get_document_bytes(
        current_user.id, document_id
    )
    await db.commit()
    return Response(content=content, media_type=_content_type_for(content))
