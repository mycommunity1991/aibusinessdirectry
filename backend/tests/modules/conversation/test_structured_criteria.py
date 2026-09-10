"""
Tests for the `StructuredCriteria` Pydantic model and its persisted
population on `conversation_sessions.structured_criteria` (AI-001,
Decision 1b, AC9).

`TestStructuredCriteriaValidation` is pure Pydantic, no database.
`TestStructuredCriteriaPersistence` exercises the real `ConversationService`
against a real database (mirroring `test_conversation_service.py`'s
approach) to prove the payload is actually written correctly at
completion time, and left `NULL` for a `routed_to_admin` session.
"""

import uuid

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.category.services.category_service import CategoryService
from app.modules.conversation.models import ConversationStatus
from app.modules.conversation.repositories.confidence_score_repository import (
    ConfidenceScoreRepository,
)
from app.modules.conversation.repositories.conversation_session_repository import (
    ConversationSessionRepository,
)
from app.modules.conversation.repositories.message_repository import MessageRepository
from app.modules.conversation.services.conversation_ai_client import (
    RuleBasedConversationAiClient,
)
from app.modules.conversation.services.conversation_service import ConversationService
from app.modules.conversation.services.structured_criteria import (
    StructuredCriteria,
    StructuredCriteriaAnswer,
)
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import AuthProvider, User


class TestStructuredCriteriaValidation:
    def test_accepts_a_well_formed_payload(self) -> None:
        payload = StructuredCriteria(
            category_id=uuid.uuid4(),
            category_slug="plumbing",
            answers=[
                StructuredCriteriaAnswer(
                    question_id=uuid.uuid4(),
                    question_text="What's leaking?",
                    answer_text="The kitchen sink",
                )
            ],
        )
        dumped = payload.model_dump(mode="json")
        assert dumped["category_slug"] == "plumbing"
        assert dumped["answers"][0]["answer_text"] == "The kitchen sink"

    def test_accepts_zero_answers(self) -> None:
        """A category with no required questions is a valid, empty
        answer set."""
        payload = StructuredCriteria(
            category_id=uuid.uuid4(), category_slug="simple-service", answers=[]
        )
        assert payload.answers == []

    def test_rejects_missing_category_id(self) -> None:
        with pytest.raises(ValidationError):
            StructuredCriteria(category_slug="plumbing", answers=[])

    def test_rejects_an_invalid_category_id_type(self) -> None:
        with pytest.raises(ValidationError):
            StructuredCriteria(
                category_id="not-a-uuid", category_slug="plumbing", answers=[]
            )

    def test_rejects_an_answer_missing_question_text(self) -> None:
        with pytest.raises(ValidationError):
            StructuredCriteria(
                category_id=uuid.uuid4(),
                category_slug="plumbing",
                answers=[
                    {
                        "question_id": str(uuid.uuid4()),
                        "answer_text": "The kitchen sink",
                    }
                ],
            )

    def test_rejects_an_answer_with_wrong_types(self) -> None:
        with pytest.raises(ValidationError):
            StructuredCriteria(
                category_id=uuid.uuid4(),
                category_slug="plumbing",
                answers=[
                    {
                        "question_id": "not-a-uuid",
                        "question_text": "What's leaking?",
                        "answer_text": "The kitchen sink",
                    }
                ],
            )


PHONE_COUNTRY_CODE = "+971"


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code=PHONE_COUNTRY_CODE,
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_category(
    db_session, *, question_count: int = 2, slug: str = "plumbing"
) -> Category:
    category = Category(name="Plumbing", name_ar=None, slug=slug, sort_order=0)
    db_session.add(category)
    await db_session.flush()
    for i in range(question_count):
        db_session.add(
            CategoryQuestionTemplate(
                category_id=category.id,
                question_text=f"Question {i}?",
                question_text_ar=None,
                question_type="text",
                options=None,
                is_required=True,
                sort_order=i,
            )
        )
    await db_session.commit()
    await db_session.refresh(category)
    return category


def _make_service(db_session) -> ConversationService:
    return ConversationService(
        conversation_session_repository=ConversationSessionRepository(db_session),
        message_repository=MessageRepository(db_session),
        confidence_score_repository=ConfidenceScoreRepository(db_session),
        conversation_ai_client=RuleBasedConversationAiClient(),
        customer_service=CustomerService(
            CustomerProfileRepository(db_session),
            CustomerPreferencesRepository(db_session),
        ),
        category_service=CategoryService(
            CategoryRepository(db_session),
            CategoryQuestionTemplateRepository(db_session),
        ),
    )


class TestStructuredCriteriaPersistence:
    async def test_completed_session_structured_criteria_matches_answers(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "702000001")
        category = await _seed_category(db_session, question_count=2)
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        after_q0 = await service.submit_turn(
            user.id, started.session.id, content="Leaking sink"
        )
        completed = await service.submit_turn(
            user.id, after_q0.session.id, content="Very urgent"
        )

        assert completed.session.status == ConversationStatus.COMPLETED
        payload = completed.session.structured_criteria
        assert payload["category_id"] == str(category.id)
        assert payload["category_slug"] == "plumbing"
        assert [a["question_text"] for a in payload["answers"]] == [
            "Question 0?",
            "Question 1?",
        ]
        assert [a["answer_text"] for a in payload["answers"]] == [
            "Leaking sink",
            "Very urgent",
        ]
        # Validates as a real `StructuredCriteria` round trip.
        StructuredCriteria.model_validate(payload)

    async def test_category_with_no_required_questions_has_empty_answers(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "702000002")
        await _seed_category(db_session, question_count=0)
        service = _make_service(db_session)

        completed = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        assert completed.session.status == ConversationStatus.COMPLETED
        assert completed.session.structured_criteria["answers"] == []

    async def test_routed_to_admin_session_has_null_structured_criteria(
        self, db_session, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "CONVERSATION_MAX_TURNS", 1)
        user = await _create_user(db_session, "702000003")
        await _seed_category(db_session, question_count=5)
        service = _make_service(db_session)

        routed = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        assert routed.session.status == ConversationStatus.ROUTED_TO_ADMIN
        assert routed.session.structured_criteria is None
