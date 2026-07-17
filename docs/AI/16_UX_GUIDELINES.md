# AI Marketplace — UX Guidelines

**Document ID:** AI-16
**Version:** 1.0.0
**Status:** Draft — pending product/design review
**Owner:** CTO & Product Owner
**Audience:** UI/UX Designers, Flutter Developers, Copywriters, AI Assistants
**Last Updated:** 15 July 2026

---

# Purpose

`07_UI_GUIDELINES.md` defines how the app **looks** (visual system). `15_SCREEN_INVENTORY.md` defines **what screens exist and what's on them**. This document defines how the app **behaves and communicates** — interaction rules, response-time handling, content tone, and the trust-building patterns this specific product depends on. A screen can follow every visual-system rule and every layout in the inventory and still fail its user if it responds too slowly with no feedback, or explains an error in internal jargon. That failure mode is what this document exists to prevent.

---

# UX Principles

Adapted from established usability heuristics, made specific to this product rather than left generic:

1. **Visibility of system status.** The user must never wonder "did that work?" This matters most in three places specific to this product: the AI conversation (response latency), verification status (a multi-day async process), and Contact View/Outcome Tag (an action with real-world consequences the app can't observe). See dedicated sections below for each.
2. **Speak the user's language, not the domain model's.** Internal entity names (`Conversation Session`, `Outcome Tag`, `Contact View`, confidence score) exist in `03_DOMAIN_MODEL.md` for engineering precision. None of them should appear as literal user-facing copy. See the mapping table below.
3. **User control and freedom.** During the AI Conversation (`S-07`), the user must be able to go back and revise a previous answer without restarting the whole conversation. A "Start over" option must exist but never be the only path back.
4. **Recognition over recall.** Never make the user remember something the app already knows — e.g. don't re-ask a question the AI already extracted from an earlier free-text answer in the same session.
5. **Error prevention over error messages.** Validate inline before submission is even possible (e.g. disable "Verify" until the OTP field has the expected digit count) rather than letting the user submit and then explaining what went wrong.
6. **Recovery over dead ends.** Every error state offers a next step — retry, edit, contact support, or (for the AI conversation specifically) a graceful fallback that the user experiences as "we'll handle this for you," never as a failure message. This is the user-facing face of the Wizard-of-Oz fallback in `14_USER_FLOWS.md` Flow 4/7 — the user must never see the words "manual" or "fallback."
7. **Minimalism, but not at the cost of trust.** `07_UI_GUIDELINES.md` calls for removing unnecessary information — but verification status, unclaimed-listing labeling, and rating counts are never "unnecessary," even when they add visual weight. Trust information is load-bearing content, not decoration to trim.

---

# Perceived Performance & Latency (AI Conversation)

The AI Conversation (`S-07`) is the one screen in the product where a real backend call (LLM + retrieval) takes longer than a typical mobile interaction. Handle this explicitly rather than treating it like any other async call:

- **0–500ms:** typing indicator only (three-dot animation), no text.
- **500ms–3s:** typing indicator is sufficient; do not add a text label yet — adding "Thinking..." too early reads as slower, not faster.
- **>3s:** switch to a contextual label matched to what's actually happening — "Finding matches near you," not a generic "Loading." Never show a raw percentage or the internal confidence score.
- **>8s or a timeout:** do not let the user sit on a spinner indefinitely. Transition to: "This is taking a moment — we'll notify you as soon as we have matches," close the session gracefully, and let the Wizard-of-Oz fallback take over silently in the background (`14_USER_FLOWS.md` Flow 4 step 5 / Flow 7). The user later gets a normal-looking result; they never learn it took a detour through manual matching.
- Never freeze input controls while waiting — if the user wants to add more context while the AI is "thinking," queue it rather than blocking the text field.

---

# Content & Microcopy Standards

**Tone:** calm, plain-language, professional-but-warm. Not corporate-cold ("Your request has been submitted for processing"), not casual-slangy ("Yay, we found you some pros!"). Read every string out loud — if it sounds like something a person would actually say to a friend asking for help finding a plumber, it's right.

**Internal term → user-facing copy** (never leak the left column into UI text):

| Internal (domain model) term | User-facing equivalent |
|---|---|
| Conversation Session | "your request" / the chat itself, unnamed |
| Confidence Score | never shown to users, in any form |
| Search Request | "your request" |
| Provider Matches | "matches" / "results near you" |
| Contact View | not named as a noun — it's the *result* of tapping "Contact," not a concept the user needs |
| Outcome Tag | "Did you hire them?" (already plain — keep this exact phrasing, don't rename it to something more "clever") |
| Verification Status: Pending / Under Review | "We're reviewing your documents" |
| Verification Status: Approved | "You're verified" + badge |
| Verification Status: Rejected | "We couldn't verify this" + the specific `rejection_reason`, in plain language, + how to fix it |
| Wizard-of-Oz / Manual Match Assignment | never surfaced in any form |
| `listing_source = google_seeded_unclaimed` | "Unclaimed listing" badge + "Is this your business? Claim it" |
| Service Area / radius | "how far they'll travel" (Freelancer) / "areas they serve" (Business) |

**Error message formula:** what happened, in plain language + what to do next. Never surface a stack trace, HTTP status code, or internal identifier (per `06_SECURITY.md`). "We couldn't verify your Emirates ID — the photo was too blurry to read. Try again with better lighting" — not "Verification failed: OCR confidence 0.31."

**Empty state formula:** why it's empty + one primary action. "No matches yet — describe what you need and we'll find someone nearby" (Home, first-time) is different from "No results for this search — try widening your search area" (Search Results, post-search) — don't reuse one generic empty state for both.

**Destructive action copy:** state the actual consequence, not a generic warning. "This will permanently delete your account, saved addresses, and review history" — not "Are you sure?"

---

# Form & Input UX

- **Validation timing:** inline, on blur, for most fields; live (character-by-character) only where the format is unambiguous and short — OTP codes, phone numbers.
- **Keyboard matching:** numeric keypad for OTP/phone, email keyboard for email, no autocorrect on names or Emirates ID fields.
- **Progressive disclosure:** long onboarding (Provider Basic Info → Business/Freelancer Details → Verification Upload, `S-17`–`S-19`) is broken into short steps with a visible step indicator, never one long scrolling form — each step should feel completable in under 30 seconds.
- **Skippable is actually skippable:** `S-05` (first address) must not silently require the field later — if skipped, the app asks again only when an address is actually needed (submitting the first Search Request), not before.

---

# Trust & Verification UX Patterns

Trust is the product's core value proposition (`00_PROJECT_CONTEXT.md`), so these patterns are not optional polish:

- Verification status is **always visible with a label**, never an icon alone — a checkmark with no text is ambiguous; "Verified" with a checkmark is not.
- An unclaimed listing (`S-08`, `S-09`) must be **visually distinct at a glance** — not just a small badge a user could miss — since showing it as indistinguishable from a claimed, verified listing directly contradicts the Google Places open decision in `13_OPEN_DECISIONS.md` item 4.
- "Verified Visit" badges are tappable/explainable on first encounter — a one-line explanation sheet ("This customer confirmed the provider showed up in person"), not an assumption the user already knows what it means.
- Rating and review counts are shown together, never rating alone — "4.8 (3 reviews)" reads very differently from "4.8 (140 reviews)," and hiding the count would be misleading.

---

# Notification & Interruption UX

- Non-urgent events (new lead for a Provider) update the bell-icon badge; they do not interrupt with a push notification unless the user has opted in.
- Time-sensitive events (OTP codes, verification status changes) may push immediately — these are the cases the user is actively waiting on.
- Dialogs are reserved strictly for confirmation, critical information, and destructive actions, per `07_UI_GUIDELINES.md` — a "new lead" notification is a snackbar/badge event, never a modal dialog interrupting whatever the user was doing.

---

# Accessibility (Concrete Targets)

Expands `07_UI_GUIDELINES.md`'s accessibility principle into testable targets:

- Minimum touch target: 44×44px (already stated in `07_UI_GUIDELINES.md` — restated here as a hard gate, not a suggestion).
- Text contrast: WCAG AA minimum (4.5:1 for body text, 3:1 for large text) against both light and dark surface colors from the palette in `15_SCREEN_INVENTORY.md`.
- Every icon-only control (bell icon, mic icon, back arrow) has a screen-reader label — an icon is not self-describing to a screen reader.
- Layouts must survive the OS's largest standard dynamic-text setting without clipping or overlapping — test this on the AI Conversation screen specifically, since chat bubbles are the most likely to break.
- RTL reading order matches visual order for screen readers, not just visual mirroring — a common gap where visual RTL is implemented but the underlying reading order isn't.

---

# Onboarding & Friction Reduction

- Registration is mandatory (no guest path) but must feel fast: prefer native OS account pickers for Google/Apple, and OS-level OTP autofill for mobile registration wherever the platform supports it — don't make the user manually copy a code from an SMS.
- Ask for information only when it's needed, not upfront "to be safe." The first address (`S-05`) is skippable at registration and only re-requested at the moment it's actually required (submitting a Search Request) — this is a deliberate friction-reduction decision, not an oversight.
- Provider onboarding (`S-15`–`S-19`) should let a user stop and resume later without losing progress — verification is a multi-step, sometimes multi-day process; treat partial completion as a normal state, not an error.

---

# Feedback, Confirmation & Reversibility

- Every user-initiated action gets acknowledgment: button loading state while in flight, success confirmation (snackbar/toast) on completion, per `07_UI_GUIDELINES.md`'s loading-state rules.
- Reversible actions (deleting a saved address, for instance) use an "Undo" snackbar rather than a confirmation dialog — this is faster for the common case and still safe, since undo is available for a few seconds after the action.
- Irreversible actions (submitting a Review, submitting an Outcome Tag, deleting an account) require an explicit confirmation step — see the destructive-action copy rule above.

---

# UX Review Checklist

Run this against any new or changed screen before marking an implementation story done — it operationalizes the "three questions" rule already in `07_UI_GUIDELINES.md`:

- [ ] Can the user answer "where am I, what can I do, what happens next" within a few seconds of landing on this screen?
- [ ] Does every async action (>500ms) show feedback appropriate to its actual expected duration, per the latency rules above?
- [ ] Does any user-facing string leak an internal domain term from the mapping table?
- [ ] Does every error state explain what happened in plain language and give a next step?
- [ ] Does every empty state explain why it's empty and offer one primary action?
- [ ] Has this screen been checked in both LTR and RTL?
- [ ] Do all icon-only controls have accessible labels, and does text scale without breaking layout?
- [ ] Is trust-relevant information (verification status, unclaimed label, rating count) visible without requiring a tap to reveal?

---

# Related Documents

- `00_PROJECT_CONTEXT.md`
- `03_DOMAIN_MODEL.md`
- `06_SECURITY.md`
- `07_UI_GUIDELINES.md`
- `14_USER_FLOWS.md`
- `15_SCREEN_INVENTORY.md`

---

**End of Document**
