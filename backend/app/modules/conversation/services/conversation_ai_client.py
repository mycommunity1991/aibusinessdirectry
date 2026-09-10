"""
LLM-provider abstraction and interim implementation (AI-001, Decision 2).

No LLM provider, SDK, or credential is confirmed anywhere in this
codebase (Open Question 1, `Plan_S07_AI-001.md`). This module builds the
correct swappable *shape* for one to be plugged in later -- the fourth
application of the `FileStorage` (ADR-017) / `DocumentOcrService`
(ADR-018) / `GooglePlacesClient` (ADR-031) pattern -- rather than
guessing at or partially reverse-engineering a vendor integration that
isn't present.

`ConversationService` depends on the `ConversationAiClient` Protocol
only, never `RuleBasedConversationAiClient` directly (wired via
`conversation/dependencies.py:get_conversation_ai_client`) -- neither
API routes nor a future mobile screen ever import or reference a
concrete client. This satisfies AC2 directly: the Protocol boundary
itself, not the choice of implementation behind it, is what AC2
requires.

`RuleBasedConversationAiClient` is the only implementation this story
ships, and is "grounded by construction" (AC10), not merely by prompt
instruction: it has no free-text generation capability at all beyond
(a) echoing a `CategoryQuestionTemplate.question_text`/`question_text_ar`
value verbatim, and (b) quoting a real, resolved `Category.name`/
`name_ar` back to the customer. There is no code path anywhere in this
class that can emit a question, category, or fact absent from the
`category.categories`/`category_question_templates` rows it was handed
by `ConversationService` -- the handful of short, fixed English/Arabic
copy strings below (module-level constants, mirroring
`customer_service.DEFAULT_DISPLAY_NAME`'s established pattern for
necessary interim UI copy) are the only strings this class ever emits
that are not template/category data, and none of them assert any fact
about a category, question, or provider.

**Deviation from `Plan_S07_AI-001.md`'s literal `process_turn` signature
(flagged honestly, per this story's own execution instructions):** the
Plan's Decision 2 specifies `active_question: CategoryQuestionTemplate |
None` as a parameter. Implementing Decision 2's own described *behavior*
("walk `CategoryQuestionTemplate` rows in `sort_order`, one at a time"
and "confidence... rising in equal steps as required questions are
answered") turned out to be impossible from a single `active_question`
value alone -- the client also needs the resolved category's *entire*
ordered required-question list to know both "what comes next" and "how
many are left", and (for the same-turn category-resolution case) there
is no `active_question` yet to hand it at all, since the category is
being resolved for the first time *in this very call*. This class
therefore receives `question_templates_by_category: dict[uuid.UUID,
list[CategoryQuestionTemplate]]` instead (every active category's
templates, keyed by `category_id`) -- small (14 categories, ~47 rows
total in the seeded taxonomy), and it closes the circular dependency
cleanly: a category resolved *in this same call* already has its
templates available for the very next line of this method to use.
`ConversationService` is the one that assembles this dict (via
`CategoryService`, Decision 3). No other part of Decision 2's design
changes.
"""

import uuid
from typing import Protocol

from pydantic import BaseModel, Field

from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.conversation.models import ConversationSession, Message, MessageSender
from app.modules.identity.models import LanguageCode

# Fixed, non-fabricating interim copy (Decision 2b: this client has no
# prompts to version-control -- AC3 is an honest, documented gap). None
# of these strings assert any fact about a category, question, or
# provider; they only ever wrap verbatim template/category data.
_CLARIFY_CATEGORY_EN = (
    "We couldn't quite match that to one of our services. "
    "Please choose the closest match below."
)
_CLARIFY_CATEGORY_AR = (
    "لم نتمكن من مطابقة ذلك تمامًا مع إحدى خدماتنا. يرجى اختيار الأقرب من القائمة أدناه."
)
_ALL_DONE_EN = "Thanks -- that's everything we need to find the right provider for you."
_ALL_DONE_AR = "شكرًا لك — هذا كل ما نحتاجه للعثور على المزود المناسب لك."

MODEL_VERSION = "rule_based_v1"


class ConversationTurnResult(BaseModel):
    """
    One AI turn's outcome (Decision 2). `reply_message`/`reply_message_ar`
    are the same underlying content in each supported language --
    `ConversationService` picks one to persist as `messages.content`
    based on the session's resolved `language` (Decision 6); neither
    field is ever shown directly to the customer without that selection.
    """

    reply_message: str = Field(..., description="The AI's reply, in English.")
    reply_message_ar: str | None = Field(
        None,
        description=(
            "The AI's reply, in Arabic, if available for this turn. "
            "`None` falls back to `reply_message` (Decision 6)."
        ),
    )
    resolved_category_id: uuid.UUID | None = Field(
        None,
        description=(
            "The category this session is resolved to, if known -- "
            "either already resolved on the session, or newly resolved "
            "this turn."
        ),
    )
    is_complete: bool = Field(
        ...,
        description=(
            "Whether this AI client believes the conversation has "
            "gathered everything it needs. `ConversationService`'s own "
            "completion decision is driven by `confidence` against "
            "`settings.CONVERSATION_CONFIDENCE_THRESHOLD` (Decision 4), "
            "not this flag directly -- for this story's interim client "
            "the two always agree, since confidence is only ever 0.0 or "
            "1.0."
        ),
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="A genuine, auditable confidence score."
    )
    quick_reply_options: list[str] | None = Field(
        None,
        description=(
            "Chip choices for the mobile UI to render -- either the "
            "active category list (category-pick clarification) or a "
            "`single_select`/`multi_select` question's `options`. `None` "
            "when the current turn expects free text."
        ),
    )


class ConversationAiClient(Protocol):
    """Swappable LLM-provider abstraction (Decision 2, AC2)."""

    async def process_turn(
        self,
        *,
        session: ConversationSession,
        history: list[Message],
        categories: list[Category],
        question_templates_by_category: dict[uuid.UUID, list[CategoryQuestionTemplate]],
        customer_message: str,
        language: LanguageCode,
    ) -> ConversationTurnResult:
        """Produces the next AI turn for a session, given its full
        message history and the category taxonomy needed to ground any
        question/category the reply might reference."""
        ...


class RuleBasedConversationAiClient:
    """
    The only `ConversationAiClient` implementation this story ships
    (Decision 2). Fully deterministic: no external network call, no
    natural-language generation, no invented question or fact (AC10).
    """

    async def process_turn(
        self,
        *,
        session: ConversationSession,
        history: list[Message],
        categories: list[Category],
        question_templates_by_category: dict[uuid.UUID, list[CategoryQuestionTemplate]],
        customer_message: str,
        language: LanguageCode,
    ) -> ConversationTurnResult:
        if session.category_id is None:
            return self._resolve_category(
                categories, question_templates_by_category, customer_message, language
            )

        templates = question_templates_by_category.get(session.category_id, [])
        answered_count = self._count_answered_required_questions(categories, history)
        return self._advance(
            resolved_category_id=session.category_id,
            templates=templates,
            answered_count=answered_count,
            language=language,
        )

    def _resolve_category(
        self,
        categories: list[Category],
        question_templates_by_category: dict[uuid.UUID, list[CategoryQuestionTemplate]],
        customer_message: str,
        language: LanguageCode,
    ) -> ConversationTurnResult:
        """
        Case-insensitive substring match of the customer's free text
        against each active category's `name`/`name_ar`/`slug` (Decision
        2). Zero or multiple matches never guess -- they return a
        clarifying, quick-reply category-pick prompt instead (AC4).
        """
        matches = [c for c in categories if self._category_matches(c, customer_message)]

        if len(matches) != 1:
            return ConversationTurnResult(
                reply_message=_CLARIFY_CATEGORY_EN,
                reply_message_ar=_CLARIFY_CATEGORY_AR,
                resolved_category_id=None,
                is_complete=False,
                confidence=0.0,
                quick_reply_options=[
                    self._localize(c.name, c.name_ar, language) for c in categories
                ],
            )

        category = matches[0]
        templates = question_templates_by_category.get(category.id, [])
        return self._advance(
            resolved_category_id=category.id,
            templates=templates,
            answered_count=0,
            language=language,
        )

    def _advance(
        self,
        *,
        resolved_category_id: uuid.UUID,
        templates: list[CategoryQuestionTemplate],
        answered_count: int,
        language: LanguageCode,
    ) -> ConversationTurnResult:
        """
        Walks a resolved category's `is_required=true` templates in
        `sort_order`, one at a time, verbatim (AC4) -- never phrases or
        invents a question. Confidence is `0.0` while unresolved, rising
        in equal steps as required questions are answered, `1.0` once
        every required question has a persisted answer (Decision 2).
        """
        required = sorted(
            (t for t in templates if t.is_required), key=lambda t: t.sort_order
        )

        if not required or answered_count >= len(required):
            return ConversationTurnResult(
                reply_message=_ALL_DONE_EN,
                reply_message_ar=_ALL_DONE_AR,
                resolved_category_id=resolved_category_id,
                is_complete=True,
                confidence=1.0,
                quick_reply_options=None,
            )

        next_question = required[answered_count]
        confidence = answered_count / len(required)
        return ConversationTurnResult(
            reply_message=next_question.question_text,
            reply_message_ar=next_question.question_text_ar,
            resolved_category_id=resolved_category_id,
            is_complete=False,
            confidence=confidence,
            quick_reply_options=self._quick_replies(next_question),
        )

    def _count_answered_required_questions(
        self, categories: list[Category], history: list[Message]
    ) -> int:
        """
        Deterministically replays the same category-matching logic this
        client already used to resolve the session's category, to find
        which customer message in `history` was the resolving one (the
        `messages` schema has no column recording this -- it is not
        needed, since replay is deterministic and side-effect-free). The
        count returned is the number of customer messages that arrived
        *after* that one -- each one, in order, is an answer to exactly
        one required question (Decision 2's one-at-a-time walk).
        """
        customer_messages = sorted(
            (m for m in history if m.sender == MessageSender.CUSTOMER),
            key=lambda m: m.sequence_number,
        )

        resolution_index: int | None = None
        for index, message in enumerate(customer_messages):
            matches = [
                c for c in categories if self._category_matches(c, message.content)
            ]
            if len(matches) == 1:
                resolution_index = index
                break

        if resolution_index is None:
            # Defensive: should never happen once `session.category_id`
            # is set, since that can only have been set by this same
            # matching logic succeeding on some prior customer message.
            return 0

        return len(customer_messages) - resolution_index - 1

    @staticmethod
    def _category_matches(category: Category, customer_message: str) -> bool:
        text = customer_message.strip().lower()
        if not text:
            return False
        candidates = (category.name, category.name_ar, category.slug)
        return any(candidate and candidate.lower() in text for candidate in candidates)

    @staticmethod
    def _quick_replies(template: CategoryQuestionTemplate) -> list[str] | None:
        """
        `options` is only populated for `single_select`/`multi_select`
        questions (`CategoryQuestionTemplate`'s own docstring) and is
        English-only in the seeded taxonomy today (no `options_ar`
        column exists) -- returned verbatim, never translated or
        reworded.
        """
        if not template.options:
            return None
        return list(template.options)

    @staticmethod
    def _localize(value_en: str, value_ar: str | None, language: LanguageCode) -> str:
        """Decision 6: Arabic when requested and populated, English
        fallback otherwise -- `name_ar`/`question_text_ar` are nullable
        until populated, never a hard failure."""
        if language == LanguageCode.AR and value_ar:
            return value_ar
        return value_en
