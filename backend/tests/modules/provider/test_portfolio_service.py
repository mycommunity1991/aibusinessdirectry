"""
Integration tests for `PortfolioService` (PRO-002), exercised against a
real Postgres database and a real `LocalFileStorage` writing to a
temporary directory -- upload validation, the 20-photo cap, reorder
persistence (re-fetched, not just asserted on the write call), soft
delete, and the ownership boundary are all best verified against the
real thing rather than mocked (mirrors `test_session_service.py`'s
precedent).
"""

import io
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import (
    InvalidPortfolioReorderError,
    InvalidPortfolioUploadError,
    PortfolioLimitExceededError,
    PortfolioPhotoNotFoundError,
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
from app.modules.provider.repositories.portfolio_repository import PortfolioRepository
from app.modules.provider.repositories.provider_category_label_repository import (
    ProviderCategoryLabelRepository,
)
from app.modules.provider.repositories.provider_repository import ProviderRepository
from app.modules.provider.repositories.provider_search_repository import (
    ProviderSearchRepository,
)
from app.modules.provider.repositories.service_area_repository import (
    ServiceAreaRepository,
)
from app.modules.provider.services.portfolio_service import PortfolioService
from app.modules.provider.services.provider_service import ProviderService
from app.shared.storage.local_file_storage import LocalFileStorage

_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


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
        "provider_type": ProviderType.BUSINESS,
        "display_name": "Acme Plumbing",
        "slug": f"acme-plumbing-{uuid.uuid4().hex[:8]}",
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
        provider_search_repository=ProviderSearchRepository(db_session),
        portfolio_repository=PortfolioRepository(db_session),
    )


def _portfolio_service(db_session, upload_dir: Path) -> PortfolioService:
    return PortfolioService(
        portfolio_repository=PortfolioRepository(db_session),
        provider_service=_provider_service(db_session),
        file_storage=LocalFileStorage(base_directory=str(upload_dir)),
    )


def _upload(
    *, filename: str = "my-original-photo.jpg", content: bytes = _JPEG_BYTES
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "image/jpeg"}),
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class TestAddPhoto:
    @pytest.mark.anyio
    async def test_upload_validation_rejects_magic_byte_mismatch(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC2: a `.jpg`-declared file whose bytes aren't a real JPEG is
        rejected, and no `portfolios` row is created."""
        user = await _create_user(db_session, "505000001")
        provider = await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        with pytest.raises(InvalidPortfolioUploadError):
            await service.add_photo(
                user.id,
                upload=_upload(content=b"not a real image, just text padding" * 4),
                caption=None,
            )

        assert await service.list_my_portfolio(user.id) == []
        assert provider.id  # sanity: provider row exists, untouched

    @pytest.mark.anyio
    async def test_generated_filename_never_equals_the_original(
        self, db_session, tmp_path: Path
    ) -> None:
        """`06_SECURITY.md`: the stored filename is always server-
        generated, never the client-supplied original."""
        user = await _create_user(db_session, "505000002")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        photo = await service.add_photo(
            user.id, upload=_upload(filename="my-original-photo.jpg"), caption=None
        )

        assert "my-original-photo" not in photo.media_url
        assert photo.media_url.endswith(".jpg")
        assert photo.media_url.startswith("/media/portfolios/")

    @pytest.mark.anyio
    async def test_enforces_the_twenty_photo_cap(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "505000003")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        for _ in range(20):
            await service.add_photo(user.id, upload=_upload(), caption=None)

        with pytest.raises(PortfolioLimitExceededError):
            await service.add_photo(user.id, upload=_upload(), caption=None)

        assert len(await service.list_my_portfolio(user.id)) == 20


class TestReorder:
    @pytest.mark.anyio
    async def test_reorder_persists_correctly_across_a_fresh_list_call(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC8: create 3 photos, reorder, re-fetch (a separate call, not
        the return value of `reorder` itself), assert the exact order."""
        user = await _create_user(db_session, "505000004")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        first = await service.add_photo(user.id, upload=_upload(), caption="first")
        second = await service.add_photo(user.id, upload=_upload(), caption="second")
        third = await service.add_photo(user.id, upload=_upload(), caption="third")

        new_order = [third.id, first.id, second.id]
        await service.reorder(user.id, new_order)

        refetched = await service.list_my_portfolio(user.id)
        assert [photo.id for photo in refetched] == new_order

    @pytest.mark.anyio
    async def test_reorder_rejects_a_mismatched_id_set(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "505000005")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        first = await service.add_photo(user.id, upload=_upload(), caption=None)
        await service.add_photo(user.id, upload=_upload(), caption=None)

        with pytest.raises(InvalidPortfolioReorderError):
            await service.reorder(user.id, [first.id, uuid.uuid4()])

        with pytest.raises(InvalidPortfolioReorderError):
            await service.reorder(user.id, [first.id])

        with pytest.raises(InvalidPortfolioReorderError):
            await service.reorder(user.id, [first.id, first.id])

        # No partial reorder happened -- original order preserved.
        unchanged = await service.list_my_portfolio(user.id)
        assert unchanged[0].id == first.id


class TestDeletePhoto:
    @pytest.mark.anyio
    async def test_soft_delete_excludes_from_list_but_leaves_file_on_disk(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "505000006")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)
        photo = await service.add_photo(user.id, upload=_upload(), caption=None)
        disk_path = tmp_path / photo.media_url.removeprefix("/media/")
        assert disk_path.exists()

        await service.delete_photo(user.id, photo.id)

        assert await service.list_my_portfolio(user.id) == []
        # Decision 5: the on-disk file must survive a soft delete.
        assert disk_path.exists()

    @pytest.mark.anyio
    async def test_a_second_provider_cannot_delete_the_first_providers_photo(
        self, db_session, tmp_path: Path
    ) -> None:
        """AC7/AC8: ownership enforced -- a 404, not a 200."""
        owner = await _create_user(db_session, "505000007")
        await _create_provider(db_session, owner)
        other = await _create_user(db_session, "505000008")
        await _create_provider(db_session, other, display_name="Someone Else")
        service = _portfolio_service(db_session, tmp_path)

        photo = await service.add_photo(owner.id, upload=_upload(), caption=None)

        with pytest.raises(PortfolioPhotoNotFoundError):
            await service.delete_photo(other.id, photo.id)

        # Still present for the actual owner.
        assert len(await service.list_my_portfolio(owner.id)) == 1

    @pytest.mark.anyio
    async def test_deleting_a_nonexistent_photo_raises_not_found(
        self, db_session, tmp_path: Path
    ) -> None:
        user = await _create_user(db_session, "505000009")
        await _create_provider(db_session, user)
        service = _portfolio_service(db_session, tmp_path)

        with pytest.raises(PortfolioPhotoNotFoundError):
            await service.delete_photo(user.id, uuid.uuid4())
