"""
Portfolio-photo management for a Provider (PRO-002).

Depends on `ProviderService` (same-module dependency) to resolve the
caller's own Provider -- mirrors `SavedAddressService`'s dependency on
`CustomerService`. Depends on the `FileStorage` protocol (Decision 2,
`Plan_S04_PRO-002.md`), never a concrete storage backend directly.
"""

import uuid

from fastapi import UploadFile

from app.core.authorization import ensure_owner_or_not_found
from app.core.config import settings
from app.core.exceptions import (
    InvalidPortfolioReorderError,
    PortfolioLimitExceededError,
    PortfolioPhotoNotFoundError,
    ProviderNotFoundError,
)
from app.modules.provider.models import Portfolio, Provider
from app.modules.provider.repositories.portfolio_repository import PortfolioRepository
from app.modules.provider.services.provider_service import ProviderService
from app.shared.storage.image_validation import validate_image_upload
from app.shared.storage.interfaces import FileStorage

_PORTFOLIO_SUBDIRECTORY = "portfolios"


class PortfolioService:
    """Orchestrates listing, uploading, soft-deleting, and reordering a
    provider's own portfolio photos."""

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        provider_service: ProviderService,
        file_storage: FileStorage,
    ) -> None:
        self.portfolio_repository = portfolio_repository
        self.provider_service = provider_service
        self.file_storage = file_storage

    async def list_my_portfolio(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Lists the caller's own active photos, ordered by `sort_order`
        (Decision 3, `Plan_S04_PRO-002.md`)."""
        provider = await self._get_provider_or_404(user_id)
        return list(
            await self.portfolio_repository.list_active_for_provider(provider.id)
        )

    async def add_photo(
        self,
        user_id: uuid.UUID,
        *,
        upload: UploadFile,
        caption: str | None,
    ) -> Portfolio:
        """
        Validates and stores a new portfolio photo (AC2). Enforces the
        20-photo cap (Decision 3, `Plan_S04_PRO-002.md`) before ever
        touching storage. Appends the new photo at
        `sort_order = max(existing) + 1`.
        """
        provider = await self._get_provider_or_404(user_id)

        existing = await self.portfolio_repository.list_active_for_provider(provider.id)
        if len(existing) >= settings.MAX_PORTFOLIO_PHOTOS_PER_PROVIDER:
            raise PortfolioLimitExceededError()

        content, extension = await validate_image_upload(upload)
        generated_filename = f"{uuid.uuid4().hex}{extension}"
        media_url = await self.file_storage.save(
            content,
            filename=generated_filename,
            subdirectory=f"{_PORTFOLIO_SUBDIRECTORY}/{provider.id}",
        )

        next_sort_order = max((photo.sort_order for photo in existing), default=-1) + 1

        return await self.portfolio_repository.create(
            {
                "provider_id": provider.id,
                "media_url": media_url,
                "caption": caption,
                "sort_order": next_sort_order,
            }
        )

    async def delete_photo(self, user_id: uuid.UUID, portfolio_id: uuid.UUID) -> None:
        """
        Soft-deletes one of the caller's own photos (AC2, Decision 5).
        `ensure_owner_or_not_found` is load-bearing here (ADR-015): the
        one genuinely `{id}`-addressable route in this module.
        """
        provider = await self._get_provider_or_404(user_id)
        photo = await self.portfolio_repository.get_active_by_id(portfolio_id)
        ensure_owner_or_not_found(
            photo.provider_id if photo is not None else None,
            provider.id,
            not_found_exc=PortfolioPhotoNotFoundError(),
        )
        assert photo is not None  # narrows for type-checkers; guaranteed above

        await self.portfolio_repository.soft_delete(photo)

    async def reorder(
        self, user_id: uuid.UUID, ordered_ids: list[uuid.UUID]
    ) -> list[Portfolio]:
        """
        Reorders the caller's own active photos (AC2, Decision 4).
        Validates the submitted id set is exactly equal (same members, no
        more, no fewer, no duplicates) to the caller's own active photo
        ids *before* writing anything -- a mismatch is rejected (422)
        with no partial reorder.
        """
        provider = await self._get_provider_or_404(user_id)
        existing = await self.portfolio_repository.list_active_for_provider(provider.id)
        existing_ids = {photo.id for photo in existing}
        submitted_ids = set(ordered_ids)

        if submitted_ids != existing_ids or len(ordered_ids) != len(submitted_ids):
            raise InvalidPortfolioReorderError()

        await self.portfolio_repository.bulk_set_sort_order(
            [(photo_id, index) for index, photo_id in enumerate(ordered_ids)]
        )
        return list(
            await self.portfolio_repository.list_active_for_provider(provider.id)
        )

    async def _get_provider_or_404(self, user_id: uuid.UUID) -> Provider:
        provider = await self.provider_service.get_my_provider(user_id)
        if provider is None:
            raise ProviderNotFoundError()
        return provider
