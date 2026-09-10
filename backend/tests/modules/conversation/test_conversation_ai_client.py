"""
Unit tests for `RuleBasedConversationAiClient` (AI-001, Decision 2).

Pure in-memory `Category`/`CategoryQuestionTemplate`/`ConversationSession`
/`Message` instances (no database) -- this client is a deterministic,
side-effect-free function of its inputs, so no persistence is needed to
exercise it fully. See `test_conversation_service.py` for the
persistence-integrated behavior and `test_grounding.py` for the
structural, cross-cutting grounding proof (AC10).
"""

import uuid

from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.conversation.models import (
    ConversationSession,
    ConversationStatus,
    Message,
    MessageSender,
)
from app.modules.conversation.services.conversation_ai_client import (
    RuleBasedConversationAiClient,
)
from app.modules.identity.models import LanguageCode


def _category(
    *, name: str, name_ar: str | None = None, slug: str, sort_order: int = 0
) -> Category:
    return Category(
        id=uuid.uuid4(),
        name=name,
        name_ar=name_ar,
        slug=slug,
        sort_order=sort_order,
    )


def _template(
    *,
    category_id: uuid.UUID,
    question_text: str,
    question_text_ar: str | None = None,
    question_type: str = "text",
    options: list[str] | None = None,
    is_required: bool = True,
    sort_order: int = 0,
) -> CategoryQuestionTemplate:
    return CategoryQuestionTemplate(
        id=uuid.uuid4(),
        category_id=category_id,
        question_text=question_text,
        question_text_ar=question_text_ar,
        question_type=question_type,
        options=options,
        is_required=is_required,
        sort_order=sort_order,
    )


def _session(*, category_id: uuid.UUID | None = None) -> ConversationSession:
    return ConversationSession(
        id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        category_id=category_id,
        status=ConversationStatus.ACTIVE,
    )


def _message(
    *,
    session_id: uuid.UUID,
    sender: MessageSender,
    content: str,
    sequence_number: int,
) -> Message:
    return Message(
        id=uuid.uuid4(),
        conversation_session_id=session_id,
        sender=sender,
        content=content,
        sequence_number=sequence_number,
    )


def _client() -> RuleBasedConversationAiClient:
    return RuleBasedConversationAiClient()


class TestCategoryResolution:
    """AC4: category resolution never guesses."""

    async def test_resolves_an_unambiguous_category_from_free_text(self) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        electrical = _category(name="Electrical", slug="electrical")
        required = _template(
            category_id=plumbing.id, question_text="What's leaking?", sort_order=0
        )
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing, electrical],
            question_templates_by_category={plumbing.id: [required]},
            customer_message="My plumbing is broken and leaking everywhere",
            language=LanguageCode.EN,
        )

        assert result.resolved_category_id == plumbing.id
        assert result.confidence == 0.0
        assert result.reply_message == required.question_text
        assert result.is_complete is False

    async def test_zero_matches_returns_a_clarifying_prompt_never_a_guess(self) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        electrical = _category(name="Electrical", slug="electrical")
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing, electrical],
            question_templates_by_category={},
            customer_message="I need some help with something",
            language=LanguageCode.EN,
        )

        assert result.resolved_category_id is None
        assert result.confidence == 0.0
        assert result.quick_reply_options == ["Plumbing", "Electrical"]

    async def test_multiple_matches_returns_a_clarifying_prompt_never_a_guess(
        self,
    ) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        electrical = _category(name="Electrical", slug="electrical")
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing, electrical],
            question_templates_by_category={},
            customer_message="I have both plumbing and electrical issues",
            language=LanguageCode.EN,
        )

        assert result.resolved_category_id is None
        assert set(result.quick_reply_options or []) == {"Plumbing", "Electrical"}

    async def test_category_with_no_required_questions_completes_immediately(
        self,
    ) -> None:
        simple = _category(name="Simple Service", slug="simple-service")
        optional_only = _template(
            category_id=simple.id,
            question_text="Anything else?",
            is_required=False,
            sort_order=0,
        )
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[simple],
            question_templates_by_category={simple.id: [optional_only]},
            customer_message="I need a simple service done",
            language=LanguageCode.EN,
        )

        assert result.resolved_category_id == simple.id
        assert result.is_complete is True
        assert result.confidence == 1.0


class TestFollowUpQuestionWalk:
    """AC4: follow-up questions are sourced only from
    `category_question_templates`, walked in `sort_order`, one at a
    time -- never an invented question. Confidence reaches `1.0` only
    once every required question is answered."""

    async def test_walks_required_questions_in_sort_order_never_inventing_one(
        self,
    ) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        q0 = _template(
            category_id=plumbing.id,
            question_text="What's leaking?",
            sort_order=0,
        )
        q1 = _template(
            category_id=plumbing.id,
            question_text="How urgent is this?",
            sort_order=1,
        )
        optional = _template(
            category_id=plumbing.id,
            question_text="Anything else we should know?",
            is_required=False,
            sort_order=2,
        )
        templates_by_category = {plumbing.id: [q0, q1, optional]}
        client = _client()

        session = _session(category_id=None)
        turn_1 = await client.process_turn(
            session=session,
            history=[],
            categories=[plumbing],
            question_templates_by_category=templates_by_category,
            customer_message="My plumbing is broken",
            language=LanguageCode.EN,
        )
        assert turn_1.reply_message == q0.question_text
        assert turn_1.confidence == 0.0
        assert turn_1.is_complete is False

        msg_1 = _message(
            session_id=session.id,
            sender=MessageSender.CUSTOMER,
            content="My plumbing is broken",
            sequence_number=1,
        )
        ai_1 = _message(
            session_id=session.id,
            sender=MessageSender.AI,
            content=q0.question_text,
            sequence_number=2,
        )
        msg_2 = _message(
            session_id=session.id,
            sender=MessageSender.CUSTOMER,
            content="It's the kitchen sink",
            sequence_number=3,
        )
        session_resolved = _session(category_id=plumbing.id)
        session_resolved.id = session.id
        turn_2 = await client.process_turn(
            session=session_resolved,
            history=[msg_1, ai_1, msg_2],
            categories=[plumbing],
            question_templates_by_category=templates_by_category,
            customer_message="It's the kitchen sink",
            language=LanguageCode.EN,
        )
        assert turn_2.reply_message == q1.question_text
        assert turn_2.confidence == 0.5
        assert turn_2.is_complete is False
        # The optional question is never asked or referenced.
        assert optional.question_text not in (
            turn_1.reply_message,
            turn_2.reply_message,
        )

        ai_2 = _message(
            session_id=session.id,
            sender=MessageSender.AI,
            content=q1.question_text,
            sequence_number=4,
        )
        msg_3 = _message(
            session_id=session.id,
            sender=MessageSender.CUSTOMER,
            content="Very urgent, water everywhere",
            sequence_number=5,
        )
        turn_3 = await client.process_turn(
            session=session_resolved,
            history=[msg_1, ai_1, msg_2, ai_2, msg_3],
            categories=[plumbing],
            question_templates_by_category=templates_by_category,
            customer_message="Very urgent, water everywhere",
            language=LanguageCode.EN,
        )
        assert turn_3.is_complete is True
        assert turn_3.confidence == 1.0


class TestQuickReplyOptions:
    async def test_single_select_question_returns_its_options_verbatim(self) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        q0 = _template(
            category_id=plumbing.id,
            question_text="What's the issue?",
            question_type="single_select",
            options=["Leak", "Blockage", "Installation"],
            sort_order=0,
        )
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing],
            question_templates_by_category={plumbing.id: [q0]},
            customer_message="My plumbing needs work",
            language=LanguageCode.EN,
        )

        assert result.quick_reply_options == ["Leak", "Blockage", "Installation"]

    async def test_free_text_question_returns_no_quick_reply_options(self) -> None:
        plumbing = _category(name="Plumbing", slug="plumbing")
        q0 = _template(
            category_id=plumbing.id,
            question_text="Describe the issue",
            question_type="text",
            options=None,
            sort_order=0,
        )
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing],
            question_templates_by_category={plumbing.id: [q0]},
            customer_message="My plumbing needs work",
            language=LanguageCode.EN,
        )

        assert result.quick_reply_options is None


class TestBilingualSelection:
    """Decision 6 / AC11 (backend half): Arabic when requested and
    populated, English fallback when the Arabic field is null."""

    async def test_category_pick_prompt_uses_arabic_names_when_available(self) -> None:
        plumbing = _category(name="Plumbing", name_ar="السباكة", slug="plumbing")
        electrical = _category(name="Electrical", name_ar=None, slug="electrical")
        session = _session(category_id=None)

        result = await _client().process_turn(
            session=session,
            history=[],
            categories=[plumbing, electrical],
            question_templates_by_category={},
            customer_message="I need some unrelated thing",
            language=LanguageCode.AR,
        )

        assert result.quick_reply_options == ["السباكة", "Electrical"]

    async def test_both_languages_are_returned_for_the_caller_to_pick(
        self,
    ) -> None:
        """The client always populates both `reply_message` (English) and
        `reply_message_ar` (Arabic or `None`) -- `ConversationService`
        picks one based on the session's language (Decision 6); the
        client itself never decides."""
        plumbing = _category(name="Plumbing", slug="plumbing")
        q0 = _template(
            category_id=plumbing.id,
            question_text="What's leaking?",
            question_text_ar="ما الذي يتسرب؟",
            sort_order=0,
        )
        q1 = _template(
            category_id=plumbing.id,
            question_text="How urgent?",
            question_text_ar=None,
            sort_order=1,
        )
        templates_by_category = {plumbing.id: [q0, q1]}
        session = _session(category_id=plumbing.id)

        msg_1 = _message(
            session_id=session.id,
            sender=MessageSender.CUSTOMER,
            content="My plumbing is broken",
            sequence_number=1,
        )
        result = await _client().process_turn(
            session=session,
            history=[msg_1],
            categories=[plumbing],
            question_templates_by_category=templates_by_category,
            customer_message="My plumbing is broken",
            language=LanguageCode.AR,
        )
        assert result.reply_message == q0.question_text
        assert result.reply_message_ar == q0.question_text_ar
