# AI Marketplace — User Flows

**Document ID:** AI-14
**Version:** 1.0.0
**Status:** Draft — pending product/engineering review
**Owner:** CTO
**Audience:** Engineering Team, Product Team, UI/UX, AI Assistants
**Last Updated:** 15 July 2026

---

# Purpose

This document maps the end-to-end step sequence of every core user journey in the AI Marketplace platform. `03_DOMAIN_MODEL.md` defines *what* the entities and business rules are; `04_DATABASE.md` defines *how* they're persisted; this document defines the *order of operations* a real Customer, Provider, or Admin moves through — the thing neither of those documents captures.

Each flow below lists: entry point, numbered steps, decision branches, the database rows/state created at each step (cross-referenced to `04_DATABASE.md` table names), and the business rules from `03_DOMAIN_MODEL.md` that apply. Flutter screen-level design should be derived from these flows, not the reverse — if a screen requires a step not listed here, add the step here first.

**Notation:** `→` means "leads to / produces." `⇒` marks a branch decision. Table names in backticks refer to `04_DATABASE.md`.

---

# 1. Customer Registration

**Entry point:** App opened with no active session; any action requiring auth (search, contact, review) redirects here first. There is no guest path (`03_DOMAIN_MODEL.md`, Identity & Access).

1. Customer selects a sign-up method: Google, Apple, or Mobile Number.
2. **⇒ Google / Apple:** OAuth consent screen → provider returns an ID token → backend verifies the token server-side against the provider's public keys (never trust a client-asserted identity) → `users` row created or matched via `(auth_provider, external_auth_subject)`.
3. **⇒ Mobile Number:** Customer enters phone number → OTP sent → `otp_verifications` row (`purpose = registration`) → Customer enters code → verified → `users` row created via `(phone_country_code, phone_number)`.
4. On first successful auth for a new account: create `customer_profiles` row, `customer_preferences` row (default channel `whatsapp`, language from device locale), and assign the `customer` role via `user_roles`.
5. Customer is prompted (optional, skippable) to add a first `saved_addresses` row.
6. Session established (`sessions` + `refresh_tokens` + `devices` row for this device) → Customer lands on the search/home screen.

**Exit state:** Registered Account with Customer role, ready to submit a Search Request.

---

# 2. Provider Registration & Onboarding

**Entry point:** "List your business or service" CTA — from the marketing site, the app menu, or an already-authenticated Customer adding the Provider role (see Flow 6).

1. Authenticate via the same mechanism as Flow 1. **If the user already has an Account** (e.g. an existing Customer), this step reuses that `users` row — it does not create a second account (see Flow 6, dual-role rule in `03_DOMAIN_MODEL.md`).
2. Choose Provider subtype: **Business** or **Freelancer** — immutable after creation; a Provider cannot switch subtype or hold both.
3. Enter shared profile fields: display name, phone/WhatsApp number, category (writes `provider_categories`), description.
4. **⇒ Business path:** address, latitude/longitude, operating hours, optional delivery radius, optional trade license number → `business_profiles` row.
   **⇒ Freelancer path:** base location, service radius, skills, years of experience → `freelancer_profiles` row.
5. `providers` row created: `listing_source = self_registered`, `is_claimed = true`, `verification_status = pending`, `is_discoverable = false`.
6. Upload verification documents:
   - **Freelancer:** Emirates ID / license — mandatory. OCR pipeline pre-extracts fields (`verification_documents.ocr_extracted_data`) for admin review; extraction is a candidate value, never auto-approved.
   - **Business:** per the configured verification bar (open decision, `13_OPEN_DECISIONS.md` item 5).
7. `verification_records` row created (`status = pending`) → Flow 7 (Admin Verification Review) takes over.
8. **⇒ Approved:** `providers.verification_status → approved`; `is_discoverable → true` (mandatory gate for Freelancer; per configured bar for Business). Provider notified.
   **⇒ Rejected:** `rejection_reason` recorded; Provider notified; may resubmit documents (new `verification_records` cycle, prior record retained).
9. Provider completes the storefront: portfolio photos (`portfolios`), weekly availability (`provider_availability`), emergency/urgent flag.
10. Once discoverable, the Provider appears in matching results for its category and service area (Flow 4).

**Exit state:** A live, discoverable Provider profile, or a rejected submission awaiting resubmission.

---

# 3. Claim-Your-Listing (Google-Seeded Unclaimed Business)

**Entry point:** A prospective owner finds their business listed with an "Unclaimed" label in search results (per the pending UX decision in `13_OPEN_DECISIONS.md` item 4) and taps "Claim this listing."

1. Authenticate or register (Flow 1 mechanism).
2. Confirm the business identity against the unclaimed `providers` row (`listing_source = google_seeded_unclaimed`, `google_place_id` populated).
3. OTP sent to the **public phone number on record** for that listing (`otp_verifications`, `purpose = claim_listing`) — not the claimant's own number, to prevent a stranger claiming someone else's listing.
4. **⇒ OTP verified:** proceeds through the same Verification gate as a self-registered Business (Flow 2, steps 6–8).
5. **⇒ OTP fails / no public number on record:** falls back to Admin manual review (documentation + identity check).
6. On approval: `providers.is_claimed → true`, `claimed_at` set, `user_id` populated with the claimant's Account.
7. Owner gains edit access to the profile and the provider dashboard (leads, analytics) for that listing.

**Exit state:** A previously unclaimed listing is now owned, editable, and analytics-enabled.

---

# 4. Core Flow — AI Intake → Search → Match → Contact

This is the product's differentiated core loop (`00_PROJECT_CONTEXT.md` §3). Entry point: an authenticated Customer taps "Describe what you need."

1. Customer enters a free-text problem description → `conversation_sessions` row created (`status = active`).
2. AI reads the message and attempts to resolve a Category. Once resolved, it asks category-specific follow-up questions sourced **only** from `category_question_templates` for that category — never an invented question outside the taxonomy.
3. Each Customer answer → a `messages` row (`sender = customer`), each AI question/response → a `messages` row (`sender = ai`), ordered by `sequence_number`.
4. After each turn, a confidence value is computed and written to `confidence_scores`; the latest value is cached on `conversation_sessions.final_confidence_score`.
5. **⇒ Confidence ≥ threshold:** `conversation_sessions.status → completed` → a `search_requests` row is produced (`structured_criteria`, `category_id`, customer lat/lng).
   **⇒ Confidence < threshold:** `conversation_sessions.status → routed_to_admin` → a `manual_match_assignments` row is created and an Admin is notified (Wizard-of-Oz fallback). The Customer's downstream experience (step 9 onward) does not visibly change — they still receive a ranked provider list, sourced from the Admin's manual selection instead of the automated matcher.
6. Matching filters run in order — Category → geospatial radius (`service_areas`, see `geospatial-matching` skill) → discoverability/verification gate — then rank by merit (rating + review volume + proximity), writing ranked `provider_matches` rows.
7. Regardless of outcome, a `search_event_log` row is written (`was_matched` true/false) — feeds Admin unmatched-query analytics (`unmatched_query_reports`) and Provider visibility analytics.
8. Customer sees the ranked Provider list: name, rating, photos, distance — **no phone number yet**.
9. Customer opens a Provider's profile and taps "Contact."
10. **Self-dealing check:** if the Customer's Account also owns this Provider (see `03_DOMAIN_MODEL.md`, Contact View business rules), the request is rejected — a Provider cannot generate a Contact View against their own listing. Otherwise, a `contact_views` row is created and the Provider's phone number is displayed directly, immediately, with no further gating.
11. Customer contacts the Provider off-platform (call/WhatsApp). Negotiation and job execution are not tracked in-app.
12. **Optional:** Provider requests an arrival OTP on-site → `visit_verifications` row created, unlocking the "Verified Visit" tag.
13. Some time after the Contact View, the app prompts the Customer: "Did you hire them?" → `outcome_tags` row recorded.
14. **⇒ `hired = true`:** Customer may submit a Review (rating 1–5 + comment) → `reviews` row → `provider_rating_summaries` recalculated for that Provider.
    **⇒ `hired = false` or no response:** flow ends; the Outcome Tag itself is still retained as the platform's conversion/leakage signal.

**Exit state:** A completed Contact View, and optionally an Outcome Tag and/or Review.

---

# 5. Dual-Role Flow (Adding the Other Role to an Existing Account)

**Entry point:** An authenticated user with only one role taps "Also list your business" (from a Customer account) or "Search for a service" (from a Provider account).

1. **⇒ Provider account adding Customer role:** create `customer_profiles` + `customer_preferences` for the same `users.id`; add `customer` via `user_roles`. No re-authentication required — same login, same JWT `sub`.
2. **⇒ Customer account adding Provider role:** proceeds through Flow 2 (Provider Registration) using the same `users.id`; add `provider` via `user_roles`.
3. Once both roles exist on one Account, the app surfaces a role switcher (Customer view ⇄ Provider dashboard) within the same session.
4. From this point on, the self-dealing guard in Flow 4 step 10 is active for this Account against its own Provider listing.

**Exit state:** One Account, two active roles, one login.

---

# 6. Admin Verification Review

**Entry point:** A new or resubmitted `verification_records` row (`status = pending`) enters the Admin review queue.

1. Admin opens the queue, reviews uploaded documents and any OCR-extracted data (`verification_documents`).
2. **⇒ Approve:** `verification_records.status → approved`, `reviewed_by` + `reviewed_at` recorded. In the same transaction, `providers.verification_status` and `providers.is_discoverable` are recomputed — never left stale.
3. **⇒ Reject:** `status → rejected`, `reviewed_by` + `rejection_reason` recorded. Provider may resubmit (Flow 2 / Flow 3, new cycle).
4. Provider is notified of the status change (Flow 8) regardless of outcome.
5. Action recorded in `admin_action_log`.

**Exit state:** Provider is discoverable (approved) or blocked with a reason (rejected).

---

# 7. Wizard-of-Oz Manual Match (Admin Side)

**Entry point:** A `manual_match_assignments` row created by Flow 4 step 5 (low-confidence session).

1. Admin opens the assignment, reviews the Conversation Session transcript (`messages`) and any partially-structured criteria.
2. Admin manually selects and ranks candidate Providers for the underlying `search_requests` row — written as `provider_matches` rows, same table the automated matcher would have used.
3. `manual_match_assignments.status → completed`.
4. Customer sees the result exactly as in Flow 4 step 8 onward — the manual origin is invisible to the Customer.

**Exit state:** A `search_requests` row is resolved without fully-automated matching.

---

# 8. Notification Triggers (Cross-Cutting)

Not a standalone journey — this table lists every point across the flows above where a Notification is generated, per `03_DOMAIN_MODEL.md` (Notification domain).

| Trigger | Recipient | Source Flow |
|---|---|---|
| New Contact View (lead) | Provider | Flow 4, step 10 |
| Verification status changed (approved/rejected) | Provider | Flow 6, step 4 |
| Outcome Tag prompt | Customer | Flow 4, step 13 |
| Manual match assignment created | Admin | Flow 4, step 5 |
| Claim-listing OTP fallback needed | Admin | Flow 3, step 5 |

All sends respect `notification_preferences` (channel + per-category opt-outs) before dispatch — a disabled channel is a hard stop, per the `third-party-integrations` skill.

---

# Related Documents

- `00_PROJECT_CONTEXT.md` — why these flows exist, growth-first contact model
- `03_DOMAIN_MODEL.md` — entities and business rules referenced throughout
- `04_DATABASE.md` — table-level detail for every row created in these flows
- `07_UI_GUIDELINES.md` — screen-level design should implement these flows, not redefine them
- `11_MVP_SCOPE.md` — confirms no Quote/messaging/payment steps exist in any flow above
- `13_OPEN_DECISIONS.md` — items 1, 3, 4, 5 directly affect Flows 2–4 and will update this document when resolved
- `15_SCREEN_INVENTORY.md` — screen-level implementation of these flows
- `16_UX_GUIDELINES.md` — interaction and content rules for each step above

---

**End of Document**
