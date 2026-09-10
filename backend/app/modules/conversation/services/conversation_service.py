"""
`ConversationService` (AI-001/AI-002) -- orchestrates a guided AI-intake
conversation end to end: starting a session, submitting turns, revising
a previous answer, and reading a session back.

Depends on the `ConversationAiClient` Protocol only (Decision 2) --
never a concrete client -- and on `CustomerService`/`CategoryService`
(Decision 3, cross-module, constructor-injected, same-session, mirroring
ADR-014/ADR-016 exactly).

**AI-002 (`Plan_S07_AI-002.md`, Decision 1) extends this service with
one new cross-module dependency, `SearchRequestService` (`search`)** --
the single call site is inside `_apply_completion_policy`, immediately
after a session transitions to `completed` **or** `routed_to_admin`;
both branches call the same `search_request_service.
handle_session_completed(...)`, passing only plain primitives (never a
`ConversationSession` ORM object) so `search` has zero imports from
`conversation`. This is what makes AC2 ("never left in limbo") and AC4/
AC6 (the automated and manual paths sharing one finalization mechanism)
true from the conversation side.
"""

import uuid
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.authorization import ensure_owner_or_not_found
from app.core.config import settings
from app.core.exceptions import (
    AnswerNotRevisableError,
    ConversationSessionNotActiveError,
    ConversationSessionNotFoundError,
    InvalidStructuredCriteriaError,
)
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.services.category_service import CategoryService
from app.modules.conversation.models import (
    ConversationSession,
    ConversationStatus,
    Message,
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
    MODEL_VERSION,
    ConversationAiClient,
    ConversationTurnResult,
)
from app.modules.conversation.services.structured_criteria import (
    StructuredCriteria,
    StructuredCriteriaAnswer,
)
from app.modules.customer.services.customer_service import CustomerService
from app.modules.identity.models import LanguageCode
from app.modules.search.services.search_request_service import SearchRequestService

TemplatesByCategory = dict[uuid.UUID, list[CategoryQuestionTemplate]]


@dataclass(frozen=True)
class ConversationTurnView:
    """
    A session plus the *ephemeral* quick-reply chip options for its
    current turn (Decision 7's `quick_reply_options`) -- deliberately not
    a persisted field on `ConversationSession` itself (no such column
    exists, and none is needed): every mutating action already has the
    just-computed `ConversationTurnResult` in hand, and a plain `GET`
    (`get_session`) recovers it by replaying `ConversationAiClient
    .process_turn` read-only against the unchanged, already-persisted
    history -- side-effect-free and deterministic for this story's
    rule-based client, so it reproduces the exact same result without
    creating a new message or confidence row.

    `search_request_id` (AI-002, Decision 6) is similarly not a
    persisted column on `ConversationSession` -- it is looked up from
    `search.search_requests.conversation_session_id` (the reverse FK)
    via `SearchRequestService.get_search_request_id_for_session` every
    time a view is built, `None` while the session is still `active`.
    """

    session: ConversationSession
    messages: list[Message]
    quick_reply_options: list[str] | None
    search_request_id: uuid.UUID | None


class ConversationService:
    """Orchestrates the guided AI-intake conversation domain (AI-001)."""

    def __init__(
        self,
        conversation_session_repository: ConversationSessionRepository,
        message_repository: MessageRepository,
        confidence_score_repository: ConfidenceScoreRepository,
        conversation_ai_client: ConversationAiClient,
        customer_service: CustomerService,
        category_service: CategoryService,
        search_request_service: SearchRequestService,
    ) -> None:
        self.conversation_session_repository = conversation_session_repository
        self.message_repository = message_repository
        self.confidence_score_repository = confidence_score_repository
        self.conversation_ai_client = conversation_ai_client
        self.customer_service = customer_service
        self.category_service = category_service
        self.search_request_service = search_request_service

    async def start_conversation(
        self, user_id: uuid.UUID, *, message: str
    ) -> ConversationTurnView:
        """
        Creates a new session, its first customer message, and the first
        AI turn, in one call (AC1, Decision 7). If the caller has a
        still-`active` prior session, it is marked `abandoned` first
        (Decision 5) -- a customer can only ever have zero or one
        `active` session at a time.
        """
        profile, preferences = await self.customer_service.get_my_profile(user_id)

        prior_active = (
            await self.conversation_session_repository.get_active_for_customer(
                profile.id
            )
        )
        if prior_active is not None:
            await self.conversation_session_repository.update_status(
                prior_active, ConversationStatus.ABANDONED
            )

        session = await self.conversation_session_repository.create(
            {"customer_id": profile.id}
        )
        await self.message_repository.create(
            {
                "conversation_session_id": session.id,
                "sender": MessageSender.CUSTOMER,
                "content": message,
                "sequence_number": 1,
            }
        )

        return await self._advance_turn(session, preferences.language)

    async def submit_turn(
        self, user_id: uuid.UUID, session_id: uuid.UUID, *, content: str
    ) -> ConversationTurnView:
        """
        Persists the customer's next free-text answer or quick-reply
        choice and generates the next AI turn (AC4/AC6/AC7). Applies
        Decision 4's completion policy: confidence-threshold first, then
        the hard turn cap.
        """
        profile, preferences = await self.customer_service.get_my_profile(user_id)
        session = await self._get_owned_session(session_id, profile.id)

        if session.status != ConversationStatus.ACTIVE:
            raise ConversationSessionNotActiveError()

        await self._append_customer_message(session, content)

        return await self._advance_turn(session, preferences.language)

    async def revise_answer(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        content: str,
    ) -> ConversationTurnView:
        """
        Truncate-and-regenerate (Decision 5, AC8): updates a prior
        customer answer, soft-deletes every later message in the same
        session (customer and AI alike), then regenerates the next turn
        fresh from the now-shorter history.

        A session that had already `completed`/`routed_to_admin` reverts
        to `active` and has any stale `structured_criteria` cleared
        (Decision 1b) while the truncated history is reprocessed -- it
        may or may not re-complete, depending on the revised answer. An
        `abandoned` session can never be revised (`AnswerNotRevisableError`)
        -- it was superseded by a newer session; reviving it would let a
        customer hold two `active` sessions at once, which the rest of
        this service assumes can never happen.

        Revising the session's very first message (`sequence_number ==
        1`, always the original free-text problem description in this
        story's flow) re-opens category resolution from scratch -- a
        different description may resolve to a different category
        entirely, so the previously resolved `category_id` is cleared
        along with everything after it.
        """
        profile, preferences = await self.customer_service.get_my_profile(user_id)
        session = await self._get_owned_session(session_id, profile.id)

        if session.status == ConversationStatus.ABANDONED:
            raise AnswerNotRevisableError()

        target = await self.message_repository.get_active_by_id(message_id)
        if (
            target is None
            or target.conversation_session_id != session.id
            or target.sender != MessageSender.CUSTOMER
        ):
            raise AnswerNotRevisableError()

        await self.message_repository.update(target, {"content": content})
        await self.message_repository.delete_after_sequence(
            session.id, target.sequence_number
        )

        if target.sequence_number == 1 and session.category_id is not None:
            session = await self.conversation_session_repository.update(
                session, {"category_id": None}
            )

        if session.status != ConversationStatus.ACTIVE:
            session = (
                await self.conversation_session_repository.clear_structured_criteria(
                    session
                )
            )
            session = await self.conversation_session_repository.update_status(
                session, ConversationStatus.ACTIVE
            )

        return await self._advance_turn(session, preferences.language)

    async def get_session(
        self, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> ConversationTurnView:
        """
        Resumes/reviews a session (after app restart, or to review the
        transcript, ADR-015): `ensure_owner_or_not_found`, never a 403.

        For a still-`active` session, the current turn's
        `quick_reply_options` are recovered by replaying
        `ConversationAiClient.process_turn` read-only against the
        unchanged history (see `ConversationTurnView`'s docstring) --
        `None` for a `completed`/`routed_to_admin`/`abandoned` session,
        since no further turn is ever expected.
        """
        profile, preferences = await self.customer_service.get_my_profile(user_id)
        session = await self._get_owned_session(session_id, profile.id)

        if session.status != ConversationStatus.ACTIVE:
            return await self._to_view(session, quick_reply_options=None)

        quick_reply_options = await self._peek_quick_reply_options(
            session, preferences.language
        )
        return await self._to_view(session, quick_reply_options=quick_reply_options)

    # -- internal helpers -----------------------------------------------

    async def _get_owned_session(
        self, session_id: uuid.UUID, customer_id: uuid.UUID
    ) -> ConversationSession:
        session = await self.conversation_session_repository.get_by_id(session_id)
        ensure_owner_or_not_found(
            session.customer_id if session is not None else None,
            customer_id,
            not_found_exc=ConversationSessionNotFoundError(),
        )
        assert session is not None  # narrows for type-checkers; guaranteed above
        return session

    async def _append_customer_message(
        self, session: ConversationSession, content: str
    ) -> Message:
        next_sequence = await self.message_repository.get_next_sequence_number(
            session.id
        )
        return await self.message_repository.create(
            {
                "conversation_session_id": session.id,
                "sender": MessageSender.CUSTOMER,
                "content": content,
                "sequence_number": next_sequence,
            }
        )

    async def _load_taxonomy(self) -> tuple[list[Category], TemplatesByCategory]:
        """
        The full active-category taxonomy plus every category's
        follow-up question templates, keyed by `category_id` -- what
        `ConversationAiClient.process_turn` needs to resolve a category
        and/or walk its required questions without ever inventing one
        (AC4/AC10). Small (14 categories, ~47 templates in the seeded
        v1 taxonomy), refetched every turn rather than cached, favoring
        correctness/simplicity over a premature optimization.
        """
        categories = await self.category_service.list_active_categories()
        templates_by_category = {
            category.id: await self.category_service.get_question_templates(category.id)
            for category in categories
        }
        return categories, templates_by_category

    async def _advance_turn(
        self, session: ConversationSession, language: LanguageCode
    ) -> ConversationTurnView:
        """
        The shared core of every turn-producing action
        (`start_conversation`/`submit_turn`/`revise_answer`): loads the
        taxonomy and full history, asks the `ConversationAiClient` for
        the next turn, persists its reply, records a newly resolved
        category, computes and persists a `confidence_scores` row
        (caching the latest value on the session itself), then applies
        Decision 4's completion policy.
        """
        categories, templates_by_category = await self._load_taxonomy()
        history = list(await self.message_repository.list_for_session(session.id))

        result = await self._process_turn(
            session, history, categories, templates_by_category, language
        )

        if result.resolved_category_id is not None and session.category_id is None:
            session = await self.conversation_session_repository.set_category(
                session, result.resolved_category_id
            )

        next_sequence = await self.message_repository.get_next_sequence_number(
            session.id
        )
        await self.message_repository.create(
            {
                "conversation_session_id": session.id,
                "sender": MessageSender.AI,
                "content": self._localize_reply(result, language),
                "sequence_number": next_sequence,
            }
        )

        await self.confidence_score_repository.create(
            {
                "conversation_session_id": session.id,
                "score": result.confidence,
                "model_version": MODEL_VERSION,
            }
        )
        session = await self.conversation_session_repository.update_final_confidence(
            session, result.confidence
        )

        session = await self._apply_completion_policy(
            session, categories, templates_by_category
        )
        quick_reply_options = (
            result.quick_reply_options
            if session.status == ConversationStatus.ACTIVE
            else None
        )
        return await self._to_view(session, quick_reply_options=quick_reply_options)

    async def _to_view(
        self, session: ConversationSession, *, quick_reply_options: list[str] | None
    ) -> ConversationTurnView:
        messages = list(await self.message_repository.list_for_session(session.id))
        search_request_id = (
            await self.search_request_service.get_search_request_id_for_session(
                session.id
            )
        )
        return ConversationTurnView(
            session=session,
            messages=messages,
            quick_reply_options=quick_reply_options,
            search_request_id=search_request_id,
        )

    async def _process_turn(
        self,
        session: ConversationSession,
        history: list[Message],
        categories: list[Category],
        templates_by_category: TemplatesByCategory,
        language: LanguageCode,
    ) -> ConversationTurnResult:
        """Thin wrapper around `ConversationAiClient.process_turn` that
        resolves `customer_message` from the history's last customer
        message -- shared by `_advance_turn` (real turn) and
        `_peek_quick_reply_options` (read-only replay for `GET`)."""
        last_customer_message = self._last_customer_message(history)
        return await self.conversation_ai_client.process_turn(
            session=session,
            history=history,
            categories=categories,
            question_templates_by_category=templates_by_category,
            customer_message=(
                last_customer_message.content
                if last_customer_message is not None
                else ""
            ),
            language=language,
        )

    async def _peek_quick_reply_options(
        self, session: ConversationSession, language: LanguageCode
    ) -> list[str] | None:
        """
        Read-only replay of the current turn's `ConversationAiClient
        .process_turn` call, purely to recover its `quick_reply_options`
        for `GET /conversations/{id}` (see `ConversationTurnView`'s
        docstring) -- creates no message, no confidence row, and never
        calls `_apply_completion_policy`.
        """
        categories, templates_by_category = await self._load_taxonomy()
        history = list(await self.message_repository.list_for_session(session.id))
        result = await self._process_turn(
            session, history, categories, templates_by_category, language
        )
        return result.quick_reply_options

    async def _apply_completion_policy(
        self,
        session: ConversationSession,
        categories: list[Category],
        templates_by_category: TemplatesByCategory,
    ) -> ConversationSession:
        """
        Decision 4 (`AI-001`): confidence-threshold completion first,
        then the hard turn cap. Both are one-way transitions out of
        `active` -- this never re-fires on a session that is already
        `completed`/`routed_to_admin`.

        **AI-002, Decision 1:** immediately after either transition, calls
        `search_request_service.handle_session_completed(...)` -- the
        single call site wiring `conversation -> search`. Both branches
        call the same method, passing only plain primitives (never the
        `ConversationSession` ORM object itself), so a `search_requests`
        row (and, for the low-confidence path, a
        `manual_match_assignments` row) always exists the moment a
        session leaves `active` -- AC2's "never left in limbo with no
        next step."
        """
        if session.status != ConversationStatus.ACTIVE:
            return session

        if (
            session.category_id is not None
            and session.final_confidence_score is not None
            and session.final_confidence_score
            >= settings.CONVERSATION_CONFIDENCE_THRESHOLD
        ):
            completed = await self._complete_session(
                session, categories, templates_by_category
            )
            await self._handoff_to_search(completed, categories)
            return completed

        turn_count = await self._count_customer_turns(session.id)
        if turn_count >= settings.CONVERSATION_MAX_TURNS:
            routed = await self.conversation_session_repository.update_status(
                session, ConversationStatus.ROUTED_TO_ADMIN
            )
            await self._handoff_to_search(routed, categories)
            return routed

        return session

    async def _handoff_to_search(
        self, session: ConversationSession, categories: list[Category]
    ) -> None:
        """
        AI-002, Decision 1's single `conversation -> search` call site.
        `search` receives plain primitives only (`session.id`, `session.
        customer_id`, `category_id`, `category_name`, `structured_
        criteria`, and `session.status.value`, a plain string) -- never a
        `ConversationSession` ORM object -- so `search` has zero imports
        from `conversation`. `category_name` is `None` for the rare
        `routed_to_admin` session that hit `AI-001`'s hard turn cap
        without ever resolving a category at all.
        """
        category_name = next(
            (c.name for c in categories if c.id == session.category_id), None
        )
        await self.search_request_service.handle_session_completed(
            conversation_session_id=session.id,
            customer_id=session.customer_id,
            status=session.status.value,
            category_id=session.category_id,
            category_name=category_name,
            structured_criteria=session.structured_criteria,
        )

    async def _complete_session(
        self,
        session: ConversationSession,
        categories: list[Category],
        templates_by_category: TemplatesByCategory,
    ) -> ConversationSession:
        """Builds and validates `StructuredCriteria` (Decision 1b, AC9)
        from the resolved category and every answered required question,
        then atomically completes the session."""
        category = next((c for c in categories if c.id == session.category_id), None)
        if category is None:
            # Defensive: `session.category_id` was set moments earlier in
            # `_advance_turn` from this same taxonomy snapshot.
            raise InvalidStructuredCriteriaError()

        required_templates = sorted(
            (t for t in templates_by_category.get(category.id, []) if t.is_required),
            key=lambda t: t.sort_order,
        )
        history = list(await self.message_repository.list_for_session(session.id))
        customer_messages = sorted(
            (m for m in history if m.sender == MessageSender.CUSTOMER),
            key=lambda m: m.sequence_number,
        )
        # The most recent `len(required_templates)` customer messages are
        # always the actual required-question answers, in order (Decision
        # 2's one-at-a-time walk) -- regardless of how many earlier
        # messages were spent on the free-text description or an
        # ambiguous category clarification round, this only ever exists
        # once every required question is already answered (the
        # confidence-threshold gate above), so taking the tail is always
        # correct without needing to replay category-resolution matching
        # here (that logic stays inside `RuleBasedConversationAiClient`,
        # never duplicated across the Protocol boundary).
        answers = (
            customer_messages[-len(required_templates) :] if required_templates else []
        )

        try:
            structured_criteria = StructuredCriteria(
                category_id=category.id,
                category_slug=category.slug,
                answers=[
                    StructuredCriteriaAnswer(
                        question_id=template.id,
                        question_text=template.question_text,
                        answer_text=answer.content,
                    )
                    for template, answer in zip(
                        required_templates, answers, strict=True
                    )
                ],
            )
        except ValidationError as exc:
            raise InvalidStructuredCriteriaError() from exc

        return await self.conversation_session_repository.complete_session(
            session,
            structured_criteria=structured_criteria.model_dump(mode="json"),
        )

    async def _count_customer_turns(self, session_id: uuid.UUID) -> int:
        history = await self.message_repository.list_for_session(session_id)
        return sum(1 for m in history if m.sender == MessageSender.CUSTOMER)

    @staticmethod
    def _last_customer_message(history: list[Message]) -> Message | None:
        customer_messages = [m for m in history if m.sender == MessageSender.CUSTOMER]
        return customer_messages[-1] if customer_messages else None

    @staticmethod
    def _localize_reply(result: ConversationTurnResult, language: LanguageCode) -> str:
        if language == LanguageCode.AR and result.reply_message_ar:
            return result.reply_message_ar
        return result.reply_message
