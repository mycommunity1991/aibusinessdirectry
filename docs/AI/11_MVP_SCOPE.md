# AI Marketplace — MVP Scope

**Document ID:** AI-11
**Version:** 0.8.0
**Status:** Draft — Authoritative (supersedes v0.1.0's RFQ/web-only MVP)
**Owner:** CTO
**Audience:** Engineering Team, Product Team, AI Assistants
**Source:** Iterative scoping decisions through v0.8.0
**Last Updated:** 14 July 2026

---

# Purpose

This document defines what is and is not built in v1. It is authoritative for sprint story scoping. No implementation story may introduce functionality outside this defined scope without a formal scope change recorded in `13_OPEN_DECISIONS.md`.

**Change note:** v0.1.0 targeted a responsive web app with guest access and an RFQ/Quote flow with staged contact disclosure. That entire model has been superseded. v0.8.0 is a native app, mandatory-registration, direct-contact model. See `00_PROJECT_CONTEXT.md` Section 11 for the full changelog.

---

# 1. Include in MVP

- **Mandatory customer registration** — Google, Apple, or Mobile number + OTP. No guest path.
- AI-based service request conversation (understand → ask → match → explain)
- Location and service-area matching
- Provider profiles — name, services, areas covered, price ranges, portfolio photos
- Provider availability — working hours, emergency/urgent availability
- **Single unified contact flow** — customer views a matched provider and sees their phone number directly; no quoting step, no instant/predefined-price booking
- Provider dashboard — view leads (Contact Views), basic visibility analytics, manage profile/portfolio, claim listing
- Admin dashboard — manual verification, request review, matching assistance, unmatched-query analytics
- Anchor-verified reviews and ratings, tied to a positive Outcome Tag on a Contact View
- Merit-based provider ranking algorithm
- WhatsApp / SMS / email notifications for leads, verification status, and Outcome Tag prompts
- Mandatory license/Emirates ID verification for freelancers before their listing goes live (reusing the existing Ejari/Emirates ID OCR pipeline)
- Supply bootstrapping: Google listings seeded as unclaimed entries, plus self-registration and a claim-your-listing flow
- English/Arabic bilingual UI
- Arrival-verification OTP ("Verified Visit" tag), provider's choice, reusing existing OTP infrastructure
- Shareable provider profile deep links, designed for WhatsApp distribution
- Customer outcome tag ("Did you hire them?") as the platform's only conversion signal

---

# 2. Explicitly Excluded from v1

- In-app payment or monetization of any kind at launch (growth-first strategy)
- A Quote entity or any RFQ→Quote transactional state machine
- Instant/predefined-price booking
- In-app customer-provider chat/messaging layer of any kind — post-match contact is direct phone visibility, not mediated messaging
- Complex online payments, escrow, payout, and a dynamic pricing engine
- Full scheduling optimization
- Loyalty programs, advanced subscriptions, automated dispute management
- Masked communication (proxy phone numbers), contact-info detection/filtering, dedicated leakage-signal monitoring — all deferred until leakage is a demonstrated revenue problem
- Dozens of service categories — start narrow; category taxonomy is a locked-before-build critical-path decision (`13_OPEN_DECISIONS.md`)

**None of these are a permanent "never."** Each is a real later-phase feature, deliberately deferred so v1 ships fast — with the exception of the RFQ/Quote and messaging models, which were evaluated and dropped, not merely deferred.

---

# 3. Build Sequence (Reference)

| Stage | What Ships | Why This Order |
|---|---|---|
| 1 | Category taxonomy locked; directory + location/category search, provider & customer profiles, native app shell (iOS/Android), bilingual UI | Proves core discovery with zero verification/contact dependency; category taxonomy is the hard blocker for Stage 2 |
| 2 | AI-based intake conversation (LLM-API + RAG-grounded) + matching + direct Contact View flow | Differentiated core; ships with manual (Wizard-of-Oz) fallback rather than waiting for a fully automated matcher |
| 3 | Mandatory freelancer ID verification (OCR-based pipeline) + admin dashboard + claim-your-listing flow | Required before trust-sensitive listings go fully live; gates public launch |
| 4 | WhatsApp/SMS/email notifications + Outcome Tag + anchor-verified reviews/ratings + basic provider analytics | Completes the feedback loop and gives providers a reason to stay engaged |
| 5 | Value-layer polish: Verified Visit OTP, portfolio, shareable deep links, storefront framing | Trust and distribution features that don't block core loop but strengthen retention |
| 6 (post-v1) | Pay-per-lead billing | Revenue layer, added once there is real lead (Contact View) volume to monetize |
| 7 (later) | Anti-circumvention hardening (masking, filtering, leakage analytics) | Deferred until leakage is provably costing real revenue |
| 8 (long-term) | Commission-based revenue model, payment infrastructure if ever needed | Highest complexity — only pursued if pay-per-lead proves insufficient |

Native app build extends the realistic timeline to **~12–16 weeks**, up from the original 6–10 week web-only estimate — this is an accepted trade-off for the platform decision in Section 5 of `00_PROJECT_CONTEXT.md`.

---

# 4. Day-One Anti-Circumvention (In Scope, No Extra Engineering Cost)

Because contact information is shown directly and immediately (growth-first decision, `00_PROJECT_CONTEXT.md` Section 6), there is no staged-disclosure lever available in this model. Day-one levers are policy-only:

- Terms of Service restriction on off-platform solicitation abuse, with account suspension as the enforcement mechanism
- "Did you hire them?" Outcome Tag as an informal leakage/conversion signal
- Admin-side unmatched/failed-query analytics, useful for supply-gap and abuse-pattern visibility

Masked communication, contact-info detection, and dedicated leakage-signal monitoring are explicitly **later-phase** — do not build these in v1.

---

# 5. Revenue Model — MVP Approach

**MVP-compatible starting point:** pay-per-lead, metered on Contact Views — this requires no payment/booking infrastructure beyond usage metering, and is deferred to post-v1 (Stage 6 above). No payment processing is required for v1 launch itself. Commission-per-completed-job is the long-term target once a reliable transaction-completion signal exists. Full detail lives in `00_PROJECT_CONTEXT.md` Section 7.

---

# 6. Scope Guardrails for AI-Assisted Implementation

AI assistants implementing sprint stories must not implement, even incidentally:

- A Quote entity, Quote status machine, or instant/predefined-price booking flow
- Any customer-provider in-app messaging/chat feature
- Payment or escrow logic of any kind
- Masked-communication/telephony proxy integration
- Chat content scanning/filtering
- Loyalty, subscription-tier, or dispute-automation logic
- A guest/unauthenticated path to Search Requests or Contact Views

...unless a story explicitly scopes it and `13_OPEN_DECISIONS.md` has been updated accordingly.

---

# Related Documents

- `00_PROJECT_CONTEXT.md`
- `03_DOMAIN_MODEL.md`
- `13_OPEN_DECISIONS.md`
- `14_USER_FLOWS.md`

---

**End of Document**
