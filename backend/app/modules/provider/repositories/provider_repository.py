import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider.models import BusinessProfile, ListingSource, Provider
from app.repositories.base_repository import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    """Repository for the `provider.providers` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Provider, session=session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Provider | None:
        """
        Retrieve a Provider by its owning `identity.users.id`. The
        one-provider-per-account existence check (AC8) and the backing
        query for `GET /providers/me` (Decision 9,
        `Plan_S04_PRO-001.md`).
        """
        stmt = select(Provider).where(Provider.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Provider | None:
        """
        Retrieve a Provider by its unique `slug` -- used only by
        `ProviderService._generate_unique_slug`'s collision-check loop
        (Decision 6, `Plan_S04_PRO-001.md`); never a client-facing lookup
        key in this story.
        """
        stmt = select(Provider).where(Provider.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[Provider]:
        """
        Batch-fetches Providers by id in one query (VER-002, Decision 9,
        `Plan_S05_VER-002.md`) -- used by `AdminVerificationService.
        list_pending_for_review` to enrich a page of verification
        records with Provider context without an N+1 query per record.
        """
        if not ids:
            return []
        stmt = select(Provider).where(Provider.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def try_claim_for_account(
        self,
        provider_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        claimed_at: datetime,
    ) -> bool:
        """
        Atomically transitions a Provider to claimed, but only if it is
        *still* `is_claimed=False` at the moment this statement executes
        (CLM-001, Decision 6 -- the genuine race-condition defense for
        two callers attempting to claim the same listing concurrently).

        A plain read-then-write (fetch the provider, check `is_claimed`
        in Python, then `UPDATE` it) leaves a window where two
        concurrent claim attempts on the *same* listing can both pass
        the Python-level check before either commits -- the second
        `UPDATE` would silently overwrite the first claimant's `user_id`
        with no error raised at all. A single conditional `UPDATE ...
        WHERE is_claimed = false` closes that window exactly the way
        `VerificationRecordRepository.try_claim_for_review` (VER-002)
        already established for the analogous "exactly one reviewer
        wins" problem: Postgres takes a row lock on the first matching
        writer, and a concurrent second `UPDATE` targeting the same row
        blocks until the first commits, then re-evaluates this
        statement's own `WHERE` clause against the now-current
        (already-claimed) row -- so at most one caller's `UPDATE` can
        ever match, even under true concurrency (this codebase's engine
        runs at Postgres's READ COMMITTED default,
        `app/database/database.py`).

        Returns `True` if this call won the race and applied the
        transition, `False` if the row was no longer claimable (already
        claimed by a concurrent call, or by the time this executes) --
        the caller is expected to raise `ClaimAlreadyClaimedError` in
        that case.
        """
        stmt = (
            sql_update(Provider)
            .where(Provider.id == provider_id, Provider.is_claimed.is_(False))
            .values(is_claimed=True, user_id=user_id, claimed_at=claimed_at)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        # `Result`'s type stubs don't expose `rowcount` (it's a
        # `CursorResult`-only attribute, always present at runtime for a
        # Core `UPDATE`/`DELETE` statement executed this way) -- mirrors
        # `VerificationRecordRepository.try_claim_for_review`'s
        # identical pattern.
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount == 1

    async def get_by_google_place_id(self, google_place_id: str) -> Provider | None:
        """
        Retrieve a Provider by its `google_place_id` (CLM-001, Decision
        1, `Plan_S06_CLM-001.md`) -- the import job's idempotency key:
        looking this up before writing decides whether a fetched place
        is a fresh `create_google_seeded_provider` or an existing
        `backfill_google_seeded_provider` target.
        """
        stmt = select(Provider).where(Provider.google_place_id == google_place_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_unclaimed(
        self, *, query: str, limit: int, offset: int
    ) -> tuple[list[Provider], int]:
        """
        Free-text substring search among still-unclaimed Google-seeded
        listings (CLM-001, AC3, Decision 5, `Plan_S06_CLM-001.md`) --
        scoped strictly to `listing_source=google_seeded_unclaimed AND
        is_claimed=false`, matching `query` via case-insensitive
        substring `ILIKE` against `display_name` and (via an outer join,
        since a companion `business_profiles` row is expected but not
        structurally guaranteed) `business_profiles.address_line`/
        `city`. Deliberately substring, not exact match, unlike DIR-001's
        category search (Decision 5's own reasoning) -- a self-
        identifying name/address search benefits from partial typing.

        Returns ordered-by-`display_name` results plus a total count for
        `PaginationMeta`.
        """
        pattern = f"%{query}%"
        base_filters = (
            Provider.listing_source == ListingSource.GOOGLE_SEEDED_UNCLAIMED,
            Provider.is_claimed.is_(False),
            or_(
                Provider.display_name.ilike(pattern),
                BusinessProfile.address_line.ilike(pattern),
                BusinessProfile.city.ilike(pattern),
            ),
        )
        base_stmt = select(Provider).outerjoin(
            BusinessProfile, BusinessProfile.provider_id == Provider.id
        )

        count_result = await self.session.execute(
            select(func.count()).select_from(base_stmt.where(*base_filters).subquery())
        )
        total = count_result.scalar_one()

        stmt = (
            base_stmt.where(*base_filters)
            .order_by(Provider.display_name.asc(), Provider.id.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
