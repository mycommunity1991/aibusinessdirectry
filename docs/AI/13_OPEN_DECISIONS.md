# AI Marketplace — Open Decisions

**Document ID:** AI-13
**Version:** 0.8.0
**Status:** Draft — Reconstructed; item 1 resolved and implemented (`CTG-001` shipped), item 4 resolved, item 3
given an explicit CTO risk-acceptance decision (still Open — the underlying legal question is unresolved), item
13 newly added and given an explicit CTO risk-acceptance decision (still Open — real LLM vendor selection remains
unresolved), item 14 newly added (`MAT-001`, still Open — a `REV-001` design question), items 5/8/10/11/12 still
pending CTO review, items 2/6/7 still unrecoverable numbering gaps
**Owner:** CTO
**Audience:** Engineering Team, Product Team, AI Assistants
**Last Updated:** 11 September 2026

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

**Status:** Resolved and implemented (09 September 2026) — v1 launch taxonomy locked *and* built: `CTG-001` has
shipped the real `category.categories`/`category.category_question_templates`/`category.provider_categories`
schema, seeded with the full 14-category, 47-question taxonomy (`docs/AI/17_CATEGORY_TAXONOMY.md` v1.1.0). This
item is now closed at both the content-decision level and the code level — see `Blocks` below for what is
genuinely unblocked as a result.

**Description:** The full category taxonomy (which service categories exist, their bilingual names, and the
category-specific follow-up questions the AI intake asks per category) has not been designed or locked. This
blocks the entire AI question-flow design (`03_DOMAIN_MODEL.md`: "it blocks AI question-flow design and must be
locked before that work starts").

**Resolution:** the CTO and engineering walked through and approved a 14-category v1 launch taxonomy, deliberately
scoped to trade/repair/personal-service needs where an AI follow-up-question flow clearly fits ("my AC broke, ask
me what's wrong" — not "I want a coffee"). Food & beverage, healthcare/clinics, and pet care are deliberately
excluded from v1, not ruled out permanently. Categories are flat (no subcategories) for v1. The full category
list, bilingual (EN/AR) names, slugs, and each category's follow-up question set are recorded in the new
`docs/AI/17_CATEGORY_TAXONOMY.md` — the authoritative source, not reproduced here. Arabic names/questions are a
first-pass translation, explicitly flagged in that document as needing native-speaker review before treated as
launch-final; that review does not block starting implementation, since `categories.name_ar` is nullable until
populated per `04_DATABASE.md`'s own column spec.

**Previous workaround (now superseded by this resolution, but still true of the shipped code until the real
domain is built):** `04_DATABASE.md` keeps `categories` self-referential and freely insertable, and
`category_question_templates.options` as JSONB, so the eventual taxonomy is a data change, not a migration
(Section 14). Two shipped stories each built their own interim stand-in because the real `category.categories`
table doesn't exist yet: PRO-001's `providers.category_label` (a single free-text column, since dropped) and
PRO-002's `provider.provider_category_labels` (a small, deliberately-not-`provider_categories`-named table
supporting multiple labels + one marked primary), and DIR-001 extended the same interim posture to query-time
matching (ADR-027). Both remain in place until the real domain is built and a separate reconciliation decision
migrates their data — reconciling free-text labels into real category references is explicitly out of scope for
this decision and its implementing story.

**Blocks (now unblocked at the code level):** AI Conversation/Intake design (Sprint 7: `AI-001`, `AI-002`) and —
transitively, per the Tracker's own dependency chain — every story in Sprints 7 through 12 (`MAT-001`, `CON-001`,
`REV-001`/`002`, `LEAD-001`/`002`, `ADM-001`/`002`, `ENG-001`/`002`) can now genuinely be planned and built against
a real, queryable taxonomy — `CTG-001` (Sprint 7) has shipped the real `category` schema domain and its seed
data, so this is no longer a blocker at the code level for any of them. **Not resolved by `CTG-001`, and still
tracked separately:** reconciling `provider.provider_category_labels`'s free-text values into the real
`category.provider_categories` join table remains a deliberately deferred, not-yet-scheduled follow-up story —
`provider_categories` was created empty by `CTG-001`'s migration and stays empty until that story ships; DIR-001's
free-text category filter (ADR-027) is likewise unaffected by `CTG-001` and continues to work against
`provider_category_labels` until that reconciliation happens. Native-speaker verification of the seeded Arabic
text (category names and all 47 question texts) also remains open, non-blocking, tracked at the
`17_CATEGORY_TAXONOMY.md` source-document level.

**Related:** `03_DOMAIN_MODEL.md` (Category domain), `04_DATABASE.md` (Category Domain section, Section 14),
`docs/AI/17_CATEGORY_TAXONOMY.md` (the resolution's full content), `Plan_S04_PRO-001.md` Decision 4,
`Plan_S04_PRO-002.md` Decision 1, `Walkthrough_S04_PRO-002.md`, `Plan_S06_DIR-001.md` Decision 1 (ADR-027).

---

## Item 2 — Unknown

**Status:** Unknown — numbering gap, no content recoverable

No document in the current repository cites item 2 by number or describes its content. Flagged for the CTO to
either fill in (if this was a real, separate decision from an earlier planning phase) or confirm as an unused
number.

---

## Item 3 — Google Places Data Legal Review

**Status:** Open — CTO has made an explicit, informed risk-acceptance decision (09 September 2026) to proceed
with `CLM-001` for MVP anyway; the underlying legal question itself remains genuinely unresolved. **`CLM-001`
has since shipped (09 September 2026) against this decision** — see "Implementation status" below.

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
by someone at the company. **Neither has happened as of this decision** — see below.

**First interim decision (08 September 2026, superseded by the risk-acceptance decision below):** rather than
build `CLM-001` against an unreviewed legal assumption, the CTO initially chose to defer `CLM-001` entirely
until this item resolved. Sprint 6 proceeded with `DIR-001` only in the meantime.

**Risk-acceptance decision (09 September 2026):** after walking through several alternative designs with
engineering — (a) live-query-only with no persistent Google content, (b) a rolling cache refreshed before a
~30-day cutoff, (c) fetch-then-verify-by-owner-then-store, (d) human-sourced leads (no API use at all) funneled
into ordinary self-registration — the CTO decided **not** to adopt any of those lower-risk designs for MVP.
Instead, `CLM-001` proceeds in its **original scope**: bulk-import Business listings from the Google Places API
as permanent `providers` rows (`listing_source = 'google_seeded_unclaimed'`, `is_claimed = false`) **without**
per-listing owner verification at seed time. The owner-verification mechanism (fetch → verify by owner via
OTP-to-public-number or another mechanism → only then treat as fully trusted) is explicitly planned as a
**later-stage improvement**, retrofitted onto whatever is pre-seeded now — not scheduled or scoped as of this
decision.

**This is a deliberate risk-acceptance, not a resolution of the legal question.** Recorded plainly, so the
record is honest about what was and wasn't decided:
- The underlying question — whether this pattern is permitted under Google's current Maps Platform Terms of
  Service and UAE PDPL — **remains genuinely open**. No legal counsel review and no first-party reading of
  Google's current terms has happened. This decision does not make the activity compliant; it means the CTO has
  chosen to proceed under uncertainty for MVP speed.
- Known, accepted exposure: possible breach of Google Maps Platform Terms of Service (API key/project
  suspension is the most likely enforcement mechanism, which would also affect any other Google Maps Platform
  use in the app, not just this feature); possible UAE PDPL exposure from holding unverified personal data
  (business owner names, phone numbers) sourced from a third party rather than collected directly with consent;
  reputational/diligence risk if this surfaces during fundraising, an app-store review, or a partnership
  evaluation.
- Existing mitigation, unchanged: `providers.listing_source`/`google_place_id` (unique when set) are already
  modeled specifically as the exact filter needed to bulk-delete every imported row if legal review later forces
  it (`04_DATABASE.md` Section 14).
- Explicit commitment, not yet scheduled: the fetch-verify-then-trust mechanism discussed this session is the
  intended long-term direction, to be implemented as a follow-up story once prioritized — existing pre-seeded,
  unverified rows would be expected to migrate toward that verified state over time, not remain permanently
  unverified.
- This item **stays Open**, not Resolved — proceeding under accepted risk is not the same as the legal question
  being answered, and a future legal review could still require changes (including deleting already-seeded
  data) to whatever `CLM-001` ships under this decision.

**Implementation status (09 September 2026, `CLM-001` shipped and signed off):** the design this decision
describes is no longer a plan — it is live in the codebase. The bulk-import mechanism
(`backend/scripts/import_google_places.py`, idempotent, keyed on `google_place_id`), the OTP-to-public-number
claim flow (`ClaimService`, `POST /claims/{provider_id}/verify-otp`), and the admin-review fallback for a failed
claim attempt (`administration.claim_review_requests`, `AdminClaimService`) are all built and tested — see
`docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md` for the full account. This is a status update, not
a resolution of the legal question above, which remains exactly as open as it was when this decision was made.
One consequence worth stating plainly: the `listing_source`/`google_place_id` bulk-deletion mitigation this item
already named is no longer a theoretical schema affordance — real, imported provider rows now exist (or will,
once the import script is run against a live Google Places API key/target in a real environment) that this
mitigation would actually need to act on if a future legal review forces deletion, not just a hypothetical case
to reason about in the abstract.

**Blocks:** Nothing now — `CLM-001` is unblocked for planning and implementation under this risk-acceptance
decision, and has since shipped. The underlying legal question remains open and should still get an actual
legal/first-party ToS review when practical; this is no longer treated as blocking, but it has not gone away, and
now applies to real data rather than a future hypothetical.

**Related:** `04_DATABASE.md` (`providers` table, Section 14; Administration Domain — `claim_review_requests`),
`09_DECISIONS.md` (ADR-029, ADR-030, ADR-031 — `CLM-001`'s shipped design), `14_USER_FLOWS.md` Flow 3
(Claim-Your-Listing), `docs/AI/Project_Tracker.xlsx` (`CLM-001` row, Sprint 6),
`docs/AI/PROJECT_IMPLEMENTATION_STATE.md` Section 17,
`docs/implementation/plans/Plan_S06_CLM-001.md`, `docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md`.

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

**Status:** Open (mechanism now implemented; the product question itself remains open)

**Description:** How much of Search Request → Provider matching runs as genuine automated matching versus
manual, admin-assisted matching behind the scenes at launch has not been decided. `03_DOMAIN_MODEL.md`'s
Administration domain names this directly as an open decision but — unlike items 1–9 — never cited it by a
specific number; it is assigned the next available number here for trackability. **This numbering is new as of
this reconstruction and should be confirmed, not assumed correct**, in case the original document (if one ever
existed) used a different number for it.

**Description (continued):** This directly affects the Administration domain's dashboard scope — how much of a
"manual match assignment" queue/UI needs to be built for low-confidence AI Conversation Sessions versus how much
matching can be fully automated.

**Update (10 September 2026, Story `AI-002` shipped):** the Wizard-of-Oz mechanism this item names now has a
real, working, first concrete implementation — a session below `Settings.CONVERSATION_CONFIDENCE_THRESHOLD`
(the same config-driven threshold `AI-001`'s ADR-034/Decision 4 introduced) is routed to
`administration.manual_match_assignments` (a pull-based admin queue, `GET /admin/search/manual-matches`, ADR-039)
rather than blocked or silently degraded; resolving it produces the identical customer-facing ranked-results
response an automated match would (ADR-040). **This update resolves nothing about the underlying product
question** — it only confirms the mechanism is real and code-level-complete. Exactly how much of launch-time
matching should stay manual long-term (i.e., what fraction of real sessions should be expected to fall below the
threshold and route to the manual queue, and whether that's an acceptable steady state or a temporary bootstrap
measure) is a product decision the CTO has not made and this story does not make on the CTO's behalf — the
threshold remains a `Settings` value specifically so that decision can be tuned without a code change once made.
This also newly informs the Administration domain's dashboard scope (`ADM-001`/`ADM-002`, Sprint 11): the queue
this item's UI question was about now has a real backend to build against.

**Blocks:** The Administration domain's dashboard scope (Sprint 11: ADM-001, ADM-002) — now with a real,
shipped backend queue to design a UI against, rather than a hypothetical one.

**Related:** `03_DOMAIN_MODEL.md` (Conversation/AI Intake Session, Administration domains); `09_DECISIONS.md`
ADR-034 (the confidence-threshold `Settings` value), ADR-039 (the pull-based queue implementation), ADR-040 (the
shared finalization guaranteeing identical customer experience); `docs/implementation/plans/Plan_S07_AI-002.md`;
`docs/implementation/walkthroughs/Walkthrough_S07_AI-002.md`.

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

## Item 12 — Mobile `features/search` and `features/home` Directly Import `features/customer`

**Status:** Open

**Description:** `02_ARCHITECTURE.md`'s Mobile Architecture section states, unqualified, "Features must not
depend directly on each other. Shared functionality belongs in shared modules." `DIR-001`'s `architect` review
found `mobile/lib/features/search/state/search_filters_controller.dart` imports
`features/customer/data/saved_address_repository.dart` and related `customer` domain models directly, to
pre-fill the search origin from the customer's default saved address. This is not a new pattern:
`mobile/lib/features/home/presentation/screens/home_placeholder_screen.dart` (pre-existing, shipped with
CUS-002, unchanged in its import shape by `DIR-001`) already imports the same `SavedAddressRepository` directly,
for its own address-required gate. Both are read-only, one-directional edges with no cycle — functionally
similar in kind (though not severity) to the bidirectional `provider`↔`verification` coupling VER-001's review
caught and fixed by extracting the shared type (`ProviderType`) into `mobile/lib/shared/models/`.

**Why not fixed immediately:** the architect's read is that this is a real violation of an unqualified
architecture rule, but fixing only the newer `search` edge while leaving the older `home` edge in place would
not actually resolve the drift — it would just produce two different remediations of the same gap at two
different times. Designing the right shared abstraction (most likely a trimmed, read-only "default address"
accessor moved into `mobile/lib/shared/`, mirroring the `ProviderType` extraction precedent) is a small but
real design decision that should be made once, deliberately, for both call sites together — not squeezed into
either story's review cycle. This is accepted, logged debt, not a decision to leave the rule unenforced
indefinitely.

**Current workaround:** none — both features import `customer` directly today. No new call site should be added
without first checking whether this item has been resolved.

**Blocks:** Nothing functionally; `02_ARCHITECTURE.md`'s "features must not depend on each other" rule is not
enforced for these two call sites until a small remediation story extracts the shared read into `shared/`.

**Related:** `02_ARCHITECTURE.md` (Mobile Architecture, "Features must not depend directly on each other"),
`Plan_S06_DIR-001.md`, `Checkpoint_S06_DIR-001.md`, `09_DECISIONS.md` (the `ProviderType` extraction precedent
from VER-001's review).

---

## Item 13 — Real LLM Vendor Selection and RAG Grounding Implementation

**Status:** Open — CTO has made an explicit, informed risk-acceptance decision (10 September 2026) to ship
`AI-001` against a fully rule-based interim client for MVP anyway; the underlying product question (which real
LLM vendor, and how RAG grounding against live provider data actually works) remains genuinely unresolved.
**`AI-001` has since shipped (10 September 2026) against this decision** — see "Implementation status" below.

**Description:** `AI-001` ("describe my service need in a guided AI conversation") is this platform's stated core
differentiator: an LLM-API-driven, RAG-grounded conversational intake. No real LLM provider, SDK, or credential is
confirmed anywhere in this codebase or environment — a repository-wide search found none (mirroring how VER-001's
planning found no real OCR pipeline either, item 11). Two of `AI-001`'s 11 verbatim acceptance criteria depend
directly on a real vendor existing:
- **AC3** ("system prompts are stored as version-controlled files, not inline strings") — meaningless for a
  client with no prompts.
- **AC5** ("a retrieved provider record with a null field is reported to the customer as unknown, never estimated
  or guessed") — requires live retrieval/grounding against real `provider.providers` records mid-conversation,
  which no code path in this story implements (`AI-001`'s scope boundary, item 1's now-resolved Category domain
  aside, deliberately never queries providers at all).

**This is a genuine product-differentiator gap, not a stub-infrastructure gap.** It is a different shape of
problem from items this document already tracks for `FileStorage`/`DocumentOcrService`/`GooglePlacesClient`
(all fully real mechanisms behind an interim/local vendor choice): here, the entire conversational intelligence
is scripted and deterministic (`RuleBasedConversationAiClient` — case-insensitive substring category matching,
verbatim template question walking, equal-step confidence) rather than prompt-driven reasoning grounded against
live data. The rule-based client is fully honest about what it is (never invents a question or fact outside the
seeded `category_question_templates`/`categories` taxonomy — a real, tested, structural guarantee, `AI-001`'s
AC10), but it is not yet the differentiated, natural-language-understanding product experience the platform's own
product description promises.

**Risk-acceptance decision (10 September 2026):** the CTO reviewed the tradeoff of blocking `AI-001` entirely on
this decision versus shipping the fully-buildable, fully-testable remainder of the story (the `conversation`
schema, the swappable Protocol boundary, the confidence/turn-cap mechanics, the revise-a-previous-answer flow, the
mobile chat screen, and 9 of 11 ACs) against a deterministic interim client. Chose to proceed with the interim
client for MVP, with AC3/AC5 honestly recorded as **not met**, not silently skipped or falsely marked satisfied —
mirroring exactly the risk-acceptance pattern item 3 already used for `CLM-001`'s Google Places decision. The
Protocol boundary (`ConversationAiClient`, ADR-034) means a future real vendor is one new class plus one
dependency-wiring change, zero changes to `ConversationService` itself.

**Known, accepted exposure:** the product's stated core differentiator does not yet exist in a customer-observable
sense — the guided conversation today is a scripted taxonomy walk, not an LLM-mediated natural-language
understanding experience. A customer describing their problem in genuinely ambiguous or colloquial free text will
be routed to a plain category picker far more often than a real NLU/LLM system would resolve automatically. Cost
and rate-control policy for real LLM calls (Open Question 2 in `Plan_S07_AI-001.md`) is entirely undecided, since
no real vendor call exists yet to have a policy for.

**This item stays Open, not Resolved** — proceeding under accepted risk for MVP speed is not the same as the
underlying product/vendor question being answered, and choosing a vendor later may require revisiting parts of the
`ConversationAiClient` Protocol shape itself (e.g. streaming responses, function-calling/tool-use for retrieval)
that the interim client's simple request/response shape does not need to anticipate.

**Implementation status (10 September 2026, `AI-001` shipped and signed off):** the design this decision describes
is live in the codebase — the full `conversation` schema and module, the `ConversationAiClient` Protocol and its
only implementation (`RuleBasedConversationAiClient`), and the mobile AI Conversation screen (S-07) are all built
and tested. See `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md` for the full account, including two
review-caught bug fixes (a mobile error-mapping bug, and a hard-delete-vs-soft-delete standards violation on the
revise-answer flow) unrelated to this item's own gap.

**Blocks:** Nothing at the code level for `AI-001` itself, which has shipped. **Blocks** AC3/AC5 ever being
genuinely satisfied, and blocks `AI-002`'s eventual confidence-routing design from being informed by a real
vendor's actual confidence-scoring behavior (today it is calibrated only against the interim client's own
0.0-or-1.0 scores). Also blocks Open Question 2 (cost/rate controls) from having anything concrete to design
against.

**Related:** `03_DOMAIN_MODEL.md` (Conversation / AI Intake Session — the RAG-grounded differentiator framing),
`04_DATABASE.md` (Conversation / AI Intake Domain), `09_DECISIONS.md` (ADR-034 — the `ConversationAiClient`
Protocol; ADR-035 — this gap's own ADR; the item-3 Google Places risk-acceptance pattern this mirrors),
`12_TECH_STACK.md` (no LLM vendor named), `docs/implementation/plans/Plan_S07_AI-001.md` (Decision 2, Decision 2b,
Open Questions 1/2), `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md`.

---

## Item 14 — `provider_rating_summaries` Remains Unbuilt: Is It Still Needed Once Real Reviews Exist?

**Status:** Open

**Description:** `04_DATABASE.md`'s Review Domain section fully specs `review.provider_rating_summaries` (a
denormalized per-provider rating aggregate, recalculated on every Review write). `MAT-001` ("see ranked
providers for my request", Sprint 8) needed a real rating signal to rank by now, but this table cannot yet hold
any real data — the Review domain is structurally impossible to build meaningfully before `CON-001` ships (a
Review anchors to a Contact View with a "Yes" Outcome Tag; Contact View is `CON-001`, which itself depends on
`MAT-001`). `MAT-001` therefore ranks against the already-existing, already-wired `providers.average_rating`/
`review_count` columns instead (`09_DECISIONS.md` ADR-043) — a deliberate, flagged substitution of AC3's
literally-named data source, not a silent reinterpretation.

**The genuinely open question, for a future `REV-001` to decide:** once the Review domain actually ships and
real reviews can exist, is `review.provider_rating_summaries` still needed as a distinct table — e.g. for a
richer, decoupled read-model separate from `providers` itself — or is `providers.average_rating`/`review_count`
alone (already `04_DATABASE.md`'s own documented `REV-001` write target, independent of whether
`provider_rating_summaries` is ever built) sufficient? `04_DATABASE.md` itself appears to carry two overlapping
denormalized-rating specs today, both described as "recalculated on/whenever a Review is written" — this looks
like undocumented drift from the schema's evolution (the `provider_rating_summaries` section's own text says it
"replaces" an earlier "ratings" placeholder), not a deliberate two-tier design. This is not `MAT-001`'s decision
to resolve; it is `REV-001`'s design question to make with real requirements in hand.

**Current workaround:** none needed yet — `provider_rating_summaries` remains an unbuilt table with zero
readers/writers anywhere in the codebase. `MAT-001`'s ranking formula and every provider-facing rating display
(DIR-001, AI-002, MAT-001) already read `providers.average_rating`/`review_count` exclusively.

**Blocks:** Nothing at the code level today. Will directly shape `REV-001`'s own schema design once that story
is planned — whichever answer is chosen, no other domain's code needs to change, since every current reader
already targets `providers.average_rating`/`review_count`, not `provider_rating_summaries`.

**Related:** `03_DOMAIN_MODEL.md` (Review domain — Contact-View/Outcome-Tag anchor requirement), `04_DATABASE.md`
(`providers.average_rating`/`review_count`, lines 405–406; `provider_rating_summaries`, Review Domain section),
`09_DECISIONS.md` (ADR-041 — AI-002's original deferred-ranking gap; ADR-042/ADR-043 — MAT-001's ranking formula
and rating-source substitution), `docs/implementation/plans/Plan_S08_MAT-001.md` (Decision 2),
`docs/implementation/walkthroughs/Walkthrough_S08_MAT-001.md`.

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
- **09 September 2026** — Item 12 added: `DIR-001`'s architect review found `features/search` and (pre-existing)
  `features/home` both import `features/customer`'s `SavedAddressRepository` directly, violating
  `02_ARCHITECTURE.md`'s "features must not depend directly on each other" rule. Logged as accepted debt with a
  recommended remediation shape, not fixed inside `DIR-001` — see item 12 for the architect's full reasoning.
- **09 September 2026 (same day)** — Item 1 (Category Taxonomy) resolved: the CTO and engineering walked through
  and approved a 14-category v1 launch taxonomy (bilingual EN/AR names, flat structure, per-category AI
  follow-up questions), recorded in full in the new `docs/AI/17_CATEGORY_TAXONOMY.md`. The content decision is
  locked; the real `category` schema domain still needs to be built, tracked as new Sprint 7 story `CTG-001`
  (added to the Tracker), which `AI-001`'s `Depends On` now includes alongside `DIR-001`.
- **09 September 2026 (Sprint 7)** — Item 1 fully implemented: `CTG-001` shipped the real
  `category.categories`/`category.category_question_templates`/`category.provider_categories` schema and seeded
  it with the full taxonomy, via this codebase's first data-seeding migration (recorded as ADR-028). During
  implementation, `17_CATEGORY_TAXONOMY.md` v1.0.0 was found to be missing the Arabic question text its own prose
  claimed existed; the CTO corrected the document (now v1.1.0, real first-pass Arabic text for all 47 questions)
  and the seed data was updated accordingly. Item 1's Status updated to "Resolved and implemented" — `AI-001`/
  `AI-002` and everything cascading from them through Sprint 12 are now genuinely unblocked at the code level.
  Reconciling `provider_category_labels` into `provider_categories` remains separately deferred, not resolved by
  this story.
- **09 September 2026 (same day)** — Item 3 (Google Places Data Legal Review) updated: after reviewing several
  lower-risk alternative designs (live-query-only, rolling short-term cache, fetch-verify-then-store, human-
  sourced leads with no API use), the CTO made an explicit, informed decision to proceed with `CLM-001` in its
  original bulk-import scope for MVP — unverified Google-seeded listings, owner verification deferred to a later
  story — accepting the known Google ToS/UAE PDPL exposure this carries rather than resolving it first. This is a
  **risk-acceptance, not a resolution**: the item stays Open, `CLM-001` is no longer blocked, and the underlying
  legal question is unchanged. See item 3 above for the full record of what was and wasn't decided.
- **09 September 2026 (Sprint 6, `CLM-001` shipped)** — Item 3 updated again: `CLM-001` has shipped and been
  signed off, executing the risk-acceptance decision above — the bulk-import script, OTP claim flow, and
  admin-review fallback are now live in the codebase (recorded as ADR-029/ADR-030/ADR-031). Item stays **Open**;
  this update is about implementation status, not a change to the legal question, which remains unresolved. The
  `listing_source`/`google_place_id` bulk-deletion mitigation is now operative against real, imported data rather
  than a theoretical schema affordance. See item 3's "Implementation status" note and
  `docs/implementation/walkthroughs/Walkthrough_S06_CLM-001.md` for the full account.
- **10 September 2026 (Sprint 7, `AI-001` shipped)** — Item 13 added: `AI-001` ("describe my service need in a
  guided AI conversation") shipped against an explicit CTO risk-acceptance decision to ship a fully rule-based
  interim `ConversationAiClient` for MVP, with AC3 (system-prompt version control) and AC5 (null-provider-field
  grounding) honestly recorded as not met rather than silently skipped — mirroring item 3's risk-acceptance
  pattern. Real LLM vendor selection and RAG grounding implementation remain genuinely open, tracked here as a
  deliberate, CTO-approved MVP gap that must stay visibly open. Recorded as ADR-035 in `09_DECISIONS.md`. See
  `docs/implementation/walkthroughs/Walkthrough_S07_AI-001.md` for the full account.
- **11 September 2026 (Sprint 8, `MAT-001` shipped)** — Item 14 added: `MAT-001` ("see ranked providers for my
  request") shipped a real merit-ranking formula reading `providers.average_rating`/`review_count` rather than
  the unbuilt `review.provider_rating_summaries` table (`09_DECISIONS.md` ADR-042/ADR-043), since the Review
  domain is structurally impossible to build meaningfully before `CON-001` ships. Whether
  `provider_rating_summaries` is still needed as a distinct table once `REV-001` ships real reviews, or whether
  `providers.average_rating`/`review_count` alone is sufficient, remains a genuinely open design question for
  that future story. See `docs/implementation/walkthroughs/Walkthrough_S08_MAT-001.md` for the full account.

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
