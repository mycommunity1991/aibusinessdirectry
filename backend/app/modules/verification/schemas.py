from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.provider.models import ProviderType, VerificationStatus
from app.modules.verification.models import DocumentType, VerificationType


class VerificationPreviewResponse(BaseModel):
    """
    Response payload for `POST /providers/me/verification/documents/
    preview` -- the OCR stub's (always empty, Decision 6) candidate
    fields, presented as editable, provisional data ("what we read --
    please confirm"), never as already-verified fact (AC4).
    """

    document_type: DocumentType
    full_name: str | None = None
    id_number: str | None = None
    expiry_date: date | None = None
    confidence: float = Field(
        ..., description="Always `0.0` -- `StubDocumentOcrService` never guesses."
    )


class ConfirmedFieldsInput(BaseModel):
    """
    The user's final, possibly-edited values for `POST
    /providers/me/verification` (AC4/AC8) -- deliberately optional at
    every field, since even a real future OCR pipeline won't always
    extract every field, and no AC mandates these as required.
    """

    full_name: str | None = Field(None, max_length=200)
    id_number: str | None = Field(None, max_length=100)
    expiry_date: date | None = None


class SubmitVerificationRequest(BaseModel):
    """
    Request payload for `POST /providers/me/verification` (Decision 4).

    Deliberately has **no** `status`, `reviewed_at`, `reviewed_by`, or
    `rejection_reason` field anywhere -- there is no route through which
    a caller could even attempt to set them, making self-approval (AC6)
    structurally impossible, not just conventionally forbidden.
    """

    document_type: DocumentType | None = Field(
        None,
        description=(
            "Required for Freelancer (must be `emirates_id`); optional for "
            "Business, per `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED`."
        ),
    )
    confirmed_fields: ConfirmedFieldsInput | None = None


class VerificationDocumentResponse(BaseModel):
    """One document attached to a verification cycle, in an API response."""

    id: uuid.UUID
    document_type: DocumentType
    ocr_extracted_data: dict[str, str | None] | None = None
    file_download_url: str = Field(
        ...,
        description=(
            "Always this module's own authenticated streaming endpoint "
            "-- never a raw file path or public URL (Decision 7)."
        ),
    )


class VerificationRecordResponse(BaseModel):
    """Response payload for `GET /providers/me/verification` (AC6)."""

    id: uuid.UUID
    verification_type: VerificationType
    status: VerificationStatus
    submitted_at: datetime
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    documents: list[VerificationDocumentResponse] = Field(default_factory=list)


class AdminVerificationRecordResponse(BaseModel):
    """
    Response payload for the admin review surface (VER-002, AC1) --
    `GET /admin/verification/records` and the `approve`/`reject`
    responses. Unlike `VerificationRecordResponse` (the caller's own
    status view), this carries enough Provider context
    (`provider_id`/`provider_display_name`/`provider_type`) for an
    Admin acting across *every* provider's queue, and its documents'
    `file_download_url` points at the new admin-only download route
    (`/admin/verification/documents/{id}/file`), never the existing
    owner-only one.
    """

    id: uuid.UUID
    provider_id: uuid.UUID
    provider_display_name: str
    provider_type: ProviderType
    verification_type: VerificationType
    status: VerificationStatus
    submitted_at: datetime
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    documents: list[VerificationDocumentResponse] = Field(default_factory=list)


class RejectVerificationRequest(BaseModel):
    """
    Request payload for `POST /admin/verification/records/{record_id}/
    reject` (VER-002, AC3). `min_length=1` structurally enforces "requires
    a rejection_reason" -- a missing/empty reason 422s before the service
    layer ever runs; no redundant service-layer check is added for this.
    """

    rejection_reason: str = Field(..., min_length=1, max_length=2000)
