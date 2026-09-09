"""
Integration tests for `CategoryService`/`CategoryRepository`/
`CategoryQuestionTemplateRepository` (CTG-001, AC2/AC3/AC5/AC7),
exercised against a real Postgres database (see `tests/conftest.py`'s
`db_session` fixture).

Seeds the ordinary test database directly from
`app.modules.category.seed_data` via the ORM (never via the
`category_domain` migration -- the ordinary test fixtures never run
Alembic; they build every domain's schema via `Base.metadata.
create_all()`, per `tests/conftest.py`'s `db_engine` fixture).
"""

import uuid

from app.modules.category import seed_data
from app.modules.category.models import Category, CategoryQuestionTemplate
from app.modules.category.repositories.category_question_template_repository import (
    CategoryQuestionTemplateRepository,
)
from app.modules.category.repositories.category_repository import CategoryRepository
from app.modules.category.services.category_service import CategoryService


async def _seed_taxonomy(db_session) -> dict[str, uuid.UUID]:
    """Seeds the real test database directly from `seed_data.py`,
    mirroring exactly what the `category_domain` migration's own seed
    step does, minus the `ON CONFLICT` idempotency machinery (irrelevant
    here -- each test starts from an empty, freshly-truncated schema).
    Returns a `slug -> category_id` map for tests to look up questions
    by category.
    """
    slug_to_id: dict[str, uuid.UUID] = {}
    for category_data in seed_data.CATEGORY_SEED:
        category = Category(**category_data)
        db_session.add(category)
        await db_session.flush()
        slug_to_id[category_data["slug"]] = category.id

    for slug, questions in seed_data.QUESTION_SEED_BY_SLUG.items():
        category_id = slug_to_id[slug]
        for question_data in questions:
            db_session.add(
                CategoryQuestionTemplate(category_id=category_id, **question_data)
            )

    await db_session.commit()
    return slug_to_id


def _make_service(db_session) -> CategoryService:
    return CategoryService(
        CategoryRepository(db_session),
        CategoryQuestionTemplateRepository(db_session),
    )


class TestListActiveCategories:
    async def test_returns_all_14_categories_in_sort_order(self, db_session) -> None:
        await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        categories = await service.list_active_categories()

        assert len(categories) == 14
        assert [c.sort_order for c in categories] == list(range(14))
        assert [c.slug for c in categories] == [
            entry["slug"] for entry in seed_data.CATEGORY_SEED
        ]

    async def test_bilingual_names_match_the_seed_data(self, db_session) -> None:
        await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        categories = await service.list_active_categories()
        by_slug = {c.slug: c for c in categories}

        plumbing = by_slug["plumbing"]
        assert plumbing.name == "Plumbing"
        assert plumbing.name_ar == "السباكة"

        tailoring = by_slug["tailoring-alterations"]
        assert tailoring.name == "Tailoring & Alterations"
        assert tailoring.name_ar == "الخياطة والتعديلات"


class TestGetQuestionTemplates:
    async def test_plumbing_questions_cover_single_select_text_and_optional(
        self, db_session
    ) -> None:
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        questions = await service.get_question_templates(slug_to_id["plumbing"])

        assert len(questions) == len(seed_data.QUESTION_SEED_BY_SLUG["plumbing"])
        assert [q.sort_order for q in questions] == [0, 1, 2, 3]
        assert questions[0].question_text == "What's the issue?"
        assert questions[0].question_text_ar == "ما هي المشكلة؟"
        assert questions[0].question_type == "single_select"
        assert questions[0].options == ["Leak", "Blockage", "Installation", "Other"]
        assert questions[0].is_required is True
        # The final question is optional free text -- both is_required
        # states must be exercised (Decision 5).
        assert questions[3].question_type == "text"
        assert questions[3].options is None
        assert questions[3].is_required is False

    async def test_painting_questions_cover_multi_select(self, db_session) -> None:
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        questions = await service.get_question_templates(slug_to_id["painting"])

        assert len(questions) == len(seed_data.QUESTION_SEED_BY_SLUG["painting"])
        assert questions[0].question_type == "multi_select"
        assert questions[0].options == [
            "Walls",
            "Ceiling",
            "Doors / windows",
            "Furniture",
            "Exterior",
        ]

    async def test_moving_packing_questions_cover_boolean(self, db_session) -> None:
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        questions = await service.get_question_templates(slug_to_id["moving-packing"])

        assert len(questions) == len(seed_data.QUESTION_SEED_BY_SLUG["moving-packing"])
        boolean_question = questions[1]
        assert boolean_question.question_text == "Do you need packing service too?"
        assert boolean_question.question_type == "boolean"
        assert boolean_question.options is None
        assert boolean_question.is_required is True

    async def test_tutoring_questions_are_correctly_ordered(self, db_session) -> None:
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        questions = await service.get_question_templates(
            slug_to_id["tutoring-private-lessons"]
        )

        expected = seed_data.QUESTION_SEED_BY_SLUG["tutoring-private-lessons"]
        assert len(questions) == len(expected)
        assert [q.question_text for q in questions] == [
            q["question_text"] for q in expected
        ]
        assert [q.question_type for q in questions] == [
            q["question_type"] for q in expected
        ]

    async def test_unknown_category_id_returns_empty_list_not_error(
        self, db_session
    ) -> None:
        await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        questions = await service.get_question_templates(uuid.uuid4())

        assert questions == []


class TestSeedCompleteness:
    async def test_every_category_has_the_exact_seeded_question_count(
        self, db_session
    ) -> None:
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        for slug, expected_questions in seed_data.QUESTION_SEED_BY_SLUG.items():
            questions = await service.get_question_templates(slug_to_id[slug])
            assert len(questions) == len(expected_questions), slug

    async def test_every_question_has_non_null_bilingual_text(
        self, db_session
    ) -> None:
        """`17_CATEGORY_TAXONOMY.md` v1.1.0 added real first-pass Arabic
        text for all 47 questions (previously `NULL` -- a gap in v1.0.0
        of that document, now resolved). Every seeded question must
        carry non-empty `question_text_ar`."""
        slug_to_id = await _seed_taxonomy(db_session)
        service = _make_service(db_session)

        for slug in seed_data.QUESTION_SEED_BY_SLUG:
            questions = await service.get_question_templates(slug_to_id[slug])
            for question in questions:
                assert question.question_text_ar, (slug, question.question_text)

    async def test_no_category_uses_the_number_question_type(self) -> None:
        """Documents a fact about the real seed data (Decision 5): none
        of the 14 categories' questions use `question_type='number'`,
        so no test exercises that type -- not a test gap."""
        used_types = {
            question["question_type"]
            for questions in seed_data.QUESTION_SEED_BY_SLUG.values()
            for question in questions
        }
        assert "number" not in used_types
        assert used_types == {"single_select", "multi_select", "text", "boolean"}
