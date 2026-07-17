# AI Marketplace — Project Context

**Document ID:** AI-00
**Version:** 0.8.0
**Status:** Draft — Aligned to MVP Scope v0.8.0
**Owner:** Founder / CTO
**Audience:** Engineering Team, AI Assistants
**Source:** Consolidated from *AI-Powered Directory & Booking Marketplace — Master Concept*, superseded by MVP scope iterations through v0.8.0
**Last Updated:** 14 July 2026

---

# Purpose

This document defines the product vision, scope boundaries, and guiding principles for the AI Marketplace platform. It is the entry point for all engineering, product, and AI-assisted implementation work.

All development must align with this document. Any conflict between this document and a sprint story must be raised before implementation continues.

**Change note (v0.1.0 → v0.8.0):** Several foundational assumptions from the original concept have been explicitly overturned during scoping. See Section 10 for a full changelog. The most important reversals: this is now a **native mobile app**, not web-only; registration is **mandatory**, not guest-optional; and contact is **direct and immediate** after a match, not staged behind a quote-acceptance step.

---

# 1. What This Product Is

A location-based directory and AI-mediated conversational-intake marketplace connecting two supply types with nearby customers, rather than category-tree search:

- **Formal businesses** — cafes, repair shops, salons, and similar fixed-location operations
- **Individual freelancers** — plumbers, electricians, tutors, car-washers, and similar mobile, one-to-one service providers

This is a deliberate pivot away from a social-feed model toward a task-oriented, transactional utility. The product is a **utility** (search → match → contact), not a **feed** (post → like → comment). Feeds are a moderation and engagement-chasing business; a directory product with a lightweight contact flow is a simpler, more directly monetizable loop.

**Core flow (current):** Customer describes their need in natural language → AI asks category-specific follow-ups → AI matches against real provider data → customer views a matched provider's profile → customer sees the provider's phone number directly and contacts them off-platform to arrange the job. There is no in-app booking, quoting, payment, or chat step between match and contact.

---

# 2. Vision

Any business or individual freelancer can list what they do for free and be found by nearby customers through AI-powered, natural-language search — because discovery is driven by **location and category**, not by a closed, verified community.

Two principles are carried forward as non-negotiable:

1. **Country-agnostic by design.** The product must not assume a single launch market's identity infrastructure, language, or regulatory environment as a permanent constraint. UAE is the confirmed launch market (see Section 5), but the architecture must not hard-code that assumption.
2. **Utility, not feed.** No post/comment/reaction loop. Every core interaction moves a customer toward contacting a provider.

---

# 3. Why AI Is the Core, Not a Feature

A category-tree directory (JustDial-style) is a commodity — Google Maps and existing directories already do that well. The differentiated value is in understanding an unstructured, plain-language problem and turning it into a structured, matchable request.

The AI has four distinct jobs:

1. Understand the customer's problem, described in natural language
2. Ask category-specific follow-up questions
3. Match the request against real provider data
4. Explain why a recommendation makes sense

**Hard constraint:** the AI must never invent availability, prices, ratings, or capabilities. Every claim must be grounded in real platform data — a RAG/grounding requirement, not a nice-to-have.

**Scope boundary:** "AI is the core" describes the customer/provider *experience*, not a requirement for custom AI/ML infrastructure. The architecture is an **LLM-API-driven, RAG-grounded conversation layer** (prompt-engineered against the platform's own provider database) — not a custom-trained matching model.

---

# 4. Two-Sided Supply

| Dimension | Formal Business | Individual Freelancer |
|---|---|---|
| Examples | Cafe, repair shop, bakery, salon | Plumber, electrician, AC technician, carpenter, tutor, car-washer |
| Location model | Fixed location, posted hours | Mobile — travels to the customer, service-radius based |
| Listing centers on | Location, hours, service/menu catalog | Skills, service radius, availability |
| Verification bar | Lighter (open decision, `13_OPEN_DECISIONS.md`) | Mandatory license/Emirates ID verification before listing goes live (enters customers' homes) |
| Supply bootstrapping | Seeded from Google listings as unclaimed entries + self-registration, with a claim-your-listing flow | Self-registration, gated on ID/license verification |
| Off-platform risk | Lower — fixed premises, less incentive to hide | Higher — mobile, one-to-one, easiest to take a repeat customer direct |

These two supply types share search, category, and review infrastructure, but require different profile schemas, trust mechanics, and anti-circumvention pressure. See `03_DOMAIN_MODEL.md` for how this is reflected in the Provider entity.

---

# 5. Platform, Market & Localization

- **Platform:** Native iOS/Android app (pivoted away from responsive-web-only). This extends the build timeline to roughly 12–16 weeks.
- **Launch market:** UAE (reuses the existing Emirates ID / Ejari-style OCR verification pipeline).
- **Localization:** Bilingual English/Arabic UI, confirmed for launch — not a post-launch add-on.
- The product's long-term identity remains country-agnostic in architecture even though UAE is now a confirmed (not tentative) launch market — no domain entity, workflow, or UI copy should hard-assume UAE-only regulatory or cultural context beyond the initial verification integration.

---

# 6. Auth & Contact Model

These are the two biggest reversals from the original concept and must be treated as locked:

- **Auth:** Customer registration is **mandatory** — via Google, Apple, or Mobile number + OTP. There is no guest path to submit a request or view a match.
- **Contact flow:** Once a customer views a matched provider, that provider's **phone number is shown directly** — no post-match contact gating, no quote-acceptance gate, no in-app chat/messaging layer. Contact and negotiation happen off-platform, by phone or WhatsApp, exactly as it would if the customer had gotten the number from a friend.
- **Booking model:** Single unified contact flow. Instant/predefined-price booking was scoped and dropped — there is no structured Quote object and no in-app booking state machine.

This is a deliberate **growth-first** trade-off: platform lock-in and revenue protection are secondary, at this stage, to making the contact experience frictionless enough that customers and providers actually use the product.

---

# 7. Revenue Model (Summary)

Free listings monetized purely through paid promotion is explicitly rejected — it doesn't generate revenue until search volume is already large.

- **MVP-compatible starting point:** pay-per-lead (charging providers per matched contact-view), since it requires no payment/booking infrastructure beyond usage metering.
- **Long-term target:** commission per completed job — deferred, since it requires payment infrastructure and a reliable transaction-completion signal that the current offline-contact model doesn't naturally produce.
- No in-app payment or monetization at launch — this is a deliberate growth-first sequencing decision, not an oversight.

---

# 8. Anti-Circumvention (Summary)

Because contact information is shown freely and immediately (Section 6), the anti-circumvention posture is necessarily lighter-touch than a staged-disclosure model would allow. Sequencing principle: **start with policy, defer engineering cost until leakage is a demonstrated revenue problem.**

Day-one, no-engineering-cost levers:
- Terms of Service restriction on off-platform solicitation abuse
- The "Did you hire them?" customer outcome tag, which doubles as the platform's only conversion signal and an informal leakage indicator
- Admin-side search analytics surfacing unmatched/failed queries, useful for spotting supply gaps as well as abuse patterns

Later-phase levers (deferred until leakage is provably costing revenue): masked communication, contact-info detection, reputation value-lock, dedicated leakage-signal monitoring. These are explicitly **not** MVP scope.

---

# 9. Value-Layer Features (Confirmed for MVP)

Beyond bare search-and-contact, the following are locked into MVP scope as trust- and engagement-building layers:

- **Arrival-verification OTP** ("Verified Visit" tag) — provider's choice to use, reuses existing OTP infrastructure
- **Portfolio/photos** on provider profiles
- **Provider-facing digital storefront framing** — the provider profile is positioned to providers as their free storefront, not just a listing
- **Basic visibility analytics** for providers (reusing the search event log — no new tracking infrastructure)
- **Shareable provider profile deep links**, designed for WhatsApp distribution
- **Admin-side search analytics** surfacing unmatched/failed queries, to guide category and supply expansion
- **Customer outcome tag** ("Did you hire them?") — the platform's only conversion signal; see Section 8
- **Claim-your-listing flow** for Google-seeded, unclaimed provider entries

---

# 10. What This Product Is Not

- Not a resident/community social platform — no membership gating, no feed, no posts/comments/reactions
- Not a full booking-and-payment product in v1 — see `11_MVP_SCOPE.md` for the explicit exclusion list
- Not built on custom-trained ML — the AI layer is LLM-API-driven and RAG-grounded
- Not a web-first product — native app is the confirmed platform, not a stretch goal
- Not a guest-accessible product — registration is mandatory before a request can be submitted

---

# 11. Changelog (v0.1.0 → v0.8.0)

| Area | v0.1.0 (original concept) | v0.8.0 (current, locked) |
|---|---|---|
| Platform | Responsive web app, web-only for v1 | Native iOS/Android app |
| Auth | Guest request allowed, no forced signup | Mandatory registration (Google/Apple/Mobile+OTP), no guest path |
| Contact flow | Staged disclosure — phone hidden until quote accepted | Direct phone visibility immediately after match |
| Booking model | RFQ → Quote → accept/reject → booked job | Single unified contact flow; no Quote entity, no instant/predefined-price booking |
| Messaging | In-app Message Thread tied to RFQ Request | Dropped entirely — no in-app chat/messaging layer |
| Localization | Not specified | English/Arabic bilingual UI confirmed for launch |
| Launch market | UAE "likely default," open decision | UAE confirmed |
| Value-layer features | Not specified | Verified Visit OTP, portfolio, storefront framing, visibility analytics, shareable deep links, outcome tag, claim-your-listing |

---

# 12. Related Documents

- `03_DOMAIN_MODEL.md` — entities, aggregates, business rules
- `11_MVP_SCOPE.md` — include/exclude scope for v1
- `13_OPEN_DECISIONS.md` — unresolved product decisions blocking downstream work (category taxonomy is currently critical-path)
- `14_USER_FLOWS.md` — step-by-step user journeys implementing this vision
- `16_UX_GUIDELINES.md` — interaction, content, and trust-building patterns implementing this vision

---

**End of Document**
