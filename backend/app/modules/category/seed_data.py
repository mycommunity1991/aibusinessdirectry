"""
Canonical seed data for the v1 launch Category taxonomy (CTG-001).

Transcribed verbatim from `docs/AI/17_CATEGORY_TAXONOMY.md` (the
CTO-locked, authoritative source for the 14 launch categories and their
AI follow-up question templates). This module intentionally contains
**no SQLAlchemy or ORM import** -- it is plain Python data only, so it
can be safely imported both by the `category_domain` Alembic migration
(which, matching every existing migration's own convention, never
imports `app.modules.*.models`) and by test fixtures
(`tests/modules/category/test_category_service.py`), without ever
transcribing this data a second time (`08_CODING_STANDARDS.md`: never
duplicate code/data).

**Arabic content caveat (Decision 4, `Plan_S07_CTG-001.md`):** both
`name_ar` (categories) and `question_text_ar` (question templates)
below are populated with `17_CATEGORY_TAXONOMY.md` v1.1.0's first-pass
Arabic text -- this is a first-pass translation, not yet
native-speaker-verified; do not treat as launch-final.

(Historical note: v1.0.0 of `17_CATEGORY_TAXONOMY.md` did not actually
include any `question_text_ar` content despite its own prose claiming
the caveat covered it -- `question_text_ar` was seeded `NULL` for all
47 questions in this module's first version rather than fabricate
translations that had no source. v1.1.0 added the missing per-question
Arabic text; that gap is now resolved and `question_text_ar` is
populated below like every other bilingual field.)
"""

from typing import Any

CATEGORY_SEED: list[dict[str, Any]] = [
    {
        "slug": "plumbing",
        "name": "Plumbing",
        "name_ar": "السباكة",
        "sort_order": 0,
    },
    {
        "slug": "electrical",
        "name": "Electrical",
        "name_ar": "الكهرباء",
        "sort_order": 1,
    },
    {
        "slug": "ac-repair-maintenance",
        "name": "AC Repair & Maintenance",
        "name_ar": "تكييف الهواء - الصيانة والإصلاح",
        "sort_order": 2,
    },
    {
        "slug": "carpentry",
        "name": "Carpentry",
        "name_ar": "النجارة",
        "sort_order": 3,
    },
    {
        "slug": "painting",
        "name": "Painting",
        "name_ar": "الدهان",
        "sort_order": 4,
    },
    {
        "slug": "handyman-general-repairs",
        "name": "Handyman / General Repairs",
        "name_ar": "أعمال الصيانة العامة",
        "sort_order": 5,
    },
    {
        "slug": "home-cleaning",
        "name": "Home Cleaning",
        "name_ar": "تنظيف المنزل",
        "sort_order": 6,
    },
    {
        "slug": "pest-control",
        "name": "Pest Control",
        "name_ar": "مكافحة الحشرات",
        "sort_order": 7,
    },
    {
        "slug": "appliance-repair",
        "name": "Appliance Repair",
        "name_ar": "إصلاح الأجهزة المنزلية",
        "sort_order": 8,
    },
    {
        "slug": "moving-packing",
        "name": "Moving & Packing",
        "name_ar": "النقل والتغليف",
        "sort_order": 9,
    },
    {
        "slug": "tutoring-private-lessons",
        "name": "Tutoring & Private Lessons",
        "name_ar": "الدروس الخصوصية",
        "sort_order": 10,
    },
    {
        "slug": "salon-barbershop",
        "name": "Salon & Barbershop",
        "name_ar": "صالون وحلاقة",
        "sort_order": 11,
    },
    {
        "slug": "car-service-garage",
        "name": "Car Service & Garage",
        "name_ar": "صيانة السيارات",
        "sort_order": 12,
    },
    {
        "slug": "tailoring-alterations",
        "name": "Tailoring & Alterations",
        "name_ar": "الخياطة والتعديلات",
        "sort_order": 13,
    },
]

_URGENCY_OPTIONS = [
    "Emergency — need someone today",
    "Within a few days",
    "Just planning",
]
_LOCATION_OPTIONS = ["Home", "Office / Commercial"]

# Arabic question text repeated verbatim across multiple categories in
# `17_CATEGORY_TAXONOMY.md` v1.1.0 -- factored out once, mirroring
# `_URGENCY_OPTIONS`/`_LOCATION_OPTIONS` above, so it is never
# transcribed (and never risks diverging) across its several occurrences.
_URGENCY_QUESTION_AR = "ما مدى إلحاح الأمر؟"
_LOCATION_QUESTION_AR = "أين يقع الموقع؟"
_ANYTHING_ELSE_QUESTION_AR = "هل هناك أي تفاصيل إضافية تود إخبارنا بها؟"
_WHAT_DO_YOU_NEED_AR = "ما الذي تحتاجه؟"
_WHATS_THE_ISSUE_AR = "ما هي المشكلة؟"
_TIMELINE_QUESTION_AR = "ما هو الإطار الزمني المطلوب؟"

QUESTION_SEED_BY_SLUG: dict[str, list[dict[str, Any]]] = {
    "plumbing": [
        {
            "question_text": "What's the issue?",
            "question_text_ar": _WHATS_THE_ISSUE_AR,
            "question_type": "single_select",
            "options": ["Leak", "Blockage", "Installation", "Other"],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Where is this?",
            "question_text_ar": _LOCATION_QUESTION_AR,
            "question_type": "single_select",
            "options": _LOCATION_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
        {
            "question_text": "Anything else we should know?",
            "question_text_ar": _ANYTHING_ELSE_QUESTION_AR,
            "question_type": "text",
            "options": None,
            "is_required": False,
            "sort_order": 3,
        },
    ],
    "electrical": [
        {
            "question_text": "What do you need?",
            "question_text_ar": _WHAT_DO_YOU_NEED_AR,
            "question_type": "single_select",
            "options": [
                "Power outage / fault",
                "New installation",
                "Wiring repair",
                "Appliance connection",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Where is this?",
            "question_text_ar": _LOCATION_QUESTION_AR,
            "question_type": "single_select",
            "options": _LOCATION_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
        {
            "question_text": "Anything else we should know?",
            "question_text_ar": _ANYTHING_ELSE_QUESTION_AR,
            "question_type": "text",
            "options": None,
            "is_required": False,
            "sort_order": 3,
        },
    ],
    "ac-repair-maintenance": [
        {
            "question_text": "What's wrong?",
            "question_text_ar": "ما المشكلة؟",
            "question_type": "single_select",
            "options": [
                "Not cooling",
                "Not turning on",
                "Leaking water",
                "Routine maintenance / service",
                "New installation",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "What type of AC?",
            "question_text_ar": "ما نوع جهاز التكييف؟",
            "question_type": "single_select",
            "options": ["Split unit", "Central AC", "Window unit", "Not sure"],
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
        {
            "question_text": "Where is this?",
            "question_text_ar": _LOCATION_QUESTION_AR,
            "question_type": "single_select",
            "options": _LOCATION_OPTIONS,
            "is_required": True,
            "sort_order": 3,
        },
    ],
    "carpentry": [
        {
            "question_text": "What do you need?",
            "question_text_ar": _WHAT_DO_YOU_NEED_AR,
            "question_type": "single_select",
            "options": [
                "Furniture repair",
                "Custom furniture",
                "Door / window fixing",
                "Installation (shelves, cabinets)",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Anything else we should know?",
            "question_text_ar": _ANYTHING_ELSE_QUESTION_AR,
            "question_type": "text",
            "options": None,
            "is_required": False,
            "sort_order": 2,
        },
    ],
    "painting": [
        {
            "question_text": "What needs painting?",
            "question_text_ar": "ما الذي يحتاج إلى دهان؟",
            "question_type": "multi_select",
            "options": ["Walls", "Ceiling", "Doors / windows", "Furniture", "Exterior"],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "Approximately how much space?",
            "question_text_ar": "ما هي المساحة التقريبية؟",
            "question_type": "single_select",
            "options": [
                "Small touch-up",
                "Single room",
                "Whole apartment / villa",
                "Not sure",
            ],
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "What's your timeline?",
            "question_text_ar": _TIMELINE_QUESTION_AR,
            "question_type": "single_select",
            "options": ["As soon as possible", "Within 2 weeks", "Flexible"],
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "handyman-general-repairs": [
        {
            "question_text": "What needs fixing?",
            "question_text_ar": "ما الذي يحتاج إلى إصلاح؟",
            "question_type": "text",
            "options": None,
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Where is this?",
            "question_text_ar": _LOCATION_QUESTION_AR,
            "question_type": "single_select",
            "options": _LOCATION_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "home-cleaning": [
        {
            "question_text": "What type of cleaning?",
            "question_text_ar": "ما نوع التنظيف المطلوب؟",
            "question_type": "single_select",
            "options": [
                "Regular / recurring",
                "One-time deep clean",
                "Move-in / move-out clean",
                "Post-construction clean",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "What size is the property?",
            "question_text_ar": "ما حجم العقار؟",
            "question_type": "single_select",
            "options": ["Studio / 1 bedroom", "2–3 bedrooms", "4+ bedrooms / Villa"],
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "When do you need it?",
            "question_text_ar": "متى تحتاج إلى هذه الخدمة؟",
            "question_type": "single_select",
            "options": ["Today / tomorrow", "This week", "Flexible"],
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "pest-control": [
        {
            "question_text": "What pest issue are you having?",
            "question_text_ar": "ما نوع الحشرات التي تواجهها؟",
            "question_type": "single_select",
            "options": [
                "Cockroaches",
                "Ants",
                "Bed bugs",
                "Rodents",
                "Termites",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Where is this?",
            "question_text_ar": _LOCATION_QUESTION_AR,
            "question_type": "single_select",
            "options": _LOCATION_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "appliance-repair": [
        {
            "question_text": "Which appliance?",
            "question_text_ar": "ما هو الجهاز؟",
            "question_type": "single_select",
            "options": [
                "Washing machine",
                "Refrigerator",
                "Dishwasher",
                "Oven / Stove",
                "Water heater",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "What's the issue?",
            "question_text_ar": _WHATS_THE_ISSUE_AR,
            "question_type": "text",
            "options": None,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "moving-packing": [
        {
            "question_text": "What size is the move?",
            "question_text_ar": "ما حجم عملية النقل؟",
            "question_type": "single_select",
            "options": [
                "Studio / 1 bedroom",
                "2–3 bedrooms",
                "4+ bedrooms / Villa",
                "Office",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "Do you need packing service too?",
            "question_text_ar": "هل تحتاج إلى خدمة التغليف أيضاً؟",
            "question_type": "boolean",
            "options": None,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Is this within the same city or a different Emirate?",
            "question_text_ar": "هل النقل داخل نفس المدينة أم إلى إمارة أخرى؟",
            "question_type": "single_select",
            "options": ["Same city", "Different Emirate"],
            "is_required": True,
            "sort_order": 2,
        },
        {
            "question_text": "When do you need to move?",
            "question_text_ar": "متى تحتاج إلى الانتقال؟",
            "question_type": "text",
            "options": None,
            "is_required": False,
            "sort_order": 3,
        },
    ],
    "tutoring-private-lessons": [
        {
            "question_text": "What subject or skill?",
            "question_text_ar": "ما هي المادة أو المهارة؟",
            "question_type": "text",
            "options": None,
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "What level is the student?",
            "question_text_ar": "ما هو المستوى الدراسي للطالب؟",
            "question_type": "single_select",
            "options": ["Primary school", "Secondary school", "University", "Adult"],
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Where would you prefer lessons?",
            "question_text_ar": "أين تفضل أن تكون الدروس؟",
            "question_type": "single_select",
            "options": [
                "At my home",
                "Online",
                "Tutor's location",
                "No preference",
            ],
            "is_required": True,
            "sort_order": 2,
        },
        {
            "question_text": "How often?",
            "question_text_ar": "ما مدى تكرار الدروس؟",
            "question_type": "single_select",
            "options": [
                "One-time / exam prep",
                "Weekly ongoing",
                "Not sure yet",
            ],
            "is_required": True,
            "sort_order": 3,
        },
    ],
    "salon-barbershop": [
        {
            "question_text": "What service do you need?",
            "question_text_ar": "ما الخدمة التي تحتاجها؟",
            "question_type": "multi_select",
            "options": [
                "Haircut",
                "Hair coloring",
                "Styling",
                "Manicure / Pedicure",
                "Facial",
                "Shaving / Grooming",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "For whom?",
            "question_text_ar": "لمن هذه الخدمة؟",
            "question_type": "single_select",
            "options": ["Men", "Women", "Kids"],
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "Preferred timing?",
            "question_text_ar": "ما هو الوقت المفضل؟",
            "question_type": "text",
            "options": None,
            "is_required": False,
            "sort_order": 2,
        },
    ],
    "car-service-garage": [
        {
            "question_text": "What does your car need?",
            "question_text_ar": "ما الذي تحتاجه سيارتك؟",
            "question_type": "single_select",
            "options": [
                "Routine service / oil change",
                "Mechanical repair",
                "Body work / paint",
                "Tyres",
                "Battery",
                "AC service",
                "Other",
            ],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "Car make and model?",
            "question_text_ar": "ما هي ماركة وموديل السيارة؟",
            "question_type": "text",
            "options": None,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "How urgent is this?",
            "question_text_ar": _URGENCY_QUESTION_AR,
            "question_type": "single_select",
            "options": _URGENCY_OPTIONS,
            "is_required": True,
            "sort_order": 2,
        },
    ],
    "tailoring-alterations": [
        {
            "question_text": "What do you need?",
            "question_text_ar": _WHAT_DO_YOU_NEED_AR,
            "question_type": "single_select",
            "options": ["Alterations (resize / fix)", "Custom tailoring", "Other"],
            "is_required": True,
            "sort_order": 0,
        },
        {
            "question_text": "What kind of garment?",
            "question_text_ar": "ما نوع الملابس؟",
            "question_type": "text",
            "options": None,
            "is_required": True,
            "sort_order": 1,
        },
        {
            "question_text": "What's your timeline?",
            "question_text_ar": _TIMELINE_QUESTION_AR,
            "question_type": "single_select",
            "options": ["As soon as possible", "Within a week", "Flexible"],
            "is_required": True,
            "sort_order": 2,
        },
    ],
}
