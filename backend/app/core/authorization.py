"""
Ownership-check helper (AUTH-004, AC4).

Shared by any service that must reject a request against a resource the
caller does not own, without revealing whether the resource exists at
all -- a 404, never a 403, per this project's established non-revealing-
error philosophy (`SessionNotFoundError`, `Plan_S02_AUTH-003.md`
Decision 9).
"""

import uuid

from app.core.exceptions import BusinessException


def ensure_owner_or_not_found(
    owner_id: uuid.UUID | None,
    requester_id: uuid.UUID,
    *,
    not_found_exc: BusinessException,
) -> None:
    """
    Raises `not_found_exc` unless `owner_id == requester_id`.

    `owner_id=None` (the resource doesn't exist at all) is treated
    identically to "exists but is owned by someone else" -- both
    collapse into the same 404, so the response never reveals which case
    applied. Callers pass the specific, resource-appropriate 404
    exception to raise (e.g. `SessionNotFoundError`) rather than a
    generic one, so each call site keeps its own precise message.
    """
    if owner_id != requester_id:
        raise not_found_exc
