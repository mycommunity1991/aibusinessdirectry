# AI Marketplace — Category Taxonomy (v1 Launch Set)

**Document ID:** AI-17
**Version:** 1.0.0
**Status:** Active — CTO-approved 09 September 2026, resolving `13_OPEN_DECISIONS.md` item 1
**Owner:** CTO
**Audience:** Engineering Team, AI Assistants, Content/Localization
**Last Updated:** 09 September 2026

---

# Purpose

This is the authoritative source for the v1 launch category taxonomy: the categories that populate `category.categories`, and the AI's per-category follow-up questions that populate `category.category_question_templates` (both tables specified in `04_DATABASE.md`'s Category Domain section). Resolving this was the single highest-leverage open decision in the project — `13_OPEN_DECISIONS.md` item 1 names it as blocking the entire AI Conversation/Intake design (Sprint 7 onward) and everything that cascades from it (Matching, Contact, Reviews, Leads, Admin Ops, Engagement).

**This is a v1 launch set, not a final or exhaustive catalog.** The schema (`parent_category_id` self-referential, `category_question_templates.options` as JSONB) was deliberately built so adding, editing, or retiring a category is a data change, not a migration (`04_DATABASE.md` Section 14). Categories are flat (no subcategories) for v1 — deliberately, to keep the AI's category-resolution step simple for launch; subcategories can be introduced later without a schema change.

**Scope reasoning:** this list deliberately excludes food & beverage (cafes, restaurants, bakeries), healthcare/clinics, and pet care, even though `00_PROJECT_CONTEXT.md` names cafes/bakeries as Business-type examples. The AI's core value is turning an unstructured *problem* into a structured, matchable request via follow-up questions — a shape that fits trade/repair/personal-service needs ("my AC broke," "I need a plumber") far better than browsing intent ("I want a coffee"). Food & beverage and other browse-first categories are deferred to a future decision, not ruled out permanently. Healthcare/clinics are deferred separately given the regulatory weight a medical-adjacent category would carry.

---

# The 14 Categories

Ordered by `sort_order` (0-indexed). `is_primary` still applies per-provider exactly as PRO-002 built it (`provider_categories.is_primary`) — a provider can hold more than one of these.

| # | slug | name (EN) | name_ar | Typical supply side |
|---|---|---|---|---|
| 0 | `plumbing` | Plumbing | السباكة | Freelancer |
| 1 | `electrical` | Electrical | الكهرباء | Freelancer |
| 2 | `ac-repair-maintenance` | AC Repair & Maintenance | تكييف الهواء - الصيانة والإصلاح | Freelancer |
| 3 | `carpentry` | Carpentry | النجارة | Freelancer |
| 4 | `painting` | Painting | الدهان | Freelancer |
| 5 | `handyman-general-repairs` | Handyman / General Repairs | أعمال الصيانة العامة | Freelancer |
| 6 | `home-cleaning` | Home Cleaning | تنظيف المنزل | Freelancer |
| 7 | `pest-control` | Pest Control | مكافحة الحشرات | Freelancer |
| 8 | `appliance-repair` | Appliance Repair | إصلاح الأجهزة المنزلية | Freelancer |
| 9 | `moving-packing` | Moving & Packing | النقل والتغليف | Freelancer |
| 10 | `tutoring-private-lessons` | Tutoring & Private Lessons | الدروس الخصوصية | Freelancer |
| 11 | `salon-barbershop` | Salon & Barbershop | صالون وحلاقة | Business |
| 12 | `car-service-garage` | Car Service & Garage | صيانة السيارات | Business |
| 13 | `tailoring-alterations` | Tailoring & Alterations | الخياطة والتعديلات | Business |

`icon_url` is deliberately left `NULL` for every row at seed time — icon assets are a design-asset task, not a data-modeling decision, and are tracked separately (mobile may fall back to a client-side icon lookup keyed by `slug` until real icon assets exist; this is a mobile implementation detail, not a taxonomy blocker).

**Arabic names are a first-pass translation, not yet native-speaker-verified.** They should be reviewed by a native Arabic speaker (ideally UAE/Gulf dialect-aware for common trade terms) before this taxonomy is treated as launch-final. This is flagged explicitly, the same way `04_DATABASE.md`'s `categories.name_ar` column itself is documented as "nullable only until translation is populated; required before launch."

---

# Category-Specific Follow-Up Questions

Each category lists its `category_question_templates` rows, in `sort_order`. `question_type` values match `04_DATABASE.md`'s spec exactly: `text` | `single_select` | `multi_select` | `number` | `boolean`. All questions are `is_required=true` unless noted otherwise. Arabic question text (`question_text_ar`) carries the same native-speaker-review caveat as the category names above — English is authoritative for v1 seeding; Arabic is a first-pass translation.

## Plumbing

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What's the issue? | single_select | Leak, Blockage, Installation, Other |
| 1 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 2 | Where is this? | single_select | Home, Office / Commercial |
| 3 | Anything else we should know? | text | — (`is_required=false`) |

## Electrical

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What do you need? | single_select | Power outage / fault, New installation, Wiring repair, Appliance connection, Other |
| 1 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 2 | Where is this? | single_select | Home, Office / Commercial |
| 3 | Anything else we should know? | text | — (`is_required=false`) |

## AC Repair & Maintenance

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What's wrong? | single_select | Not cooling, Not turning on, Leaking water, Routine maintenance / service, New installation, Other |
| 1 | What type of AC? | single_select | Split unit, Central AC, Window unit, Not sure |
| 2 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 3 | Where is this? | single_select | Home, Office / Commercial |

## Carpentry

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What do you need? | single_select | Furniture repair, Custom furniture, Door / window fixing, Installation (shelves, cabinets), Other |
| 1 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 2 | Anything else we should know? | text | — (`is_required=false`) |

## Painting

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What needs painting? | multi_select | Walls, Ceiling, Doors / windows, Furniture, Exterior |
| 1 | Approximately how much space? | single_select | Small touch-up, Single room, Whole apartment / villa, Not sure |
| 2 | What's your timeline? | single_select | As soon as possible, Within 2 weeks, Flexible |

## Handyman / General Repairs

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What needs fixing? | text | — |
| 1 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 2 | Where is this? | single_select | Home, Office / Commercial |

## Home Cleaning

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What type of cleaning? | single_select | Regular / recurring, One-time deep clean, Move-in / move-out clean, Post-construction clean |
| 1 | What size is the property? | single_select | Studio / 1 bedroom, 2–3 bedrooms, 4+ bedrooms / Villa |
| 2 | When do you need it? | single_select | Today / tomorrow, This week, Flexible |

## Pest Control

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What pest issue are you having? | single_select | Cockroaches, Ants, Bed bugs, Rodents, Termites, Other |
| 1 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |
| 2 | Where is this? | single_select | Home, Office / Commercial |

## Appliance Repair

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | Which appliance? | single_select | Washing machine, Refrigerator, Dishwasher, Oven / Stove, Water heater, Other |
| 1 | What's the issue? | text | — |
| 2 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |

## Moving & Packing

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What size is the move? | single_select | Studio / 1 bedroom, 2–3 bedrooms, 4+ bedrooms / Villa, Office |
| 1 | Do you need packing service too? | boolean | — |
| 2 | Is this within the same city or a different Emirate? | single_select | Same city, Different Emirate |
| 3 | When do you need to move? | text | — (`is_required=false`) |

## Tutoring & Private Lessons

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What subject or skill? | text | — |
| 1 | What level is the student? | single_select | Primary school, Secondary school, University, Adult |
| 2 | Where would you prefer lessons? | single_select | At my home, Online, Tutor's location, No preference |
| 3 | How often? | single_select | One-time / exam prep, Weekly ongoing, Not sure yet |

## Salon & Barbershop

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What service do you need? | multi_select | Haircut, Hair coloring, Styling, Manicure / Pedicure, Facial, Shaving / Grooming, Other |
| 1 | For whom? | single_select | Men, Women, Kids |
| 2 | Preferred timing? | text | — (`is_required=false`) |

## Car Service & Garage

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What does your car need? | single_select | Routine service / oil change, Mechanical repair, Body work / paint, Tyres, Battery, AC service, Other |
| 1 | Car make and model? | text | — |
| 2 | How urgent is this? | single_select | Emergency — need someone today, Within a few days, Just planning |

## Tailoring & Alterations

| # | question_text | question_type | options |
|---|---|---|---|
| 0 | What do you need? | single_select | Alterations (resize / fix), Custom tailoring, Other |
| 1 | What kind of garment? | text | — |
| 2 | What's your timeline? | single_select | As soon as possible, Within a week, Flexible |

---

# Migration Notes for Implementation

- `category.categories`: 14 rows, `parent_category_id = NULL` for all (flat, v1), `sort_order` per the table above, `icon_url = NULL`.
- `category.category_question_templates`: one row per question listed above, `category_id` FK to the matching category, `sort_order` per its position within the category, `options` as a JSONB array of strings for `single_select`/`multi_select` types, `NULL` for `text`/`boolean`/`number` types.
- This data should be seeded via a data migration (or a dedicated, idempotent seed step run as part of the same migration that creates these tables) — not left for manual `INSERT`s, so it ships identically across every environment.
- Once this domain exists for real, PRO-002's interim `provider.provider_category_labels` (free-text) and the real `category.provider_categories` join table both exist side by side for a transition period — reconciling a provider's free-text labels into real category references is explicitly **not** part of this taxonomy decision or its implementing story; see `13_OPEN_DECISIONS.md` item 1's "Current workaround" section for that follow-up's own scope.

---

# Related Documents

- `docs/AI/13_OPEN_DECISIONS.md` (item 1 — Category Taxonomy, resolved by this document)
- `docs/AI/04_DATABASE.md` (Category Domain schema section)
- `docs/AI/03_DOMAIN_MODEL.md` (Category domain)
- `docs/AI/00_PROJECT_CONTEXT.md` (Section 4 — Two-Sided Supply; the Business/Freelancer examples this taxonomy draws from)

---

**End of Document**
