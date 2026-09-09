"""Dependency-injection providers for the Search module."""

from typing import Annotated

from fastapi import Depends

from app.modules.provider.dependencies import get_provider_service
from app.modules.provider.services.provider_service import ProviderService
from app.modules.search.services.search_service import SearchService


def get_search_service(
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> SearchService:
    """
    Provides a `SearchService` bound to the request-scoped DB session.

    Imports `get_provider_service` from `app.modules.provider.
    dependencies` (DIR-001, Decision 4, `Plan_S06_DIR-001.md`) -- the
    same one-directional cross-module shape ADR-014/ADR-016/VER-001
    Decision 9/VER-002 Decision 7 already established.
    """
    return SearchService(provider_service=provider_service)
