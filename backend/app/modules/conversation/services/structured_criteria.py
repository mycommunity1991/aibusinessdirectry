"""
`StructuredCriteria` Pydantic model (AI-001, Decision 1b, AC9).

Satisfies AC9 ("Every completed session produces a `search_requests`-
ready `structured_criteria` payload, validated via a Pydantic model
before persistence") without crossing Decision 1's scope boundary: this
payload lives entirely inside `conversation_sessions.structured_criteria`
(a column on a table this story already owns), never written to
`search.search_requests` itself. A future `AI-002` (or later) story is
the one that reads this column to build the actual `search_requests` row.

A genuinely category-agnostic shape -- works identically for every
category's question set, no per-category schema needed -- built from
exactly two things `ConversationService` already has in hand at
completion time: the resolved `Category` and every answered
`is_required=true` `CategoryQuestionTemplate` for it, paired with the
customer's persisted `messages.content` answer for that question.
"""

import uuid

from pydantic import BaseModel, Field


class StructuredCriteriaAnswer(BaseModel):
    """One answered, required follow-up question -- verbatim template
    text paired with the customer's own persisted answer text."""

    question_id: uuid.UUID = Field(
        ..., description="The `category_question_templates.id` this answer responds to."
    )
    question_text: str = Field(
        ..., description="The question's verbatim text, in the language it was asked."
    )
    answer_text: str = Field(
        ..., description="The customer's own answer, verbatim (`messages.content`)."
    )


class StructuredCriteria(BaseModel):
    """
    The `search_requests`-ready payload for a `completed` conversation
    session (AC9). Validated via `StructuredCriteria.model_validate(...)`
    before `ConversationService` ever passes it to
    `ConversationSessionRepository.complete_session` -- a malformed or
    incomplete shape raises `pydantic.ValidationError` here, which
    `ConversationService` catches and re-raises as
    `InvalidStructuredCriteriaError` (a 500 that should never occur in
    correct code, but is a real, non-decorative validation gate, not
    merely true by convention).
    """

    category_id: uuid.UUID = Field(
        ..., description="The session's resolved `categories.id`."
    )
    category_slug: str = Field(
        ..., description="The resolved category's `slug`, for a human-legible payload."
    )
    answers: list[StructuredCriteriaAnswer] = Field(
        ...,
        description=(
            "Every answered `is_required=true` question for the resolved "
            "category, in `sort_order`."
        ),
    )
