import uuid
from datetime import datetime

from pydantic import BaseModel, Field

_MAX_COMMENT_LENGTH = 2000


class SubmitReviewRequest(BaseModel):
    """
    Request payload for `POST /contact-views/{contact_view_id}/review`
    (REV-002, AC1/AC3) -- rating the provider after a confirmed hire.

    `rating`'s `ge=1, le=5` bound is the first, cheapest layer of AC3's
    three-layer validation (Decision 6, `Plan_S09_REV-002.md`) -- a 422
    before any DB round trip; the DB `CHECK`
    (`chk_reviews_rating_range`) and the `SMALLINT` column type are the
    other two, redundant by design.

    `comment`'s `max_length=2000` is a defensive cap (Open Question 3,
    `Plan_S09_REV-002.md`), not itself an AC requirement.
    """

    rating: int = Field(..., ge=1, le=5, description="1-5.")
    comment: str | None = Field(
        None,
        max_length=_MAX_COMMENT_LENGTH,
        description="Optional free text.",
    )


class ReviewResponse(BaseModel):
    """Response payload for a successfully submitted Review (REV-002, AC1)."""

    id: uuid.UUID
    contact_view_id: uuid.UUID
    provider_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
