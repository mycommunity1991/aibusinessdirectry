# AI Marketplace — Screen Inventory & Visual Identity

**Document ID:** AI-15
**Version:** 1.0.0
**Status:** Draft — pending product/design review
**Owner:** CTO & Product Owner
**Audience:** UI/UX Designers, Flutter Developers, AI Assistants
**Last Updated:** 15 July 2026

---

# Purpose

`07_UI_GUIDELINES.md` defines the design *system* (tokens, components, principles) but deliberately leaves two things as placeholders: an actual color palette ("maintained in the Design Tokens document") and any concrete screen list. `14_USER_FLOWS.md` defines the journeys but not the screen-by-screen UI. This document closes both gaps: a real, modern visual identity, and the full buildable screen inventory — one Flutter feature/screen per row below, cross-referenced to the flow step that produces it.

Nothing here introduces a feature outside `11_MVP_SCOPE.md`. Every screen exists because a step in `14_USER_FLOWS.md` requires it — if a screen doesn't trace back to a flow step, it doesn't belong in v1.

---

# Design Intent

The product is a **utility, not a feed** (`00_PROJECT_CONTEXT.md`): search → AI-mediated match → direct contact. The UI should feel like a fast, trustworthy tool — closer to a modern fintech or logistics app than a social/marketplace-with-feed app. Concretely, that means:

- No infinite scroll of content for its own sake — every list (matches, leads, activity) has a clear end and a purpose.
- No decorative illustration-heavy empty states or onboarding carousels — get the user to the first real action (sign in → describe the need) in as few taps as possible.
- One primary action per screen, always, per `07_UI_GUIDELINES.md`'s existing "App Bar → Content → Primary Action → Bottom Navigation" structure.
- The AI conversation should feel like a competent assistant, not a novelty chatbot — calm typography, no cartoon avatars, no excessive animation.

---

# Visual Identity (Concrete Palette)

`07_UI_GUIDELINES.md`'s Color System section names roles (Primary, Secondary, Success, Warning, Error, Info) but not values. These are the seed values — feed them into Material 3's `ColorScheme.fromSeed()` rather than hardcoding them per-widget, so light/dark and any future dynamic-color support stay automatic. The same values are also encoded as a portable token set in `DESIGN.md` at the repo root (Google's open `DESIGN.md` format), for design tools (Stitch) and any AI coding agent that reads repo-root context files — that file is generated from this section and should be regenerated if this palette changes, not edited independently.

| Role | Seed Value | Rationale |
|---|---|---|
| Primary | `#2F54EB` (electric indigo) | Reads as trustworthy and technology-forward without tipping into cold/corporate blue. Differentiates from the reds/oranges typical of legacy category-directory apps (JustDial-style) — a deliberate visual signal that this isn't that kind of product. |
| Secondary / CTA accent | `#14B8A6` (teal) | Reserved for the highest-emphasis action per screen — "Contact," "Send," "Submit" — so it stands out against Primary chrome (app bar, nav) instead of competing with it. |
| Success | `#22C55E` | Approved verification, positive outcome tag. |
| Warning | `#F59E0B` | Pending verification, unclaimed-listing label. |
| Error | `#EF4444` | Rejected verification, failed OTP. |
| Info | `#3B82F6` | Distinct from Primary indigo — used only for informational banners, never for actions, so it can't be mistaken for a tappable CTA. |
| Surface / Background | Material 3 neutral, derived from seed | Standard light/dark neutral ramps — do not hand-pick grays outside what `ColorScheme.fromSeed()` generates. |

**Typography:** Material 3 type scale (already specified in `07_UI_GUIDELINES.md`) stays, but pick the actual typeface pair now rather than leaving it to whatever Flutter defaults to: **Inter** (or Manrope) for Latin script, paired with **IBM Plex Sans Arabic** for Arabic — matched x-height and weight so the UI doesn't visibly shift "personality" when a user switches languages. This matters more than usual here since bilingual EN/AR is a locked launch requirement, not a stretch goal.

**Iconography & imagery:** Material Symbols in **outlined** style (not filled) — reads lighter and more "utility," consistent with "avoid flashy or overly decorative designs." Provider portfolios use real photography only; empty states use simple single-color line art, not multi-color mascot illustrations.

---

# Information Architecture

One Account, two possible modes — **Customer mode** (every account has this) and **Provider mode** (only if the account has added a Provider role, per `14_USER_FLOWS.md` Flow 5). This is the single most important IA decision for "the user always knows where they are": the mode switch must be an explicit, always-visible affordance, never buried.

**Customer mode — bottom navigation, 3 tabs (not 4–5):**
1. **Home** — the AI search entry point
2. **Activity** — everything the user has already done (in-progress requests, contact history, reviews)
3. **Profile** — settings, addresses, language, and the entry point to Provider mode

A bell icon in the top app bar (present on all three tabs, with an unread badge) opens **Notifications** — kept out of the tab bar because it's a cross-cutting inbox, not a primary destination, and 3 clearly-labeled tabs are easier to scan at a glance than 4.

**Provider mode — bottom navigation, 3 tabs:**
1. **Dashboard** — leads summary, verification status, quick links
2. **Leads** — the actionable list (who viewed your contact info)
3. **Storefront** — edit profile, portfolio, availability, verification

Same bell icon, same Notifications screen (filtered to Provider-relevant items when in this mode). A visible "Switch to Customer" control lives in the Storefront tab's top-level menu — one tap, no submenu diving.

**Tab labels are always shown as text + icon, never icon-only** — this is the cheapest, most reliable way to satisfy "user should know where to look for what" and costs nothing in a 3-tab bar.

---

# Screen Inventory

26 full screens + 2 bottom-sheet "moments" (deliberately not full screens, per `07_UI_GUIDELINES.md`'s preference for sheets over screens for contextual actions) = **28 total UI surfaces** for MVP. Each row traces to a `14_USER_FLOWS.md` step.

## A. Onboarding & Auth — Flow 1

| # | Screen | Purpose | Key Elements | Primary Action |
|---|---|---|---|---|
| S-01 | Splash | Brand moment + session check | Logo, loading indicator | none (auto-routes) |
| S-02 | Language Selection | Set EN/AR before anything else renders | Two large language options | Continue |
| S-03 | Sign In / Sign Up | Entry point, no guest path | Google button, Apple button, "Continue with Mobile Number," ToS/Privacy footnote | Choose method |
| S-04 | Mobile OTP Entry | Verify phone | Phone input → code input, resend timer | Verify |
| S-05 | Add Your First Address (skippable) | Seed a saved address | Map pin / manual entry, "Use current location," Skip link | Save & Continue |

## B. Customer — Core Loop — Flow 4

| # | Screen / Surface | Purpose | Key Elements | Primary Action |
|---|---|---|---|---|
| S-06 | Home | Entry to AI intake | Prominent "What do you need help with?" input + mic icon, optional quick-start category chips beneath, bell icon | Start conversation |
| S-07 | AI Conversation | Conversational intake | Chat transcript, typing indicator, quick-reply chips for structured questions, free-text input | Answer / send |
| S-08 | Search Results | Ranked matches | Provider cards (photo, name, category, rating + count, distance, Verified badge), empty state explaining Wizard-of-Oz fallback if unmatched | Open a Provider |
| S-09 | Provider Profile | Customer-facing provider view | Photo/portfolio carousel, name, category, rating, distance, hours/availability, description, Verified Visit badge if present, sticky bottom CTA | Contact |
| *(sheet)* | Contact Reveal | Show phone directly, no gating | Large phone number, Call button, WhatsApp button, "contact happens outside the app" note | Call / WhatsApp |
| *(sheet)* | Outcome Tag Prompt | Capture "Did you hire them?" | Provider name/photo, Yes/No | Yes / No |
| S-10 | Write a Review | Anchor-verified review, only after "Yes" | Star rating input, comment field | Submit |

## C. Customer — Activity, Profile, Settings

| # | Screen | Purpose | Key Elements | Primary Action |
|---|---|---|---|---|
| S-11 | My Activity | Single place for "what have I done" | Filter chips: In Progress / Contacted / Reviewed; each row deep-links to its context | Tap a row |
| S-12 | Saved Addresses | Manage locations | List with default badge, add/edit/delete | Add Address |
| S-13 | Notifications Inbox | Cross-cutting alert list | Chronological, unread/read grouping, tap-through to context | Tap a notification |
| S-14 | Profile & Settings | Account control center | Avatar/name, language toggle, notification preferences, Saved Addresses link, **"List Your Business"** CTA, legal links, delete account, log out | (context-dependent) |

## D. Provider — Onboarding & Verification — Flow 2, Flow 3

| # | Screen | Purpose | Key Elements | Primary Action |
|---|---|---|---|---|
| S-15 | List Your Business (Intro) | Value prop, single CTA | "Your free digital storefront" | Get Started |
| S-16 | Choose Provider Type | Business vs Freelancer, immutable after this | Two cards with short descriptions | Select one |
| S-17 | Basic Info | Shared profile fields | Display name, phone/WhatsApp, category picker, description | Continue |
| S-18a | Business Details *(if Business)* | Fixed-location fields | Address/map pin, operating hours editor, delivery radius slider, optional trade license number | Continue |
| S-18b | Freelancer Details *(if Freelancer)* | Mobile-provider fields | Base location/map pin, service radius slider, skills tags, years of experience | Continue |
| S-19 | Verification Upload | Document + OCR confirm | Document-type-specific uploader, camera/file picker, "we read this from your document — confirm" step | Submit |
| S-20 | Verification Status | Trust-gate visibility | Status badge (Pending/Under Review/Approved/Rejected), plain-language explanation, resubmit CTA if rejected | Resubmit (if rejected) |
| S-21 | Claim Your Listing (Search) | Find the unclaimed entry | Search by business name/location | Select listing |
| S-22 | Claim OTP Verification | Prove ownership | Code sent to public number on record, "this isn't working" fallback link | Verify |

## E. Provider — Ongoing Management

| # | Screen | Purpose | Key Elements | Primary Action |
|---|---|---|---|---|
| S-23 | Provider Dashboard | Provider-mode home | Summary cards: new leads, verification status chip, visibility snapshot, quick links | Tap a card |
| S-24 | Leads (Contact Views) | The actionable list | Timestamp, request context, outcome status if available | Tap a lead |
| S-25 | Storefront / Edit Profile | Ongoing profile management | Edit basic/business/freelancer details, portfolio manager (add/remove/reorder photos), availability editor | Save |
| S-26 | Visibility Analytics | Reused Search Event Log data | Simple stat cards: search appearances, contact views over time | (view-only) |

---

# Bilingual & RTL Considerations

- Every screen above must be validated in both LTR (English) and RTL (Arabic) layouts before being marked done — this is not a post-launch pass, per `00_PROJECT_CONTEXT.md`.
- Chat bubbles (S-07), map pins with radius sliders (S-18a/b), and rating stars (S-10) are the highest-risk components for RTL mirroring bugs — flag them explicitly in any implementation story that touches them.
- The bottom-nav tab order should visually mirror (not just text-align) in RTL, matching platform convention.

---

# Explicitly Out of Scope for This Inventory

- **Admin dashboard** (manual verification review, Wizard-of-Oz manual match, unmatched-query analytics — `14_USER_FLOWS.md` Flows 6–7) is **not** included here. `02_ARCHITECTURE.md` frames the Flutter app as the consumer-facing product and the website as a separate repository; nothing in the docs assigns the Admin dashboard to the mobile app. Recommend treating it as a separate internal web tool rather than adding 4–5 more screens to the consumer app — but this should be a confirmed decision, not an assumption baked in silently. Worth adding to `13_OPEN_DECISIONS.md` if not already settled.
- No Favorites/Saved Providers, no in-app messaging, no browsable category-tree homepage — all deliberately excluded per `11_MVP_SCOPE.md` and the "utility, not category-tree directory" positioning in `00_PROJECT_CONTEXT.md`.

---

# Related Documents

- `00_PROJECT_CONTEXT.md`
- `03_DOMAIN_MODEL.md`
- `07_UI_GUIDELINES.md`
- `11_MVP_SCOPE.md`
- `14_USER_FLOWS.md`
- `16_UX_GUIDELINES.md`

---

**End of Document**
