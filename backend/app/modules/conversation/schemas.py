import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.conversation.models import ConversationStatus, Message, MessageSender


class StartConversationRequest(BaseModel):
    """Request payload for `POST /conversations` (AC1)."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The customer's free-text description of what they need.",
        examples=["My kitchen sink is leaking and I need someone today"],
    )


class SubmitTurnRequest(BaseModel):
    """
    Request payload for `POST /conversations/{session_id}/messages`
    (AC4/AC6/AC7, Decision 7). Exactly one of `content` (free text) or
    `selected_option` (a quick-reply chip choice) must be provided --
    `selected_option` is mapped to `content` server-side for persistence
    consistency (`messages.content` has no separate "was this a chip
    choice" column, and doesn't need one).
    """

    content: str | None = Field(
        None, min_length=1, max_length=2000, description="A free-text answer."
    )
    selected_option: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="A quick-reply chip choice, verbatim.",
    )

    @model_validator(mode="after")
    def _exactly_one_provided(self) -> SubmitTurnRequest:
        if (self.content is None) == (self.selected_option is None):
            raise ValueError("Provide exactly one of `content` or `selected_option`.")
        return self

    def resolved_content(self) -> str:
        """The single string to persist as `messages.content`, regardless
        of which field the caller populated."""
        return self.content if self.content is not None else self.selected_option  # type: ignore[return-value]


class ReviseAnswerRequest(BaseModel):
    """Request payload for `PATCH
    /conversations/{session_id}/answers/{message_id}` (AC8, Decision 5)."""

    content: str = Field(
        ..., min_length=1, max_length=2000, description="The corrected answer text."
    )


class MessageResponse(BaseModel):
    """One transcript entry (AC1)."""

    id: uuid.UUID = Field(..., description="The message's unique identifier.")
    sender: MessageSender = Field(..., description="Who sent this message.")
    content: str = Field(..., description="The message's text content.")
    sequence_number: int = Field(
        ..., description="This message's position within the session."
    )
    created_at: datetime = Field(..., description="When this message was sent.")


def message_to_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        sender=message.sender,
        content=message.content,
        sequence_number=message.sequence_number,
        created_at=message.created_at,
    )


class ConversationSessionResponse(BaseModel):
    """
    Response payload for every conversation-session-returning endpoint
    (Decision 7). Deliberately never includes a raw numeric confidence/
    score field -- only `status`, which the mobile UI maps to
    user-facing states -- satisfying AC6's "never shows a raw confidence
    score to the user" at the API-contract level, not merely by the
    mobile UI choosing not to render a field it could otherwise see.

    `search_request_id` (AI-002, `Plan_S07_AI-002.md`, Decision 6) is the
    only field this story adds -- **never** a confidence value, so AC6
    (`AI-001`) and this story's own AC3 remain intact. Populated once
    `status` reaches `completed`/`routed_to_admin`, `None` while
    `active`/`abandoned` -- lets the mobile client fetch `GET
    /search-requests/{id}` for the ranked-results screen, identical
    whether the eventual match was automated or manual (AC4).
    """

    id: uuid.UUID = Field(..., description="The session's unique identifier.")
    status: ConversationStatus = Field(..., description="The session's current status.")
    category_id: uuid.UUID | None = Field(
        None, description="The resolved category, if known yet."
    )
    messages: list[MessageResponse] = Field(
        ..., description="The full transcript, ordered by `sequence_number`."
    )
    quick_reply_options: list[str] | None = Field(
        None,
        description=(
            "Chip choices for the current turn, if the AI expects a "
            "selection rather than free text. `None` when free text is "
            "expected, or when the session is no longer `active`."
        ),
    )
    search_request_id: uuid.UUID | None = Field(
        None,
        description=(
            "The `search.search_requests` row created for this session "
            "once it leaves `active` (AI-002, Decision 6). `None` while "
            "`active`/`abandoned`."
        ),
    )
