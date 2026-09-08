# AI Marketplace — Open Decisions

**Document ID:** AI-13
**Version:** 0.2.0
**Status:** Draft — Reconstructed; items 4 resolved and 3 given an interim sequencing decision by the CTO on
08 September 2026, items 1/5/8/10/11 still pending CTO review, items 2/6/7 still unrecoverable numbering gaps
**Owner:** CTO
**Audience:** Engineering Team, Product Team, AI Assistants
**Last Updated:** 08 September 2026

---

# Purpose

This document tracks unresolved product and technical decisions that block or shape downstream work. Every
other `docs/AI/` document treats this file as the authoritative home for "still open" product questions —
`03_DOMAIN_MODEL.md`, `04_DATABASE.md`, `11_MVP_SCOPE.md`, `14_USER_FLOWS.md`, `15_SCREEN_INVENTORY.md`,
`16_UX_GUIDELINES.md`, and `PROJECT_IMPLEMENTATION_STATE.md` all cite specific numbered items from it.

**Reconstruction note:** this file did not exist anywhere in the repository until now, despite being cited by
name (and by specific item number) across at least ten other documents and three shipped implementation
stories (PRO-001, PRO-002, VER-001), each of which had to design an explicit, flagged workaround specifically
*because* the real decision here was never recorded. This version was reconstructed by searching every citation
of `13_OPEN_DECISIONS.md` across the codebase and compiling exactly what each citation said about the item it
referenced — nothing below is invented. Items 1, 3, 4, 5, 8, and 9 have direct textual evidence (cited by that
exact number, more than once, in multiple documents). Items 2, 6, and 7 are numbering gaps: other items'
numbering implies they exist, but no citation anywhere in the current documentation says what they cover — their
content could not be recovered and needs the CTO (or whoever holds the original decision log) to fill in, or to
confirm the gaps are simply unused numbers. Two additional items (10, 11) are newly added here, surfaced by
implementation work but never previously tracked in any numbered list — flagged as such below.

**No implementation story should be blocked on this document's completeness.** The existing pattern — a
Plan explicitly documents a flagged, temporary workaround and cites the relevant item number here — worked
correctly three times over and should continue. This file's job is to make resolving each item easier when the
product/business decision is finally ready to be made, and to stop the same workaround from being redesigned
from scratch by a fourth or fifth story.

---

# How to use this document

- Each item has a **Status**: `Open` (unresolved, an active workaround exists or is needed), `Resolved` (the
  decision has been made — record the answer and the date, don't delete the row), or `Unknown` (a numbering gap
  with no recoverable content).
- When a decision is made, update its Status to `Resolved`, fill in **Resolution**, and add a changelog entry at
  the bottom — do not delete the row or renumber other items, mirroring `09_DECISIONS.md`'s append-only
  convention.
- When a new implementation story surfaces a genuinely new open product/technical decision it had to work
  around, add a new item at the next available number rather than inventing a parallel tracking mechanism.

---

# Tracked Decisions

## Item 1 — Category Taxonomy

**Status:** Open — critical path

**Description:** The full category taxonomy (which service categories exist, their bilingual names, and the
category-specific follow-up questions the AI intake asks per category) has not been designed or locked. This
blocks the entire AI question-flow design (`03_DOMAIN_MODEL.md`: "it blocks AI question-flow design and must be
locked before that work starts").

**Current workaround:** `04_DATABASE.md` keeps `categories` self-referential and freely insertable, and
`category_question_templates.options` as JSONB, so the eventual taxonomy is a data change, not a migration
(Section 14). Two shipped stories have each built their own interim stand-in because the real `category.categories`
table doesn't exist yet: PRO-001's `providers.category_label` (a single free-text column, since dropped) and
PRO-002's `provider.provider_category_labels` (a small, deliberately-not-`provider_categories`-named table
supporting multiple labels + one marked primary). Both are documented as temporary, pending this decision.

**Blocks:** AI Conversation/Intake design (Sprint 7+), the real `provider_categories` join table, category-based
search/matching.

**Related:** `03_DOMAIN_MODEL.md` (Category domain), `04_DATABASE.md` (Category Domain section, Section 14),
`Plan_S04_PRO-001.md` Decision 4, `Plan_S04_PRO-002.md` Decision 1, `Walkthrough_S04_PRO-002.md`.

---

## Item 2 — Unknown

**Status:** Unknown — numbering gap, no content recoverable

No document in the current repository cites item 2 by number or describes its content. Flagged for the CTO to
either fill in (if this was a real, separate decision from an earlier planning phase) or confirm as an unused
number.

---

## Item 3 — Google Places Data Legal Review

**Status:** Open — interim sequencing decision made (08 September 2026), underlying legal question still
unresolved

**Description:** The platform plans to seed initial Business listings from Google Places data
(`listing_source = 'google_seeded_unclaimed'`) before a real owner claims them. Whether this is legally
permissible to do at scale, and under what terms (attribution, deletion-on-request, data-retention limits), has
not been reviewed. This is a real, non-trivial concern, not a formality: Google's Places API / Google Maps
Platform Terms of Service have historically placed specific restrictions on caching and persistently storing
Place data to build an independent directory (as opposed to querying live and using data only for the display
Google's terms permit) — bulk-importing many businesses as permanent, pre-claim `providers` rows, exactly as
`CLM-001` originally scoped it, is close to the pattern those terms are written to restrict. This needs an
actual reading of Google's *current* Terms of Service (they are revised periodically) and, given personal data
(names, phone numbers) is involved, a check against UAE PDPL — neither of which this document or any engineering
agent can perform; it requires either legal counsel or a careful first-party reading of Google's current terms
by someone at the company.

**Interim decision (08 September 2026):** rather than build `CLM-001` against an unreviewed legal assumption,
the CTO chose to **defer `CLM-001` entirely** until this item is actually resolved. Sprint 6 proceeds with
`DIR-001` only, which does not depend on this item at all — confirmed directly from the Tracker: `DIR-001`
("Browse nearby providers by category and location") depends only on `CUS-002`/`PRO-002`/`VER-002` (all done)
and searches only self-registered providers with `is_discoverable=true`; it never touches Google Places data or
the `google_seeded_unclaimed`/`is_claimed` columns. `CLM-001` alone (depends on `DIR-001`, `VER-002`) is the one
blocked by this item, and stays out of Sprint 6's delivered scope until it resolves. This decision only concerns
*when* `CLM-001` is built, not the underlying legal question, which remains genuinely open.

**Current workaround (unchanged, still relevant once this resolves):** `04_DATABASE.md` already models
`providers.listing_source` and `google_place_id` (unique when set) as the exact filter needed if legal review
later forces deletion of imported data (Section 14): "if legal review forces deletion of imported data,
`listing_source = 'google_seeded_unclaimed'` rows are the exact filter needed."

**Blocks:** `CLM-001` only (not `DIR-001`, confirmed above) and any Google Places API integration work.

**Related:** `04_DATABASE.md` (`providers` table, Section 14), `14_USER_FLOWS.md` Flow 3 (Claim-Your-Listing),
`docs/AI/Project_Tracker.xlsx` (`DIR-001`/`CLM-001` rows, Sprint 6).

---

## Item 4 — Unclaimed Listing UX

**Status:** Resolved (08 September 2026) — design decided; build deferred alongside item 3/`CLM-001`

**Description:** How an unclaimed, Google-seeded listing should be visually presented to customers browsing the
directory — specifically how prominently/how it's labeled as "unclaimed" versus a claimed, verified listing —
had not been finalized.

**Resolution:** a full-width banner across the top of both the provider card (`S-08`) and the provider profile
(`S-09`), in the Warning color (`#F59E0B`, already reserved for this in `16_UX_GUIDELINES.md`'s color table),
reading "Unclaimed — Is this your business? Claim it" with an inline CTA opening the Claim flow (`S-21`,
Flow 3) — chosen over a smaller badge or a separate "not yet verified" section specifically to satisfy the
existing "visually distinct at a glance, not a small badge a user could miss" constraint directly and
unambiguously. Recorded in full in `16_UX_GUIDELINES.md`'s Trust & Verification UX Patterns section.

**Note:** this is a design decision only. Nothing gets built from it yet — no unclaimed listing exists in the
product until `CLM-001` ships, and `CLM-001` itself is deferred pending item 3. When `CLM-001` is eventually
planned, this resolution is ready to implement directly, no re-derivation needed.

**Blocks:** Nothing further — the design question itself is settled. `CLM-001`'s own build timeline is gated by
item 3, not by this item.

**Related:** `04_DATABASE.md` (`providers` table, Section 14), `14_USER_FLOWS.md` Flow 3, `16_UX_GUIDELINES.md`
(Trust & Verification UX Patterns — the resolution's full text lives there).

---

## Item 5 — Business Verification Bar

**Status:** Open

**Description:** Freelancer verification is a hard, mandatory safety gate (Emirates ID, always required, never
configurable — freelancers enter customers' homes). What a Business Provider must submit to verify — and
whether a document is required at all — has not been decided.

**Current workaround:** `04_DATABASE.md`'s `verification_type` enum already includes both `business_license` and
`business_lightweight`, framing which one is required as "an application-config decision, not a schema decision"
(Section 14). VER-001 (Sprint 5) has since shipped exactly that: two settings,
`BUSINESS_VERIFICATION_TYPE` (default `business_lightweight`) and `BUSINESS_VERIFICATION_DOCUMENT_REQUIRED`
(default `False`), so the eventual product answer is a config flip, not a schema or endpoint change.

**Blocks:** Nothing further right now — the config-driven design absorbs whichever answer is chosen. Resolving
this item only changes the two setting values above, once decided.

**Related:** `03_DOMAIN_MODEL.md` (Provider/Verification domains), `04_DATABASE.md` Section 14, `14_USER_FLOWS.md`
Flow 2 step 6, `Plan_S05_VER-001.md` Decision 3, `Walkthrough_S05_VER-001.md`.

---

## Item 6 — Unknown

**Status:** Unknown — numbering gap, no content recoverable

No document in the current repository cites item 6 by number or describes its content. Flagged for the CTO to
either fill in or confirm as an unused number.

---

## Item 7 — Unknown

**Status:** Unknown — numbering gap, no content recoverable

No document in the current repository cites item 7 by number or describes its content. Flagged for the CTO to
either fill in or confirm as an unused number.

---

## Item 8 — Final Product / Company Name

**Status:** Open

**Description:** "AI Marketplace" is a working title, not a cleared final product name. `docs/design/STITCH_UI_PROMPTS.md`
uses "Qivo" as a provisional candidate name, "chosen after a first-pass collision check... but not yet formally
cleared," pending a real UAE/GCC trademark and domain search.

**Current workaround:** `09_DECISIONS.md` records the working-title rename from "MyCommunity" to "AI Marketplace"
explicitly as provisional ("final name is still an open decision"). Code identifiers, package names, and
infrastructure naming follow the `ai_marketplace`/`ai-marketplace` convention until this resolves.

**Blocks:** Final app-store listing names, marketing/domain registration, and the design system's product-name
references in `docs/AI/DESIGN.md` and `docs/design/STITCH_UI_PROMPTS.md` (which would need a find-and-replace
across generated screens if the name changes). Also directly relevant to the company-registration question
raised earlier in this conversation — a cleared trade name is typically needed before finalizing a UAE trade
license.

**Related:** `09_DECISIONS.md` (the MyCommunity → AI Marketplace rename ADR), `10_GLOSSARY.md`, `docs/AI/DESIGN.md`,
`docs/design/STITCH_UI_PROMPTS.md`.

---

## Item 9 — Launch Market Confirmation

**Status:** Resolved — UAE confirmed

**Description:** Whether the UAE was a "likely default" or a firmly confirmed launch market was open as of the
v0.1.0 concept.

**Resolution:** `00_PROJECT_CONTEXT.md`'s own Changelog (Section 11) records this as resolved in the current,
locked v0.8.0 scope: "Launch market | UAE 'likely default,' open decision → UAE confirmed." The architecture
remains deliberately country-agnostic regardless (`country_code`, ISO 3166-1, appears wherever geography matters
instead of an implicit UAE default), so this resolution required no schema change.

**Note:** `04_DATABASE.md` Section 14 still lists this as an open item needing schema accommodation. That
accommodation (the country-agnostic `country_code` columns) was already built and needs no further work — the
schema-flexibility table there predates this resolution being recorded in `00_PROJECT_CONTEXT.md` and should be
read as historical, not as evidence the decision is still open.

**Related:** `00_PROJECT_CONTEXT.md` Section 11, `04_DATABASE.md` Section 14.

---

## Item 10 — Degree of Manual ("Wizard-of-Oz") Matching at Launch

**Status:** Open

**Description:** How much of Search Request → Provider matching runs as genuine automated matching versus
manual, admin-assisted matching behind the scenes at launch has not been decided. `03_DOMAIN_MODEL.md`'s
Administration domain names this directly as an open decision but — unlike items 1–9 — never cited it by a
specific number; it is assigned the next available number here for trackability. **This numbering is new as of
this reconstruction and should be confirmed, not assumed correct**, in case the original document (if one ever
existed) used a different number for it.

**Description (continued):** This directly affects the Administration domain's dashboard scope — how much of a
"manual match assignment" queue/UI needs to be built for low-confidence AI Conversation Sessions versus how much
matching can be fully automated.

**Blocks:** The Administration domain's dashboard scope (Sprint 11: ADM-001, ADM-002) and the AI-Guided Service
Intake sprint's confidence-threshold routing design (Sprint 7: AI-001, AI-002).

**Related:** `03_DOMAIN_MODEL.md` (Conversation/AI Intake Session, Administration domains).

---

## Item 11 — Real OCR Pipeline Interface Confirmation

**Status:** Open

**Description:** VER-001's story description referenced reusing "the existing Ejari/Emirates ID OCR pipeline,"
but a repository-wide search during VER-001's planning found no OCR pipeline, external OCR SDK, or Ejari
integration anywhere in this codebase or development environment — every hit was either narrative documentation
or a behavioral skill file, not actual code. `00_PROJECT_CONTEXT.md`'s changelog documents this codebase as a
pivot from an earlier "MyCommunity" product; the "existing pipeline" language is most plausibly a product-level
asset assumption carried over from that earlier planning, not something literally present here. **This item is
newly added as of this reconstruction** — it was not previously tracked under any number, but is exactly the
kind of "blocks real implementation, has an explicit interim workaround" item this document exists to track.

**Current workaround:** VER-001 shipped a swappable `DocumentOcrService` Protocol with a `StubDocumentOcrService`
that always returns empty candidate fields, honestly telling the provider "we couldn't read this automatically
yet — please fill it in yourself," rather than guessing at an unconfirmed vendor's interface (recorded as
ADR-018). A future story can add a real implementation as one new class plus one dependency-wiring change once
this item resolves.

**Blocks:** Any real, automated OCR extraction on verification documents. Does not block VER-001/VER-002's core
functionality (the stub is a fully honest, working substitute for now).

**Related:** `03_DOMAIN_MODEL.md` (Verification domain), `Plan_S05_VER-001.md` Decision 6, `09_DECISIONS.md`
ADR-018, `.agents/skills/identity-verification/SKILL.md`.

---

# Changelog

- **08 September 2026** — Document created (reconstructed from citations across the codebase; see
  Reconstruction Note above). Items 1, 3, 4, 5, 8 recorded as Open from direct citation evidence. Item 9
  recorded as Resolved (UAE confirmed) per `00_PROJECT_CONTEXT.md`'s own changelog. Items 2, 6, 7 recorded as
  unrecoverable numbering gaps. Items 10 and 11 newly added, surfaced by `03_DOMAIN_MODEL.md`'s Administration
  section and VER-001's OCR findings respectively.
- **08 September 2026 (same day, ahead of Sprint 6)** — Item 4 (Unclaimed Listing UX) resolved: full-width
  Warning-color banner, recorded in full in `16_UX_GUIDELINES.md`. Item 3 (Google Places Data Legal Review)
  given an interim sequencing decision, not a resolution of the underlying legal question: `CLM-001` is
  deferred until a real legal/PDPL review happens; `DIR-001` proceeds in Sprint 6 unaffected, confirmed
  independent of this item via the Tracker's own `Depends On` field.

---

# Related Documents

- `00_PROJECT_CONTEXT.md`
- `03_DOMAIN_MODEL.md`
- `04_DATABASE.md` (Section 14 — Schema Flexibility Against Open Decisions)
- `09_DECISIONS.md`
- `11_MVP_SCOPE.md`
- `14_USER_FLOWS.md`
- `15_SCREEN_INVENTORY.md`
- `16_UX_GUIDELINES.md`
- `PROJECT_IMPLEMENTATION_STATE.md`

---

**End of Document**
