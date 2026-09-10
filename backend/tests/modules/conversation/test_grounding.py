"""
Structural grounding proof (AI-001, AC10): no `ConversationTurnResult`/
persisted AI-sender `messages.content` can contain text absent from the
seeded `category_question_templates`/`categories` tables for that
session's resolved category.

This is the concrete, code-level proof behind Decision 2's "grounded by
construction" claim -- not a prompt-instruction assertion. It works by
collecting every *possible* honest string `RuleBasedConversationAiClient`
could ever emit (every seeded category's name/name_ar, every seeded
question's text/text_ar, plus the small, fixed, non-fact-asserting
interim copy constants) and then, for a real multi-turn conversation run
through the real `ConversationService`, asserting every AI-sender
message's content is a member of that closed set.
"""

from app.core.config import settings
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.category.services.category_service import CategoryService
from app.modules.conversation.models import ConversationStatus, MessageSender
from app.modules.conversation.repositories.confidence_score_repository import (
    ConfidenceScoreRepository,
)
from app.modules.conversation.repositories.conversation_session_repository import (
    ConversationSessionRepository,
)
from app.modules.conversation.repositories.message_repository import MessageRepository
from app.modules.conversation.services.conversation_ai_client import (
    _ALL_DONE_AR,
    _ALL_DONE_EN,
    _CLARIFY_CATEGORY_AR,
    _CLARIFY_CATEGORY_EN,
    RuleBasedConversationAiClient,
)
from app.modules.conversation.services.conversation_service import ConversationService
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import AuthProvider, User

from ._search_request_service_helper import make_search_request_service

PHONE_COUNTRY_CODE = "+971"

# The small, fixed, non-fact-asserting interim copy this client may emit
# beyond verbatim template/category data (Decision 2b: no real prompts
# exist for this client to version-control) -- neither invents a
# question, a category, nor any provider fact.
_FIXED_COPY = {_CLARIFY_CATEGORY_EN, _CLARIFY_CATEGORY_AR, _ALL_DONE_EN, _ALL_DONE_AR}


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


async def _seed_categories(db_session) -> list[Category]:
    """Seeds two categories with distinct required and optional
    questions -- a small, deliberately closed taxonomy this test can
    exhaustively enumerate."""
    plumbing = Category(
        name="Plumbing", name_ar="السباكة", slug="plumbing", sort_order=0
    )
    electrical = Category(
        name="Electrical", name_ar=None, slug="electrical", sort_order=1
    )
    db_session.add_all([plumbing, electrical])
    await db_session.flush()

    templates = [
        CategoryQuestionTemplate(
            category_id=plumbing.id,
            question_text="What's leaking?",
            question_text_ar="ما الذي يتسرب؟",
            question_type="text",
            options=None,
            is_required=True,
            sort_order=0,
        ),
        CategoryQuestionTemplate(
            category_id=plumbing.id,
            question_text="How urgent is this?",
            question_text_ar=None,
            question_type="single_select",
            options=["Emergency", "This week", "Just planning"],
            is_required=True,
            sort_order=1,
        ),
        CategoryQuestionTemplate(
            category_id=plumbing.id,
            question_text="Anything else we should know?",
            question_text_ar=None,
            question_type="text",
            options=None,
            is_required=False,
            sort_order=2,
        ),
        CategoryQuestionTemplate(
            category_id=electrical.id,
            question_text="What's the electrical issue?",
            question_text_ar=None,
            question_type="text",
            options=None,
            is_required=True,
            sort_order=0,
        ),
    ]
    db_session.add_all(templates)
    await db_session.commit()
    return [plumbing, electrical]


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
        search_request_service=make_search_request_service(db_session),
    )


async def _allowed_ai_strings(db_session) -> set[str]:
    """The closed set of every string an honest AI-sender message may
    ever equal: every seeded category's `name`/`name_ar`, every seeded
    question's `question_text`/`question_text_ar`, and the client's
    fixed, non-fact-asserting interim copy."""
    category_repo = CategoryRepository(db_session)
    template_repo = CategoryQuestionTemplateRepository(db_session)
    categories = await category_repo.list_active()

    allowed: set[str] = set(_FIXED_COPY)
    for category in categories:
        if category.name:
            allowed.add(category.name)
        if category.name_ar:
            allowed.add(category.name_ar)
        for template in await template_repo.list_for_category(category.id):
            allowed.add(template.question_text)
            if template.question_text_ar:
                allowed.add(template.question_text_ar)
    return allowed


class TestGrounding:
    async def test_no_ai_message_content_is_absent_from_the_seeded_taxonomy(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "704000001")
        await _seed_categories(db_session)
        service = _make_service(db_session)
        allowed = await _allowed_ai_strings(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        after_q0 = await service.submit_turn(
            user.id, started.session.id, content="Kitchen sink"
        )
        completed = await service.submit_turn(
            user.id, after_q0.session.id, content="Emergency"
        )

        ai_messages = [m for m in completed.messages if m.sender == MessageSender.AI]
        assert len(ai_messages) == 3
        for message in ai_messages:
            assert message.content in allowed, message.content

    async def test_clarifying_prompt_content_is_never_a_fabricated_question(
        self, db_session
    ) -> None:
        """Zero/multiple category matches never invent a question -- the
        reply is always the fixed clarify copy, and the offered chips are
        always real category names."""
        user = await _create_user(db_session, "704000002")
        categories = await _seed_categories(db_session)
        service = _make_service(db_session)
        allowed = await _allowed_ai_strings(db_session)

        started = await service.start_conversation(
            user.id, message="I need some unrelated help with a thing"
        )

        ai_message = next(m for m in started.messages if m.sender == MessageSender.AI)
        assert ai_message.content in allowed
        assert ai_message.content == _CLARIFY_CATEGORY_EN
        assert started.session.category_id is None
        assert set(started.quick_reply_options or []) == {c.name for c in categories}

    async def test_grounded_by_construction_across_the_hard_turn_cap_path(
        self, db_session, monkeypatch
    ) -> None:
        """Even a session forced to `routed_to_admin` by the turn cap
        (Decision 4) never accumulates a fabricated AI message along the
        way."""
        monkeypatch.setattr(settings, "CONVERSATION_MAX_TURNS", 1)
        user = await _create_user(db_session, "704000003")
        await _seed_categories(db_session)
        service = _make_service(db_session)
        allowed = await _allowed_ai_strings(db_session)

        routed = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        assert routed.session.status == ConversationStatus.ROUTED_TO_ADMIN
        ai_messages = [m for m in routed.messages if m.sender == MessageSender.AI]
        assert ai_messages
        for message in ai_messages:
            assert message.content in allowed, message.content
