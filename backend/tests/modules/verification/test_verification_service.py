"""
Integration tests for `VerificationService` (VER-001), exercised against
a real Postgres database and a real `LocalFileStorage` (private,
`public_url_prefix=None`) writing to a temporary directory.
"""

import io
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.exceptions import (
    ProviderNotFoundError,
    VerificationDocumentInvalidTypeError,
    VerificationDocumentRequiredError,
    VerificationDocumentTooLargeError,
    VerificationSubmissionNotAllowedError,
)
from app.modules.identity.models import AuthProvider, User
from app.modules.identity.repositories.role_repository import RoleRepository
from app.modules.identity.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.modules.provider.models import (
    ListingSource,
    Provider,
    ProviderType,
    VerificationStatus,
)
from app.modules.provider.repositories.business_profile_repository import (
    BusinessProfileRepository,
)
from app.modules.provider.repositories.freelancer_profile_repository import (
    FreelancerProfileRepository,
)
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.services.provider_service import ProviderService
from app.modules.verification.models import DocumentType, VerificationType
from app.modules.verification.repositories.verification_document_repository import (
    VerificationDocumentRepository,
)
from app.modules.verification.repositories.verification_record_repository import (
    VerificationRecordRepository,
)
from app.modules.verification.services.document_ocr_service import (
    StubDocumentOcrService,
)
from app.modules.verification.services.verification_service import VerificationService
from app.shared.storage.local_file_storage import LocalFileStorage

_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PDF_BYTES = b"%PDF-1.4" + b"\x00" * 32


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_provider(db_session, user: User, **overrides: object) -> Provider:
    payload: dict[str, object] = {
        "user_id": user.id,
        "provider_type": ProviderType.FREELANCER,
        "display_name": "Jane the Plumber",
        "slug": f"jane-the-plumber-{uuid.uuid4().hex[:8]}",
        "listing_source": ListingSource.SELF_REGISTERED,
        "is_claimed": True,
        "verification_status": VerificationStatus.PENDING,
        "is_discoverable": False,
        "review_count": 0,
        "country_code": "AE",
    }
    payload.update(overrides)
    provider = Provider(**payload)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


def _provider_service(db_session) -> ProviderService:
    return ProviderService(
        provider_repository=ProviderRepository(db_session),
        business_profile_repository=BusinessProfileRepository(db_session),
        freelancer_profile_repository=FreelancerProfileRepository(db_session),
        provider_category_label_repository=ProviderCategoryLabelRepository(db_session),
        service_area_repository=ServiceAreaRepository(db_session),
        role_assignment_service=RoleAssignmentService(RoleRepository(db_session)),
    )


def _verification_service(db_session, upload_dir: Path) -> VerificationService:
    return VerificationService(
        provider_service=_provider_service(db_session),
        verification_record_repository=VerificationRecordRepository(db_session),
        verification_document_repository=VerificationDocumentRepository(db_session),
        verification_file_storage=LocalFileStorage(
            base_directory=str(upload_dir), public_url_prefix=None
        ),
        document_ocr_service=StubDocumentOcrService(),
    )


def _upload(
    *,
    filename: str = "emirates-id.jpg",
    content: bytes = _JPEG_BYTES,
    content_type: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestPreviewDocument:
    @pytest.mark.anyio
    async def test_preview_rejects_oversized_upload_with_the_size_specific_error(
        self, db_session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "MAX_VERIFICATION_DOCUMENT_SIZE_BYTES", 10)
        user = await _create_user(db_session, "601000001")
        await _create_provider(db_session, user)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentTooLargeError):
            await service.preview_document(
                user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
            )

    @pytest.mark.anyio
    async def test_preview_rejects_wrong_extension_with_the_type_specific_error(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "601000002")
        await _create_provider(db_session, user)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await service.preview_document(
                user.id,
                upload=_upload(filename="id.docx"),
                document_type=DocumentType.EMIRATES_ID,
            )

    @pytest.mark.anyio
    async def test_preview_rejects_magic_byte_mismatch_with_the_type_specific_error(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "601000003")
        await _create_provider(db_session, user)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentInvalidTypeError):
            await service.preview_document(
                user.id,
                upload=_upload(content=b"not a real image, just text padding" * 4),
                document_type=DocumentType.EMIRATES_ID,
            )

    @pytest.mark.anyio
    async def test_preview_writes_no_database_row(
        self, db_session, tmp_path: Path
    ) -> None:
        """Decision 4: preview is a validate-and-stash-the-file step only."""
        user = await _create_user(db_session, "601000004")
        await _create_provider(db_session, user)
        service = _verification_service(db_session, tmp_path)

        await service.preview_document(
            user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
        )

        assert await service.get_my_current_status(user.id) is None

    @pytest.mark.anyio
    async def test_preview_returns_the_stub_ocr_result_always_empty(
        self, db_session, tmp_path: Path
    ) -> None:
        """Decision 6: the OCR stub always returns empty fields,
        regardless of the actual file content."""
        user = await _create_user(db_session, "601000005")
        await _create_provider(db_session, user)
        service = _verification_service(db_session, tmp_path)

        result = await service.preview_document(
            user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
        )

        assert result.full_name is None
        assert result.id_number is None
        assert result.expiry_date is None
        assert result.confidence == 0.0

    @pytest.mark.anyio
    async def test_preview_without_a_provider_raises_not_found(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "601000006")
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(ProviderNotFoundError):
            await service.preview_document(
                user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
            )


class TestSubmitFreelancer:
    @pytest.mark.anyio
    async def test_freelancer_without_a_document_is_rejected(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC2: Freelancer must submit an Emirates-ID-equivalent document."""
        user = await _create_user(db_session, "602000001")
        await _create_provider(db_session, user, provider_type=ProviderType.FREELANCER)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentRequiredError):
            await service.submit(user.id, document_type=None, confirmed_fields=None)

    @pytest.mark.anyio
    async def test_freelancer_with_wrong_document_type_is_rejected(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC2: Freelancer's accepted `document_type` is restricted to
        `emirates_id` only."""
        user = await _create_user(db_session, "602000002")
        await _create_provider(db_session, user, provider_type=ProviderType.FREELANCER)
        service = _verification_service(db_session, tmp_path)
        await service.preview_document(
            user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
        )

        with pytest.raises(VerificationDocumentRequiredError):
            await service.submit(
                user.id,
                document_type=DocumentType.TRADE_LICENSE,
                confirmed_fields=None,
            )

    @pytest.mark.anyio
    async def test_freelancer_without_a_preceding_preview_is_rejected(
        self, db_session, tmp_path: Path
    ) -> None:
        """`document_type=emirates_id` alone isn't enough -- the pending-
        slot file must actually exist (i.e. `preview` was called first)."""
        user = await _create_user(db_session, "602000003")
        await _create_provider(db_session, user, provider_type=ProviderType.FREELANCER)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentRequiredError):
            await service.submit(
                user.id,
                document_type=DocumentType.EMIRATES_ID,
                confirmed_fields=None,
            )

    @pytest.mark.anyio
    async def test_freelancer_happy_path_creates_a_pending_record_and_document(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "602000004")
        provider = await _create_provider(
            db_session, user, provider_type=ProviderType.FREELANCER
        )
        service = _verification_service(db_session, tmp_path)
        await service.preview_document(
            user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
        )

        record = await service.submit(
            user.id,
            document_type=DocumentType.EMIRATES_ID,
            confirmed_fields={"full_name": "Jane Doe"},
        )

        assert record.provider_id == provider.id
        assert record.verification_type == VerificationType.FREELANCER_ID
        assert record.status == VerificationStatus.PENDING
        documents = await service.get_documents_for_record(record.id)
        assert len(documents) == 1
        assert documents[0].document_type == DocumentType.EMIRATES_ID
        assert documents[0].ocr_extracted_data == {"full_name": "Jane Doe"}

    @pytest.mark.anyio
    async def test_repreview_with_a_different_extension_replaces_not_accumulates(
        self, db_session, tmp_path: Path
    ) -> None:
        """
        A provider who previews a `.jpg`, then changes their mind and
        previews a `.pdf` instead, must have the `.pdf` be the file that
        actually gets submitted -- not the stale `.jpg` left behind by
        the first preview. Regression test for the fixed-order
        extension search in `_find_pending_file` picking up an orphaned
        file from an earlier preview with a different extension.
        """
        user = await _create_user(db_session, "602000099")
        provider = await _create_provider(
            db_session, user, provider_type=ProviderType.FREELANCER
        )
        service = _verification_service(db_session, tmp_path)

        await service.preview_document(
            user.id,
            upload=_upload(filename="emirates-id.jpg"),
            document_type=DocumentType.EMIRATES_ID,
        )
        await service.preview_document(
            user.id,
            upload=_upload(
                filename="emirates-id.pdf",
                content=_PDF_BYTES,
                content_type="application/pdf",
            ),
            document_type=DocumentType.EMIRATES_ID,
        )

        record = await service.submit(
            user.id,
            document_type=DocumentType.EMIRATES_ID,
            confirmed_fields={"full_name": "Jane Doe"},
        )

        documents = await service.get_documents_for_record(record.id)
        assert len(documents) == 1
        assert documents[0].file_url.endswith(".pdf")

        stale_jpg = tmp_path / "pending" / f"{provider.id}.jpg"
        assert not stale_jpg.exists()


class TestSubmitBusiness:
    @pytest.mark.anyio
    async def test_business_with_no_document_succeeds_by_default(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC2: Business submits per the (lighter, default) config bar --
        no document required."""
        user = await _create_user(db_session, "603000001")
        provider = await _create_provider(
            db_session, user, provider_type=ProviderType.BUSINESS
        )
        service = _verification_service(db_session, tmp_path)

        record = await service.submit(
            user.id, document_type=None, confirmed_fields=None
        )

        assert record.provider_id == provider.id
        assert record.verification_type == VerificationType.BUSINESS_LIGHTWEIGHT
        assert record.status == VerificationStatus.PENDING
        assert await service.get_documents_for_record(record.id) == []

    @pytest.mark.anyio
    async def test_business_document_required_flag_makes_it_behave_like_freelancer(
        self, db_session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "BUSINESS_VERIFICATION_DOCUMENT_REQUIRED", True)
        user = await _create_user(db_session, "603000002")
        await _create_provider(db_session, user, provider_type=ProviderType.BUSINESS)
        service = _verification_service(db_session, tmp_path)

        with pytest.raises(VerificationDocumentRequiredError):
            await service.submit(user.id, document_type=None, confirmed_fields=None)


class TestOcrConfirmationIsEditable:
    @pytest.mark.anyio
    async def test_submitted_confirmed_fields_are_persisted_not_the_stub_output(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC4/AC8: the preview's (always-empty) stub output must never
        be what ends up persisted -- only the user's own, edited,
        submitted `confirmed_fields`."""
        user = await _create_user(db_session, "604000001")
        await _create_provider(db_session, user, provider_type=ProviderType.FREELANCER)
        service = _verification_service(db_session, tmp_path)

        preview_result = await service.preview_document(
            user.id, upload=_upload(), document_type=DocumentType.EMIRATES_ID
        )
        assert preview_result.full_name is None  # the stub's raw (empty) output

        submitted_fields = {
            "full_name": "Jane Q. Doe",
            "id_number": "784-1234-1234567-1",
            "expiry_date": "2030-01-01",
        }
        record = await service.submit(
            user.id,
            document_type=DocumentType.EMIRATES_ID,
            confirmed_fields=submitted_fields,
        )

        documents = await service.get_documents_for_record(record.id)
        assert documents[0].ocr_extracted_data == submitted_fields
        assert documents[0].ocr_extracted_data != {
            "full_name": preview_result.full_name
        }


class TestNeverTouchesProviderDiscoverability:
    @pytest.mark.anyio
    async def test_submit_never_changes_is_discoverable_or_verification_status(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC5/AC8: a successful submission never changes
        `providers.is_discoverable`/`providers.verification_status`."""
        user = await _create_user(db_session, "605000001")
        provider = await _create_provider(
            db_session, user, provider_type=ProviderType.BUSINESS
        )
        before_discoverable = provider.is_discoverable
        before_status = provider.verification_status
        service = _verification_service(db_session, tmp_path)

        await service.submit(user.id, document_type=None, confirmed_fields=None)

        refreshed = await ProviderRepository(db_session).get_by_id(provider.id)
        assert refreshed is not None
        assert refreshed.is_discoverable == before_discoverable
        assert refreshed.verification_status == before_status

    def test_verification_service_never_imports_a_provider_write_path(self) -> None:
        """
        Grep-level review (AC5/AC8, `Plan_S05_VER-001.md`'s Verification
        Plan table): this module must never import `ProviderRepository`
        at all -- only `ProviderService.get_my_provider`, a pure read,
        via constructor injection (Decision 9).
        """
        source = Path(
            "app/modules/verification/services/verification_service.py"
        ).read_text()

        assert "ProviderRepository" not in source
        assert ".verification_status =" not in source
        assert ".is_discoverable =" not in source
        assert "verification_status:" not in source
        assert "is_discoverable" not in source


class TestResubmissionAfterRejection:
    @pytest.mark.anyio
    async def test_resubmission_creates_a_new_row_leaving_the_first_unchanged(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC7: resubmission after a rejection creates a new verification
        cycle rather than mutating the rejected record."""
        user = await _create_user(db_session, "606000001")
        await _create_provider(db_session, user, provider_type=ProviderType.BUSINESS)
        service = _verification_service(db_session, tmp_path)

        first = await service.submit(user.id, document_type=None, confirmed_fields=None)
        # Simulates VER-002 (not built yet) rejecting the first cycle.
        first.status = VerificationStatus.REJECTED
        first.rejection_reason = "Illegible document."
        db_session.add(first)
        await db_session.commit()

        second = await service.submit(
            user.id, document_type=None, confirmed_fields=None
        )

        assert second.id != first.id
        assert second.status == VerificationStatus.PENDING

        refreshed_first = await VerificationRecordRepository(db_session).get_by_id(
            first.id
        )
        assert refreshed_first is not None
        assert refreshed_first.status == VerificationStatus.REJECTED
        assert refreshed_first.rejection_reason == "Illegible document."

    @pytest.mark.anyio
    async def test_second_submit_while_latest_is_pending_is_rejected(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "606000002")
        await _create_provider(db_session, user, provider_type=ProviderType.BUSINESS)
        service = _verification_service(db_session, tmp_path)
        await service.submit(user.id, document_type=None, confirmed_fields=None)

        with pytest.raises(VerificationSubmissionNotAllowedError):
            await service.submit(user.id, document_type=None, confirmed_fields=None)
