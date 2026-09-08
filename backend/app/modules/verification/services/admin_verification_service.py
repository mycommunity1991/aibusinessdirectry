"""
Admin-facing verification review orchestration (VER-002).

A deliberately **separate** class from the existing, provider-facing
`VerificationService` (`verification_service.py`) -- different
authorization model (`require_role(ROLE_ADMIN)` only, Decision 6,
`Plan_S05_VER-002.md`, no ownership check of any kind), different
callers, and different side effects (writes into `provider`,
`administration`, `notification`, none of which `VerificationService`
ever touches). Single Responsibility, not a God class (Decision 7).

`approve`/`reject` each do all of their work -- the `verification_
records` status transition, the `providers` cache update
(`ProviderService.apply_verification_outcome`), the `admin_action_log`
write, and the `notifications` write -- on the same request-scoped
`AsyncSession`, flush only, never a nested commit (Decision 4): the
API layer's single `await db.commit()` remains the only transaction
boundary, so every write lands together or none do.
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    ProviderNotFoundError,
    VerificationDocumentNotFoundError,
    VerificationRecordNotActionableError,
    VerificationRecordNotFoundError,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.notification.services.notification_service import NotificationService
from app.modules.provider.models import Provider, VerificationStatus
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.models import (
    DocumentType,
    VerificationDocument,
    VerificationRecord,
)
from app.modules.verification.repositories.verification_document_repository import (
    VerificationDocumentRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)
from app.shared.storage.interfaces import FileStorage


class AdminVerificationService:
    """
    Orchestrates an Admin's review queue, approve/reject actions, and
    document download. `require_role(ROLE_ADMIN)` at the API layer is
    this surface's entire authorization boundary (Decision 6) -- no
    ownership check of any kind applies anywhere in this class.
    """

    def __init__(
        self,
        verification_record_repository: VerificationRecordRepository,
        verification_document_repository: VerificationDocumentRepository,
        provider_service: ProviderService,
        admin_action_log_service: AdminActionLogService,
        notification_service: NotificationService,
        verification_file_storage: FileStorage,
    ) -> None:
        self.verification_record_repository = verification_record_repository
        self.verification_document_repository = verification_document_repository
        self.provider_service = provider_service
        self.admin_action_log_service = admin_action_log_service
        self.notification_service = notification_service
        self.verification_file_storage = verification_file_storage

    async def list_pending_for_review(
        self, *, page: int, page_size: int
    ) -> tuple[
        list[VerificationRecord],
        dict[uuid.UUID, Provider],
        dict[uuid.UUID, list[VerificationDocument]],
        int,
    ]:
        """
        Returns one page of `pending`/`under_review` records (oldest
        first, AC1), plus batch-fetched Provider context (Decision 9 --
        exactly one `list_by_ids` query for the whole page, never one
        query per record) and each record's documents, plus the total
        count for `PaginationMeta`.
        """
        offset = (page - 1) * page_size
        records, total = await self.verification_record_repository.list_for_review(
            offset=offset, limit=page_size
        )

        provider_ids = list({record.provider_id for record in records})
        providers = await self.provider_service.list_by_ids(provider_ids)
        providers_by_id = {provider.id: provider for provider in providers}

        documents_by_record_id: dict[uuid.UUID, list[VerificationDocument]] = {}
        for record in records:
            documents_by_record_id[record.id] = await self.get_documents_for_record(
                record.id
            )

        return records, providers_by_id, documents_by_record_id, total

    async def get_provider(self, provider_id: uuid.UUID) -> Provider:
        """
        Single-Provider lookup, reused from the batch `list_by_ids` path
        (Decision 9) -- used by the API layer to build the response
        after `approve`/`reject`.
        """
        providers = await self.provider_service.list_by_ids([provider_id])
        if not providers:
            raise ProviderNotFoundError()
        return providers[0]

    async def get_documents_for_record(
        self, verification_record_id: uuid.UUID
    ) -> list[VerificationDocument]:
        """Lists a verification cycle's documents -- used to build both
        the review-queue listing and the post-action response."""
        return list(
            await self.verification_document_repository.list_for_record(
                verification_record_id
            )
        )

    async def approve(
        self, admin_user_id: uuid.UUID, *, record_id: uuid.UUID
    ) -> VerificationRecord:
        """
        Approves a `pending`/`under_review` record (AC2), atomically:
        the record's own status transition, the `providers` cache
        update (`is_discoverable=True` for **both** Freelancer and
        Business Providers, Decision 5), the `admin_action_log` write
        (AC6), and the notification send (AC5).
        """
        record = await self._claim_record_or_raise(
            record_id,
            new_status=VerificationStatus.APPROVED,
            reviewed_by=admin_user_id,
        )

        provider = await self.provider_service.apply_verification_outcome(
            record.provider_id,
            verification_status=VerificationStatus.APPROVED,
            is_discoverable=True,
        )

        await self.admin_action_log_service.record_verification_review(
            admin_user_id=admin_user_id,
            verification_record_id=record.id,
            provider_id=record.provider_id,
            decision="approved",
            rejection_reason=None,
        )
        await self._notify(provider, record, approved=True, rejection_reason=None)

        return record

    async def reject(
        self,
        admin_user_id: uuid.UUID,
        *,
        record_id: uuid.UUID,
        rejection_reason: str,
    ) -> VerificationRecord:
        """
        Rejects a `pending`/`under_review` record (AC3). `is_discoverable`
        is **never** set `True` here, unconditionally -- both subtypes.
        """
        record = await self._claim_record_or_raise(
            record_id,
            new_status=VerificationStatus.REJECTED,
            reviewed_by=admin_user_id,
            rejection_reason=rejection_reason,
        )

        provider = await self.provider_service.apply_verification_outcome(
            record.provider_id,
            verification_status=VerificationStatus.REJECTED,
            is_discoverable=False,
        )

        await self.admin_action_log_service.record_verification_review(
            admin_user_id=admin_user_id,
            verification_record_id=record.id,
            provider_id=record.provider_id,
            decision="rejected",
            rejection_reason=rejection_reason,
        )
        await self._notify(
            provider, record, approved=False, rejection_reason=rejection_reason
        )

        return record

    async def get_document_bytes_for_admin(
        self, document_id: uuid.UUID
    ) -> tuple[bytes, DocumentType]:
        """
        Streams a document's raw bytes for an Admin caller -- **no**
        ownership check of any kind (Decision 6): `require_role
        (ROLE_ADMIN)` at the API layer is this route's entire
        authorization boundary. Deliberately does not call
        `ensure_owner_or_not_found` -- unlike `VerificationService.
        get_document_bytes`, that check would be wrong here.
        """
        document = await self.verification_document_repository.get_by_id(document_id)
        if document is None:
            raise VerificationDocumentNotFoundError()

        content = await self.verification_file_storage.read(document.file_url)
        return content, document.document_type

    async def _notify(
        self,
        provider: Provider,
        record: VerificationRecord,
        *,
        approved: bool,
        rejection_reason: str | None,
    ) -> None:
        # Guaranteed non-null in practice: a provider with an active
        # verification cycle was always created by its own owning
        # account (`ProviderService.create_provider` always sets
        # `user_id`) -- the nullable column exists only for a future,
        # unrelated Google-seeded-unclaimed-listing path.
        assert provider.user_id is not None
        await self.notification_service.notify_verification_status_change(
            user_id=provider.user_id,
            approved=approved,
            rejection_reason=rejection_reason,
            verification_record_id=record.id,
        )

    async def _claim_record_or_raise(
        self,
        record_id: uuid.UUID,
        *,
        new_status: VerificationStatus,
        reviewed_by: uuid.UUID,
        rejection_reason: str | None = None,
    ) -> VerificationRecord:
        """
        Looks up the record (404 if it doesn't exist at all), then
        atomically claims it via `try_claim_for_review` -- a single
        conditional `UPDATE` that only succeeds if the record is still
        `pending`/`under_review` at the moment it executes, closing the
        read-then-write race window a plain fetch-then-update would
        leave open between two concurrent admin actions on the same
        record (AC6/AC8's "exactly one" guarantee). Raises 409 if the
        claim is lost (already reviewed by this call or a concurrent
        one), and refreshes `record` in place so its Python attributes
        reflect the just-applied transition before returning it.
        """
        record = await self.verification_record_repository.get_by_id(record_id)
        if record is None:
            raise VerificationRecordNotFoundError()

        claimed = await self.verification_record_repository.try_claim_for_review(
            record_id,
            new_status=new_status,
            reviewed_by=reviewed_by,
            reviewed_at=datetime.now(UTC),
            rejection_reason=rejection_reason,
        )
        if not claimed:
            raise VerificationRecordNotActionableError()

        await self.verification_record_repository.session.refresh(record)
        return record
