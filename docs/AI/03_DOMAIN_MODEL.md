# AI Marketplace — Domain Model

**Document ID:** AI-03
**Version:** 0.8.1
**Status:** Draft — Aligned to MVP Scope v0.8.0
**Owner:** CTO
**Audience:** Engineering Team, Product Team, AI Assistants
**Last Updated:** 15 July 2026

**Change note (v0.8.0 → v0.8.1):** Added an explicit rule that one Account may hold both the Customer and Provider roles simultaneously (Identity & Access), and the resulting self-dealing restriction on Contact View / Review — a Provider cannot generate a Contact View or Review against their own listing.

---

# Purpose

This document defines the core business domain of the AI Marketplace platform. It identifies the primary business entities, their responsibilities, ownership, relationships, and boundaries.

This document represents the business model, not the database schema. Database implementation details belong in `04_DATABASE.md`.

**This domain model has no Community aggregate.** Discovery is driven by location and category alone, not by a closed, verified community.

**Change note (v0.1.0 → v0.8.0):** The original domain model was built around an RFQ → Quote → Messaging transactional loop with staged contact disclosure. That loop has been replaced by a single unified contact flow: a match produces a direct, immediately visible contact — there is no Quote entity and no Messaging domain. See `00_PROJECT_CONTEXT.md` Section 11 for the full changelog.

---

# Domain Overview

The platform connects two supply types — **Businesses** and **Freelancers** — with **Customers**, through an AI-mediated conversational intake that produces a structured **Search Request**, matched against provider data, and resolved through a direct **Contact View** and, optionally, a self-reported outcome.

```
Customer (registered — mandatory)

↓ starts

Conversation / AI Intake Session

↓ produces

Search Request

↓ matched against

Provider (Business | Freelancer)

↓ customer views matched provider

Contact View (phone number shown directly)

↓ off-platform contact & job (not tracked in-app)

↓ customer self-reports

Outcome Tag ("Did you hire them?") → enables Review
```

---

# Core Domains

## Identity & Access

### Purpose
Authentication, authorization, and account security for both customers and providers.

### Entities
- Account
- Session
- Refresh Token
- Role (Customer / Provider / Admin)
- Device

### Business Rules
- **Customer registration is mandatory** — via Google, Apple, or Mobile number + OTP. There is no guest path; an Account must exist before a Search Request can be submitted or a Contact View can occur.
- A Provider Account is always linked to exactly one Provider profile (Business or Freelancer). A Provider cannot hold two Provider profiles (e.g. cannot be both a Business and a Freelancer under one Account).
- **An Account may hold both the Customer and Provider roles simultaneously.** A Business owner or Freelancer is not blocked from also registering a Customer Profile and using the platform to search for and contact other Providers — this is one Account with two optional profiles, not two separate accounts. See the self-dealing restriction under Contact View below, which exists specifically because this dual-role case is allowed.

---

## Customer

### Purpose
Represents the person seeking a service.

### Entities
- Customer Profile
- Saved Address / Location
- Preferences (notification channel, language: English/Arabic)

### Business Rules
- A Customer must be a registered Account — no guest submission.
- A Customer may have multiple saved addresses but one active location per request.

---

## Provider

### Purpose
Represents supply on the platform. This is a single aggregate with two subtypes carrying different schemas and trust mechanics, per `00_PROJECT_CONTEXT.md` Section 4.

### Entities
- Provider (base)
- Business Profile (subtype) — fixed location, posted hours, service/menu catalog
- Freelancer Profile (subtype) — skills, service radius, availability, mobile service area
- Provider Availability — working hours, emergency/urgent availability flag
- Portfolio (photos)
- Listing Source (Self-Registered | Google-Seeded-Unclaimed)

### Business Rules
- Every Provider is exactly one subtype: Business or Freelancer. A Provider cannot be both.
- A Freelancer Provider cannot go live (be discoverable) until Verification status is `Approved`.
- A Business Provider's verification bar is lighter and configurable per `13_OPEN_DECISIONS.md`.
- A Provider seeded from Google listings starts as `Unclaimed` and is discoverable, but cannot be edited or receive its own analytics until it is claimed (see Claim Flow below).
- Provider profile includes: name, services offered, areas covered, price ranges, portfolio photos.
- Provider profile doubles as a "digital storefront" — this framing affects copy and onboarding, not schema.

---

## Category

### Purpose
Defines the taxonomy that structures both provider listings and AI question-flows.

### Entities
- Category
- Category Question Template (drives the AI's category-specific follow-up questions)

### Business Rules
- A Provider belongs to one or more Categories.
- Category taxonomy is the current **critical-path open decision** (`13_OPEN_DECISIONS.md`) — it blocks AI question-flow design and must be locked before that work starts.
- Start narrow: launch with a small number of categories, expand once matching is proven.

---

## Service Area

### Purpose
Defines where a Provider can be discovered and matched.

### Entities
- Service Area (geo-radius or defined zone)
- Location (Customer request location)

### Business Rules
- A Business Provider's Service Area is derived from its fixed location plus an optional delivery/service radius.
- A Freelancer Provider's Service Area is a configurable radius around a base location, since freelancers travel to the customer.
- Matching requires the Customer's Location to fall within a Provider's Service Area.

---

## Conversation / AI Intake Session

### Purpose
The core differentiated mechanism of the product. Understands an unstructured customer problem, asks follow-up questions, and produces a structured Search Request.

### Entities
- Conversation Session
- Message (customer / AI turns — this is the AI intake chat, not customer-provider messaging, which does not exist in this model)
- Confidence Score (per session, drives Wizard-of-Oz fallback routing)

### Business Rules
- Every Conversation Session belongs to exactly one (registered) Customer and results in zero or one Search Request.
- The AI must never assert availability, prices, ratings, or capabilities not grounded in real platform data (hard constraint, see `00_PROJECT_CONTEXT.md` Section 3).
- Sessions below a confidence threshold are routed to manual admin-assisted matching (Wizard-of-Oz fallback) rather than blocking on full automation.
- A Conversation Session is not a public/social artifact — it is private between the Customer and the platform.

---

## Search Request

### Purpose
A structured, matchable representation of the customer's need, produced by the Conversation/AI Intake Session.

### Entities
- Search Request
- Search Event Log (every request/query, matched or not — feeds provider analytics and admin unmatched-query analytics)

### Business Rules
- A Search Request belongs to one Customer and one Category.
- A Search Request produces a ranked set of matched Providers, not a Quote and not a booked job — there is no RFQ→Quote transactional state machine in this model.
- Unmatched or low-result Search Requests are logged for admin review, to surface supply gaps and category taxonomy issues.

---

## Contact View

### Purpose
Represents a customer viewing a matched provider's contact details. This replaces the old Quote/staged-disclosure step entirely.

### Entities
- Contact View (Customer × Provider × Search Request, timestamped)

### Business Rules
- A Contact View shows the Provider's phone number directly and immediately — no acceptance step, no gating.
- Contact Views are the basis for: (a) provider visibility analytics, (b) pay-per-lead billing (post-MVP), and (c) eligibility to submit an Outcome Tag or Review.
- All subsequent negotiation and job execution happen off-platform and are not modeled as platform entities.
- **Self-dealing restriction:** since an Account may hold both the Customer and Provider roles (see `Identity & Access` above), a Contact View must be rejected if the requesting Customer's Account is the same Account that owns the target Provider. A Provider cannot generate a Contact View, Outcome Tag, or Review against their own listing. This cannot be expressed as a single-table constraint — it must be enforced where the Contact View is created, by checking the Customer's Account against the Provider's owning Account.

---

## Outcome Tag

### Purpose
The platform's only conversion signal, given the offline-payment reality of the contact model.

### Entities
- Outcome Tag ("Did you hire them?" — Yes / No, tied to a Contact View)

### Business Rules
- An Outcome Tag can only be submitted by the Customer who generated the corresponding Contact View.
- A "Yes" Outcome Tag is a prerequisite for that Customer to submit a Review against that Provider (anchor-verified review, not open review).
- Outcome Tag data does not attempt to track payment amount, job completion detail, or scheduling — it is intentionally minimal.

---

## Provider Dashboard (functional, not a distinct aggregate)

### Responsibilities
- View incoming Contact Views (leads)
- View basic visibility analytics (reusing the Search Event Log)
- Claim an unclaimed, Google-seeded listing
- Manage portfolio photos and profile details

---

## Verification

### Purpose
Establishes trust before a Provider can be discovered (Freelancer) or claim a listing (Business/Freelancer).

### Entities
- Verification Record
- Verification Document (Emirates ID, trade license, etc.)
- Verification Status (Pending → Under Review → Approved → Rejected)

### Business Rules
- Mandatory for all Freelancer Providers before their listing goes live — a safety issue (freelancers enter customers' homes), not just a quality one.
- Freelancer verification reuses the existing Ejari/Emirates ID OCR pipeline as a reusable asset — this is an extension, not a rebuild.
- Business Provider verification path is lighter and is an open decision (`13_OPEN_DECISIONS.md`).
- Claiming a Google-seeded listing requires passing the same Verification gate as a self-registered Provider of that type.

---

## Review

### Purpose
Captures customer feedback tied to a Contact View with a positive Outcome Tag, and drives Provider ranking.

### Entities
- Review
- Rating

### Business Rules
- A Review can only be created against a Contact View with a "Yes" Outcome Tag — **anchor-verified**, not open/unrestricted review submission.
- Provider ranking is merit-based, driven by Reviews and completed-Contact-View volume rather than a paid-placement model.
- Because a Review always anchors to a Contact View, the self-dealing restriction on Contact View (see above) transitively blocks a Provider from reviewing their own listing — no separate check is needed here as long as the Contact View rule is enforced.

---

## Notification

### Purpose
Delivers time-sensitive platform events to Customers and Providers.

### Entities
- Notification
- Notification Channel (WhatsApp / SMS / Email)
- Delivery Status

### Business Rules
- Notifications are triggered by: new Contact View (lead) for a Provider, Verification status change, Outcome Tag prompt for a Customer.
- Channel preference is configurable per user.

---

## Administration

### Purpose
Platform management, manual verification, and matching assistance.

### Entities
- Admin User
- Admin Action Log
- Manual Match Assignment (for low-confidence AI Conversation Sessions)
- Unmatched Query Report (from the Search Event Log)

### Business Rules
- How much of matching is "manual behind the scenes" at launch is an open decision (`13_OPEN_DECISIONS.md`) that directly affects this domain's dashboard scope.
- Unmatched Query Reports are a primary input for category taxonomy and supply-gap decisions.

---

# Aggregate Roots

| Aggregate | Child Entities |
|---|---|
| Customer | Saved Addresses, Preferences |
| Provider | Business Profile / Freelancer Profile, Availability, Portfolio, Verification Record |
| Search Request | Search Event Log entries, matched Provider references |
| Conversation Session | Messages (AI intake), Confidence Score |
| Contact View | Outcome Tag |
| Review | Rating |
| Notification | Delivery Records |

---

# Explicitly Out of Scope for This Domain Model

The following are deferred per `11_MVP_SCOPE.md` and must not be implemented unless the MVP scope is formally expanded:

- Quote entity, Quote Status, and any RFQ→Quote transactional state machine
- Messaging domain (Message Thread, customer-provider chat) — dropped entirely, not deferred to a later stage
- Complex online payments / escrow / payout — no Payment or Transaction aggregate in v1
- Dynamic pricing engine
- Instant/predefined-price booking
- Loyalty programs, subscriptions-as-a-feature, automated dispute management
- Masked communication (proxy phone numbers), contact-info detection, leakage-signal monitoring — all later-phase anti-circumvention hardening

---

# Domain Events

```
CustomerRegistered
ConversationSessionCompleted
SearchRequestSubmitted
SearchRequestUnmatched
ProviderMatched
ContactViewCreated
OutcomeTagSubmitted
ReviewSubmitted
ProviderVerificationApproved
ProviderVerificationRejected
ListingClaimed
NotificationSent
```

Events should represent completed business actions.

---

# Cross-Domain Communication

Domains communicate through services and domain events. Direct access to another domain's internal data is prohibited.

Allowed:
```
Search Request Service → Provider Matching Service
```

Not allowed:
```
Contact View Repository → Provider Database Tables (direct)
```

---

# Related Documents

- `00_PROJECT_CONTEXT.md`
- `04_DATABASE.md`
- `11_MVP_SCOPE.md`
- `13_OPEN_DECISIONS.md`
- `14_USER_FLOWS.md`
- `16_UX_GUIDELINES.md`

---

**End of Document**
