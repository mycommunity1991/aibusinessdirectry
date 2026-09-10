import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_role
from app.core.constants import ROLE_CUSTOMER
from app.database.session import get_db
from app.modules.conversation.dependencies import get_conversation_service
from app.modules.conversation.schemas import (
    ConversationSessionResponse,
    ReviseAnswerRequest,
    StartConversationRequest,
    SubmitTurnRequest,
    message_to_response,
)
from app.modules.conversation.services.conversation_service import (
    ConversationService,
    ConversationTurnView,
)
from app.shared.schemas.response import SuccessResponse

router = APIRouter(tags=["Conversation"])


def _to_response(view: ConversationTurnView) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        id=view.session.id,
        status=view.session.status,
        category_id=view.session.category_id,
        messages=[message_to_response(m) for m in view.messages],
        quick_reply_options=view.quick_reply_options,
        search_request_id=view.search_request_id,
    )


@router.post(
    "",
    response_model=SuccessResponse[ConversationSessionResponse],
    status_code=201,
    responses={
        201: {
            "model": SuccessResponse[ConversationSessionResponse],
            "description": "The conversation session was created.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
    },
    summary="Start a Guided AI Conversation",
    description=(
        "Creates a new conversation session, its first customer message, "
        "and the first AI turn, in one call (AC1). If the caller has a "
        "still-active prior session, it is marked `abandoned` first "
        "(Decision 5) -- a customer can only ever have zero or one "
        "`active` session at a time."
    ),
)
async def start_conversation(
    payload: StartConversationRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    conversation_service: ConversationService = Depends(  # noqa: B008
        get_conversation_service  # noqa: B008
    ),
) -> SuccessResponse[ConversationSessionResponse]:
    """Start a new guided AI-intake conversation."""
    view = await conversation_service.start_conversation(
        current_user.id, message=payload.message
    )
    await db.commit()
    return SuccessResponse[ConversationSessionResponse](
        success=True,
        message="Conversation started.",
        data=_to_response(view),
    )


@router.post(
    "/{session_id}/messages",
    response_model=SuccessResponse[ConversationSessionResponse],
    responses={
        200: {
            "model": SuccessResponse[ConversationSessionResponse],
            "description": "The turn was submitted and the next AI turn generated.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The session does not exist, or does not belong to the "
                "caller -- the response never reveals which."
            ),
        },
        409: {
            "description": (
                "The session is no longer `active` (already `completed`, "
                "`routed_to_admin`, or `abandoned`)."
            ),
        },
    },
    summary="Submit a Conversation Turn",
    description=(
        "Submits the customer's next free-text answer or quick-reply "
        "chip choice and generates the next AI turn (AC4/AC6/AC7). "
        "Follow-up questions are sourced only from `category_question_"
        "templates` for the resolved category -- the AI never asks an "
        "invented question (AC4)."
    ),
)
async def submit_turn(
    session_id: uuid.UUID,
    payload: SubmitTurnRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    conversation_service: ConversationService = Depends(  # noqa: B008
        get_conversation_service  # noqa: B008
    ),
) -> SuccessResponse[ConversationSessionResponse]:
    """Submit the next turn in an active conversation session."""
    view = await conversation_service.submit_turn(
        current_user.id, session_id, content=payload.resolved_content()
    )
    await db.commit()
    return SuccessResponse[ConversationSessionResponse](
        success=True,
        message="Turn submitted.",
        data=_to_response(view),
    )


@router.patch(
    "/{session_id}/answers/{message_id}",
    response_model=SuccessResponse[ConversationSessionResponse],
    responses={
        200: {
            "model": SuccessResponse[ConversationSessionResponse],
            "description": "The answer was revised and the conversation regenerated.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The session does not exist, or does not belong to the "
                "caller -- the response never reveals which."
            ),
        },
        422: {
            "description": (
                "`message_id` does not reference an existing customer "
                "message in this session, or the session is `abandoned` "
                "and cannot be revised."
            ),
        },
    },
    summary="Revise a Previous Answer",
    description=(
        "Updates a prior customer answer, truncates every later message "
        "in the same session, and regenerates the next turn fresh from "
        "the now-shorter history (AC8, Decision 5) -- the customer can "
        "go back and revise without restarting the entire conversation."
    ),
)
async def revise_answer(
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: ReviseAnswerRequest,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    conversation_service: ConversationService = Depends(  # noqa: B008
        get_conversation_service  # noqa: B008
    ),
) -> SuccessResponse[ConversationSessionResponse]:
    """Revise a previous customer answer without restarting the session."""
    view = await conversation_service.revise_answer(
        current_user.id, session_id, message_id, content=payload.content
    )
    await db.commit()
    return SuccessResponse[ConversationSessionResponse](
        success=True,
        message="Answer revised.",
        data=_to_response(view),
    )


@router.get(
    "/{session_id}",
    response_model=SuccessResponse[ConversationSessionResponse],
    responses={
        200: {
            "model": SuccessResponse[ConversationSessionResponse],
            "description": "The session's current state and full transcript.",
        },
        401: {"description": "Authentication required."},
        403: {
            "description": (
                "The token is valid, but the caller does not hold the customer role."
            ),
        },
        404: {
            "description": (
                "The session does not exist, or does not belong to the "
                "caller -- the response never reveals which."
            ),
        },
    },
    summary="Get a Conversation Session",
    description=(
        "Resumes a session after an app restart, or reviews its "
        "transcript -- resolved exclusively against the caller's own "
        "sessions (`ensure_owner_or_not_found`, ADR-015)."
    ),
)
async def get_session(
    session_id: uuid.UUID,
    current_user: CurrentUser = Depends(  # noqa: B008
        require_role(ROLE_CUSTOMER)  # noqa: B008
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    conversation_service: ConversationService = Depends(  # noqa: B008
        get_conversation_service  # noqa: B008
    ),
) -> SuccessResponse[ConversationSessionResponse]:
    """Retrieve a conversation session owned by the caller."""
    view = await conversation_service.get_session(current_user.id, session_id)
    await db.commit()
    return SuccessResponse[ConversationSessionResponse](
        success=True,
        message="Conversation retrieved.",
        data=_to_response(view),
    )
