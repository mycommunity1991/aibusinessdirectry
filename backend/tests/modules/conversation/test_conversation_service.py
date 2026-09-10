"""
Integration tests for `ConversationService` (AI-001), exercised against a
real Postgres database with the real `RuleBasedConversationAiClient`
(deterministic, so this stays a reliable integration test) and real
`CustomerService`/`CategoryService` -- mirrors `test_category_service.py`'s
real-DB approach, since this service's own repositories (`get_next_
sequence_number`, `delete_after_sequence`, `get_active_for_customer`)
are exactly the kind of behavior worth proving against a real database.

See `test_conversation_ai_client.py` for `RuleBasedConversationAiClient`'s
own unit tests, `test_conversation_api.py` for the HTTP layer, and
`test_structured_criteria.py` for AC9's payload-shape assertions.
"""

import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import (
    AnswerNotRevisableError,
    ConversationSessionNotActiveError,
    ConversationSessionNotFoundError,
)
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.category.services.category_service import CategoryService
from app.modules.conversation.models import (
    ConfidenceScore,
    ConversationStatus,
    MessageSender,
)
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
from app.modules.customer.repositories.customer_preferences_repository import (
    CustomerPreferencesRepository,
)
from app.modules.customer.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import AuthProvider, User

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
    db_session,
    *,
    name: str = "Plumbing",
    slug: str = "plumbing",
    question_count: int = 2,
) -> Category:
    category = Category(name=name, name_ar=None, slug=slug, sort_order=0)
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


class TestStartConversation:
    async def test_creates_session_and_first_two_messages(self, db_session) -> None:
        """AC1: a new session, its first customer message
        (`sequence_number=1`), and the first AI turn."""
        user = await _create_user(db_session, "701000001")
        await _seed_category(db_session)
        service = _make_service(db_session)

        view = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        assert view.session.status == ConversationStatus.ACTIVE
        assert len(view.messages) == 2
        assert view.messages[0].sender == MessageSender.CUSTOMER
        assert view.messages[0].sequence_number == 1
        assert view.messages[0].content == "My Plumbing needs fixing"
        assert view.messages[1].sender == MessageSender.AI
        assert view.messages[1].sequence_number == 2
        assert view.messages[1].content == "Question 0?"

    async def test_a_prior_active_session_is_marked_abandoned(self, db_session) -> None:
        """Decision 5: a customer can only ever have zero or one
        `active` session at a time."""
        user = await _create_user(db_session, "701000002")
        await _seed_category(db_session)
        service = _make_service(db_session)

        first = await service.start_conversation(user.id, message="Ambiguous text")
        await service.start_conversation(user.id, message="My Plumbing needs fixing")

        session_repo = ConversationSessionRepository(db_session)
        refreshed_first = await session_repo.get_by_id(first.session.id)
        assert refreshed_first.status == ConversationStatus.ABANDONED


class TestSubmitTurn:
    async def test_persists_ordered_messages_and_a_confidence_score_each_turn(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "701000010")
        await _seed_category(db_session)
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        view = await service.submit_turn(
            user.id, started.session.id, content="It's a leak"
        )

        assert [m.sequence_number for m in view.messages] == [1, 2, 3, 4]
        assert view.session.final_confidence_score == 0.5

        scores_result = await db_session.execute(
            select(ConfidenceScore).where(
                ConfidenceScore.conversation_session_id == started.session.id
            )
        )
        scores = scores_result.scalars().all()
        assert len(scores) == 2
        assert all(s.model_version == "rule_based_v1" for s in scores)

    async def test_confidence_reaching_threshold_completes_the_session(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "701000011")
        await _seed_category(db_session)
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        view = await service.submit_turn(
            user.id, started.session.id, content="It's a leak"
        )
        final_view = await service.submit_turn(
            user.id, view.session.id, content="Very urgent"
        )

        assert final_view.session.status == ConversationStatus.COMPLETED
        assert final_view.session.completed_at is not None
        assert final_view.session.structured_criteria is not None
        assert final_view.quick_reply_options is None

    async def test_exceeding_max_turns_without_completing_routes_to_admin(
        self, db_session, monkeypatch
    ) -> None:
        """Decision 4: the hard turn cap forces `routed_to_admin` rather
        than looping indefinitely."""
        monkeypatch.setattr(settings, "CONVERSATION_MAX_TURNS", 1)
        user = await _create_user(db_session, "701000012")
        await _seed_category(db_session, question_count=5)
        service = _make_service(db_session)

        view = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        assert view.session.status == ConversationStatus.ROUTED_TO_ADMIN
        assert view.session.structured_criteria is None

    async def test_submitting_a_turn_to_a_non_active_session_raises(
        self, db_session, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "CONVERSATION_MAX_TURNS", 1)
        user = await _create_user(db_session, "701000013")
        await _seed_category(db_session, question_count=5)
        service = _make_service(db_session)

        view = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        assert view.session.status == ConversationStatus.ROUTED_TO_ADMIN

        try:
            await service.submit_turn(user.id, view.session.id, content="anything")
            raise AssertionError("expected ConversationSessionNotActiveError")
        except ConversationSessionNotActiveError:
            pass

    async def test_cross_customer_submit_turn_raises_not_found(
        self, db_session
    ) -> None:
        owner = await _create_user(db_session, "701000014")
        stranger = await _create_user(db_session, "701000015")
        await _seed_category(db_session)
        service = _make_service(db_session)

        started = await service.start_conversation(
            owner.id, message="My Plumbing needs fixing"
        )

        try:
            await service.submit_turn(
                stranger.id, started.session.id, content="It's a leak"
            )
            raise AssertionError("expected ConversationSessionNotFoundError")
        except ConversationSessionNotFoundError:
            pass


class TestReviseAnswer:
    async def test_truncates_later_messages_and_regenerates(self, db_session) -> None:
        """AC8, Decision 5: revising an earlier answer removes every
        stale message after it and continues from the edited point."""
        user = await _create_user(db_session, "701000020")
        await _seed_category(db_session)
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        after_first_answer = await service.submit_turn(
            user.id, started.session.id, content="It's a leak"
        )
        completed = await service.submit_turn(
            user.id, after_first_answer.session.id, content="Very urgent"
        )
        assert completed.session.status == ConversationStatus.COMPLETED

        # Revise the answer to "Question 0?" (the first customer answer
        # after the free-text description, sequence_number=3).
        answer_to_q0 = next(
            m
            for m in completed.messages
            if m.sender == MessageSender.CUSTOMER and m.content == "It's a leak"
        )
        revised = await service.revise_answer(
            user.id,
            completed.session.id,
            answer_to_q0.id,
            content="It's a blockage",
        )

        # Reprocessed with only one required question answered so far ->
        # reverted to `active`, and the stale `structured_criteria` from
        # the earlier completion must never survive the edit.
        assert revised.session.status == ConversationStatus.ACTIVE
        assert revised.session.structured_criteria is None
        assert [m.sequence_number for m in revised.messages] == [1, 2, 3, 4]
        assert revised.messages[2].content == "It's a blockage"
        assert revised.messages[3].content == "Question 1?"

        # The regenerated question is the same "Question 1?" text --
        # never an invented one -- and the conversation can still
        # re-complete normally.
        recompleted = await service.submit_turn(
            user.id, revised.session.id, content="Still urgent"
        )
        assert recompleted.session.status == ConversationStatus.COMPLETED
        answers = recompleted.session.structured_criteria["answers"]
        assert [a["answer_text"] for a in answers] == [
            "It's a blockage",
            "Still urgent",
        ]

    async def test_revising_the_original_description_re_resolves_category(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "701000021")
        plumbing = await _seed_category(
            db_session, name="Plumbing", slug="plumbing", question_count=1
        )
        electrical = await _seed_category(
            db_session, name="Electrical", slug="electrical", question_count=1
        )
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        assert started.session.category_id == plumbing.id

        first_message = started.messages[0]
        revised = await service.revise_answer(
            user.id,
            started.session.id,
            first_message.id,
            content="My Electrical wiring is broken",
        )

        assert revised.session.category_id == electrical.id
        assert revised.messages[1].content == "Question 0?"

    async def test_revising_a_nonexistent_message_raises(self, db_session) -> None:
        user = await _create_user(db_session, "701000022")
        await _seed_category(db_session)
        service = _make_service(db_session)
        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        try:
            await service.revise_answer(
                user.id, started.session.id, uuid.uuid4(), content="anything"
            )
            raise AssertionError("expected AnswerNotRevisableError")
        except AnswerNotRevisableError:
            pass

    async def test_revising_an_ai_message_raises(self, db_session) -> None:
        user = await _create_user(db_session, "701000023")
        await _seed_category(db_session)
        service = _make_service(db_session)
        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        ai_message = next(m for m in started.messages if m.sender == MessageSender.AI)

        try:
            await service.revise_answer(
                user.id, started.session.id, ai_message.id, content="anything"
            )
            raise AssertionError("expected AnswerNotRevisableError")
        except AnswerNotRevisableError:
            pass

    async def test_revising_an_abandoned_session_raises(self, db_session) -> None:
        user = await _create_user(db_session, "701000024")
        await _seed_category(db_session)
        service = _make_service(db_session)

        first = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        await service.start_conversation(user.id, message="Starting over")

        try:
            await service.revise_answer(
                user.id, first.session.id, first.messages[0].id, content="anything"
            )
            raise AssertionError("expected AnswerNotRevisableError")
        except AnswerNotRevisableError:
            pass


class TestGetSession:
    async def test_returns_the_owners_session_with_quick_reply_options(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "701000030")
        await _seed_category(db_session)
        service = _make_service(db_session)
        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )

        fetched = await service.get_session(user.id, started.session.id)

        assert fetched.session.id == started.session.id
        assert len(fetched.messages) == 2

    async def test_completed_session_has_no_quick_reply_options(
        self, db_session
    ) -> None:
        user = await _create_user(db_session, "701000031")
        await _seed_category(db_session, question_count=1)
        service = _make_service(db_session)
        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        completed = await service.submit_turn(
            user.id, started.session.id, content="One answer"
        )
        assert completed.session.status == ConversationStatus.COMPLETED

        fetched = await service.get_session(user.id, completed.session.id)

        assert fetched.quick_reply_options is None

    async def test_cross_customer_get_session_raises_not_found(
        self, db_session
    ) -> None:
        owner = await _create_user(db_session, "701000032")
        stranger = await _create_user(db_session, "701000033")
        await _seed_category(db_session)
        service = _make_service(db_session)
        started = await service.start_conversation(
            owner.id, message="My Plumbing needs fixing"
        )

        try:
            await service.get_session(stranger.id, started.session.id)
            raise AssertionError("expected ConversationSessionNotFoundError")
        except ConversationSessionNotFoundError:
            pass

    async def test_nonexistent_session_raises_not_found(self, db_session) -> None:
        user = await _create_user(db_session, "701000034")
        service = _make_service(db_session)

        try:
            await service.get_session(user.id, uuid.uuid4())
            raise AssertionError("expected ConversationSessionNotFoundError")
        except ConversationSessionNotFoundError:
            pass


class TestMessageOrderingInvariant:
    async def test_sequence_numbers_are_strictly_increasing_and_never_reused(
        self, db_session
    ) -> None:
        """AC1: messages are ordered by `sequence_number`, never
        overwritten."""
        user = await _create_user(db_session, "701000040")
        await _seed_category(db_session)
        service = _make_service(db_session)

        started = await service.start_conversation(
            user.id, message="My Plumbing needs fixing"
        )
        final = await service.submit_turn(
            user.id, started.session.id, content="It's a leak"
        )
        await service.submit_turn(user.id, final.session.id, content="Very urgent")

        message_repo = MessageRepository(db_session)
        all_messages = list(await message_repo.list_for_session(started.session.id))
        sequence_numbers = [m.sequence_number for m in all_messages]
        assert sequence_numbers == sorted(sequence_numbers)
        assert len(sequence_numbers) == len(set(sequence_numbers))
