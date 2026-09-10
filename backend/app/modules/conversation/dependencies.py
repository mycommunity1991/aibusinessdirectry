"""Dependency-injection providers for the Conversation module (AI-001)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.category.dependencies import get_category_service
from app.modules.category.services.category_service import CategoryService
from app.modules.conversation.repositories.confidence_score_repository import (
    ConfidenceScoreRepository,
)
from app.modules.conversation.repositories.conversation_session_repository import (
    ConversationSessionRepository,
)
from app.modules.conversation.repositories.message_repository import MessageRepository
from app.modules.conversation.services.conversation_ai_client import (
    ConversationAiClient,
    RuleBasedConversationAiClient,
)
from app.modules.conversation.services.conversation_service import ConversationService
from app.modules.customer.dependencies import get_customer_service
from app.modules.customer.services.customer_service import CustomerService


def get_conversation_session_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationSessionRepository:
    """Provides a `ConversationSessionRepository` bound to the
    request-scoped DB session."""
    return ConversationSessionRepository(db)


def get_message_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageRepository:
    """Provides a `MessageRepository` bound to the request-scoped DB
    session."""
    return MessageRepository(db)


def get_confidence_score_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfidenceScoreRepository:
    """Provides a `ConfidenceScoreRepository` bound to the request-scoped
    DB session."""
    return ConfidenceScoreRepository(db)


def get_conversation_ai_client() -> ConversationAiClient:
    """
    Provides the `ConversationAiClient` (Decision 2) -- the single wiring
    point a future real LLM implementation replaces
    (`OpenAiConversationAiClient`, `AnthropicConversationAiClient`, or
    whichever provider is eventually chosen). `RuleBasedConversationAiClient`
    is stateless and holds no per-request resources, so a fresh instance
    per call is cheap and side-effect-free.
    """
    return RuleBasedConversationAiClient()


def get_conversation_service(
    conversation_session_repository: Annotated[
        ConversationSessionRepository, Depends(get_conversation_session_repository)
    ],
    message_repository: Annotated[MessageRepository, Depends(get_message_repository)],
    confidence_score_repository: Annotated[
        ConfidenceScoreRepository, Depends(get_confidence_score_repository)
    ],
    conversation_ai_client: Annotated[
        ConversationAiClient, Depends(get_conversation_ai_client)
    ],
    customer_service: Annotated[CustomerService, Depends(get_customer_service)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> ConversationService:
    """Provides a `ConversationService` bound to the request-scoped DB
    session, with `CustomerService`/`CategoryService` (Decision 3) wired
    as cross-module, constructor-injected dependencies."""
    return ConversationService(
        conversation_session_repository=conversation_session_repository,
        message_repository=message_repository,
        confidence_score_repository=confidence_score_repository,
        conversation_ai_client=conversation_ai_client,
        customer_service=customer_service,
        category_service=category_service,
    )
