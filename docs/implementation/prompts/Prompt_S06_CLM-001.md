# Prompt for Story CLM-001 — Claim My Google-Seeded Business Listing

**Sprint:** 06 | **Epic:** ML6-EP02 | **Milestone:** ML6 | **Phase:** PH2 | **Priority:** Medium |
**Depends On:** VER-002, DIR-001 (both done)

---

## Original Task Given To `tech-lead`

Plan Story CLM-001 ("Claim my Google-seeded business listing," Sprint 6, Epic ML6-EP02, Milestone ML6, Phase PH2,
Priority Medium, Depends On: VER-002/DIR-001 — both done). Plan only, no code.

**Description (verbatim, from `docs/AI/Project_Tracker.xlsx`):** As a business owner, I want to find my business
among Google-seeded listings and verify I own the public phone number on record, so that I gain edit access to my
own storefront instead of a stranger being able to claim it. This story bootstraps Business supply from public
Google listings (so the directory isn't empty at launch) and implements the claim flow's OTP-against-public-
record safeguard. Until claimed, these listings are flagged internally as unclaimed per the pending Google
Places legal/ToS review, and must never be treated as equivalent to a verified, self-registered provider. Scope
boundary: does not change how self-registered providers (PRO-001) are created — this story only handles the
separate unclaimed-listing import and claim path.

**Acceptance Criteria (verbatim, 8 items):**
1. Import job creates providers rows with `listing_source=google_seeded_unclaimed`, `is_claimed=false`, and a
   populated `google_place_id` — never marked as `self_registered`.
2. Unclaimed listings are visually distinct in search/directory results (a clearly visible "Unclaimed" label,
   not a small badge easy to miss).
3. Claim search screen lets a user find their business by name/location among unclaimed listings.
4. An OTP is sent to the public phone number on record for that listing — never to a number the claimant types
   in themselves.
5. Successful OTP verification sets `is_claimed=true`, populates `user_id` with the claimant's Account, and
   routes the listing through the same Verification gate a self-registered Business would go through.
6. If OTP verification fails or the public number is unusable, the flow falls back to an explicit "this isn't
   working" admin-review path.
7. Once claimed, subsequent Google Places sync jobs never overwrite owner-edited fields — imported data only
   backfills genuinely empty fields.
8. Automated tests cover: OTP-goes-only-to-public-number, and the admin-fallback path triggering correctly on
   OTP failure.

**Critical context supplied with the task:** `docs/AI/13_OPEN_DECISIONS.md` item 3 (Google Places Data Legal
Review) remains genuinely Open at the legal level (no counsel review, no first-party ToS reading has happened),
but the CTO reviewed several lower-risk alternative designs (live-query-only, rolling cache, fetch-verify-then-
store, human-sourced leads) and made an explicit, informed decision to proceed with `CLM-001` in its **original
bulk-import scope** anyway, accepting the known risk. The Plan must build exactly that — bulk import into
permanent `providers` rows, unverified at seed time, OTP-to-public-number as the claim-time trust gate — and must
not substitute any of the declined lower-risk alternatives. The future owner-verification-before-trust
improvement is explicitly out of scope, deferred work.

**Reading list specified for this Plan:** `13_OPEN_DECISIONS.md` items 3 and 4 (item 4 — Unclaimed Listing UX —
already resolved: a full-width Warning-color `#F59E0B` banner, "Unclaimed — Is this your business? Claim it,"
per `16_UX_GUIDELINES.md`'s Trust & Verification UX Patterns section — use as specified, don't reinvent);
`04_DATABASE.md` (confirm `providers.listing_source`/`is_claimed`/`google_place_id`/`user_id` nullability/
constraints, and whether a migration is even needed); `14_USER_FLOWS.md` Flow 3 (Claim-Your-Listing);
`15_SCREEN_INVENTORY.md` (any existing S-2x screen spec for claim search/OTP); `03_DOMAIN_MODEL.md` (how
`listing_source`/`is_claimed` fit the Provider entity's business rules); precedent plans
`Plan_S05_VER-001.md` (existing OTP mechanism, reuse not reinvent), `Plan_S06_DIR-001.md` (search module
precedent), `Plan_S04_PRO-001.md`/`Plan_S04_PRO-002.md` (the Provider/Business aggregate a claimed listing must
route into, and the verification gate — VER-001's submission flow).

**Explicit investigation asked for before planning:** whether the four `providers` columns already exist as
columns today (checking `backend/app/modules/provider/models.py` and its migrations — DIR-001's Plan had noted
they exist but are unused); whether an import/background-job pattern already exists anywhere in this codebase to
model the import job after, or whether this is new infrastructure territory; whether the existing `identity` OTP
mechanism (phone login/registration) can be reused directly for "send OTP to a specific business's public number
and verify a code," or needs adaptation; what a valid "Business" provider row minimally requires (PRO-001) versus
what Google's Places API actually provides (name, address, phone, `google_place_id`) — and how the import job
handles the gap.

**Output format specified:** `docs/implementation/plans/Plan_S06_CLM-001.md` in this codebase's established
format — Story summary, Acceptance Criteria copied verbatim, Verified Current State, numbered Architecture
Decisions with alternatives-considered, Backend Proposed Changes, Mobile Proposed Changes (if in scope),
Explicitly Out of Scope, Delegation & Execution Sequence, Verification Plan mapped to the 8 ACs, Related
Documents. Flag explicitly, per established practice, anything genuinely blocked pending CTO confirmation before
backend work starts — while noting the two things that could look like open questions (legal/risk posture,
unclaimed-listing visual design) are both already decided and should not be re-raised. Architecture Decisions
were asked to focus on genuine implementation-shape questions: how the import job is triggered/scheduled (one-
time seed vs. recurring sync — AC7 implies recurring), how required-but-Google-doesn't-provide Business fields
are defaulted, the OTP-reuse-vs-new-mechanism decision, and how AC6's admin-review fallback concretely works
given no admin dashboard UI exists (VER-002 precedent: backend-only admin API).

---

## Resulting Plan

See `docs/implementation/plans/Plan_S06_CLM-001.md` for the full Plan produced from this prompt, including all
Architecture Decisions, Backend/Mobile Proposed Changes, and the Verification Plan mapped to the 8 ACs above.

---

**End of Document**
