"""
Forbidden customer-facing terminology test (AI-002, Decision 7,
`Plan_S07_AI-002.md`, AC3/AC7) -- a structural, automated proof that
"manual", "fallback", and "admin" (case-insensitive) never appear in any
copy the customer actually sees, not a manual copy-review checklist
(which AC7 explicitly requires be automated).

**Scope, and one documented, deliberate deviation from the Plan's
literal phrasing:** Decision 7's own text says this test scans "every
hardcoded string literal in `conversation/schemas.py`, `search/
schemas.py`". Read completely literally, that is impossible to satisfy:
`ManualMatchAssignmentSummaryResponse`/`ResolveManualMatchRequest`
(Decision 3's admin-only schemas) *must* document themselves using
exactly those words in their class docstrings and `Field(description=
...)` text -- that is legitimate developer-facing OpenAPI documentation
for an admin-only endpoint, never rendered anywhere in the mobile app or
returned inside a customer-facing response *value*. AC3's own wording is
specific: "in customer-facing copy" -- this test targets exactly that
(rendered reply/message copy and live JSON response *values* a customer
can see), not every string literal in a source file regardless of
whether a customer could ever observe it. This is recorded here plainly,
per this project's standing "flag a genuine Plan/reality mismatch,
don't silently paper over it" discipline.
"""

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.constants import ROLE_CUSTOMER
from app.core.exceptions import (
    AnswerNotRevisableError,
    ConversationSessionNotActiveError,
    ConversationSessionNotFoundError,
    InvalidStructuredCriteriaError,
    SearchRequestNotFoundError,
)
from app.core.security import create_access_token
from app.database.session import get_db
from app.main import app
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.conversation.services.conversation_ai_client import (
    _ALL_DONE_AR,
    _ALL_DONE_EN,
    _CLARIFY_CATEGORY_AR,
    _CLARIFY_CATEGORY_EN,
)
from app.modules.identity.models import AuthProvider, User

_FORBIDDEN_WORDS = ("manual", "fallback", "admin")

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_CONVERSATION_API = _BACKEND_ROOT / "app/modules/conversation/api.py"
_SEARCH_REQUEST_API = _BACKEND_ROOT / "app/modules/search/search_request_api.py"


def _contains_forbidden_word(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _FORBIDDEN_WORDS)


def _extract_message_kwarg_literals(file_path: Path) -> list[str]:
    """AST-extracts every string literal passed as a `message=` keyword
    argument in the given customer-facing route file -- the actual
    `SuccessResponse`/`CollectionResponse` copy a customer's HTTP client
    receives, as opposed to internal docstrings/OpenAPI `description=`
    text no customer ever sees."""
    tree = ast.parse(file_path.read_text())
    literals: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg == "message"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            literals.append(node.value.value)
    return literals


_INTERNAL_IDENTIFIER_KEYS = frozenset({"status"})


def _assert_no_forbidden_value(payload: object, *, path: str = "$") -> None:
    """
    Recursively checks every string *value* in a decoded JSON payload --
    deliberately never checks dict keys (field names are backend-internal
    identifiers, exempted by AC3's own "in customer-facing copy"
    wording), and skips the `status` key's own value specifically: its
    enum members (`routed_to_admin`/`pending_manual_match`) are
    themselves backend-internal identifiers per Decision 7's explicit
    carve-out, not rendered copy -- the mobile client maps `status` to
    its own honest, compliant user-facing string, never displaying the
    raw enum value directly.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in _INTERNAL_IDENTIFIER_KEYS:
                continue
            _assert_no_forbidden_value(value, path=f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _assert_no_forbidden_value(item, path=f"{path}[{index}]")
    elif isinstance(payload, str):
        assert not _contains_forbidden_word(payload), (
            f"forbidden word found in customer-facing response at {path}: {payload!r}"
        )


class TestFixedAiClientCopy:
    """The only free-standing copy strings `RuleBasedConversationAiClient`
    can ever emit beyond verbatim template/category data (Decision 2b of
    `AI-001`) -- none may introduce a forbidden word."""

    @pytest.mark.parametrize(
        "text",
        [_CLARIFY_CATEGORY_EN, _CLARIFY_CATEGORY_AR, _ALL_DONE_EN, _ALL_DONE_AR],
    )
    def test_no_forbidden_word(self, text: str) -> None:
        assert not _contains_forbidden_word(text)


class TestCustomerFacingExceptionMessages:
    """Every exception a *customer*-facing conversation/search-request
    route can raise -- `ManualMatchAssignmentNotFoundError`/
    `ManualMatchAssignmentAlreadyResolvedError` are deliberately excluded:
    they are only ever raised on the admin-only `/admin/search/
    manual-matches` routes, never returned to a customer caller."""

    @pytest.mark.parametrize(
        "exc",
        [
            ConversationSessionNotActiveError(),
            AnswerNotRevisableError(),
            ConversationSessionNotFoundError(),
            InvalidStructuredCriteriaError(),
            SearchRequestNotFoundError(),
        ],
    )
    def test_no_forbidden_word(self, exc: Exception) -> None:
        assert not _contains_forbidden_word(str(exc))


class TestCustomerFacingRouteMessageLiterals:
    """Static scan of the `message=` copy literally returned by every
    customer-facing conversation/search-request route (never the
    admin-only routes, whose own documentation legitimately discusses
    admin/manual concepts)."""

    @pytest.mark.parametrize("file_path", [_CONVERSATION_API, _SEARCH_REQUEST_API])
    def test_no_forbidden_word_in_message_literals(self, file_path: Path) -> None:
        literals = _extract_message_kwarg_literals(file_path)
        assert literals, f"expected at least one message= literal in {file_path}"
        for literal in literals:
            assert not _contains_forbidden_word(literal), (file_path, literal)


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


async def _create_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_category(db_session, *, question_count: int = 3) -> Category:
    category = Category(
        name="Plumbing", name_ar=None, slug="plumbing-forbidden-copy", sort_order=0
    )
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
    return category


def _headers(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        subject=str(user_id), roles=[ROLE_CUSTOMER], jti=str(uuid.uuid4())
    )
    return {"Authorization": f"Bearer {token}"}


class TestLiveRoutedToAdminResponseHasNoForbiddenTerminology:
    """AC3/AC7's own explicit requirement: a live `routed_to_admin`/
    `pending_manual_match` HTTP response, exercised end to end -- not
    just static string literals."""

    async def test_full_round_trip(
        self, client: TestClient, db_session, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "CONVERSATION_MAX_TURNS", 1)
        user = await _create_user(db_session, "940000001")
        await _seed_category(db_session, question_count=5)

        started = client.post(
            "/api/v1/conversations",
            headers=_headers(user.id),
            json={"message": "Something ambiguous nobody can categorize"},
        )
        assert started.status_code == 201
        started_body = started.json()
        session_data = started_body["data"]
        assert session_data["status"] == "routed_to_admin"
        _assert_no_forbidden_value(started_body)

        search_request_id = session_data["search_request_id"]
        assert search_request_id is not None

        result = client.get(
            f"/api/v1/search-requests/{search_request_id}",
            headers=_headers(user.id),
        )
        assert result.status_code == 200
        result_body = result.json()
        assert result_body["data"]["status"] == "pending_manual_match"
        _assert_no_forbidden_value(result_body)
