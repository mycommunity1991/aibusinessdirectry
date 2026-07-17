---
name: AI Marketplace
version: alpha
description: >
  Design system for AI Marketplace (working title, pending 13_OPEN_DECISIONS.md
  item 8) — a location-based directory and AI-mediated conversational-intake
  marketplace connecting businesses and freelancers with nearby customers.
  Flutter + Material Design 3, mobile-first, bilingual English/Arabic (RTL).
  Values below are an approximation of the canonical scheme; the Flutter
  implementation of record is ColorScheme.fromSeed(seedColor: 0xFF2F54EB)
  per docs/AI/07_UI_GUIDELINES.md.
colors:
  primary: "#2F54EB"
  on-primary: "#FFFFFF"
  primary-container: "#DEE1FF"
  on-primary-container: "#00105C"
  inverse-primary: "#B7C3FF"
  secondary: "#14B8A6"
  on-secondary: "#FFFFFF"
  secondary-container: "#B7F0E8"
  on-secondary-container: "#00201C"
  tertiary: "#3B82F6"
  on-tertiary: "#FFFFFF"
  tertiary-container: "#D7E3FF"
  on-tertiary-container: "#001B3D"
  error: "#EF4444"
  on-error: "#FFFFFF"
  error-container: "#FFDAD6"
  on-error-container: "#410002"
  success: "#22C55E"
  on-success: "#FFFFFF"
  success-container: "#C3F4D3"
  on-success-container: "#002109"
  warning: "#F59E0B"
  on-warning: "#3F2E00"
  warning-container: "#FFDEA6"
  on-warning-container: "#2A1C00"
  background: "#FBF8FF"
  on-background: "#1B1B21"
  surface: "#FBF8FF"
  surface-dim: "#DBD9E0"
  surface-bright: "#FBF8FF"
  surface-container-lowest: "#FFFFFF"
  surface-container-low: "#F5F2FA"
  surface-container: "#EFECF4"
  surface-container-high: "#E9E7EF"
  surface-container-highest: "#E3E1E9"
  surface-variant: "#E1E0EB"
  on-surface: "#1B1B21"
  on-surface-variant: "#46464F"
  surface-tint: "#2F54EB"
  outline: "#767680"
  outline-variant: "#C6C5D0"
  inverse-surface: "#303036"
  inverse-on-surface: "#F2EFF7"
  primary-fixed: "#DEE1FF"
  primary-fixed-dim: "#B7C3FF"
  on-primary-fixed: "#00105C"
  on-primary-fixed-variant: "#17399E"
  secondary-fixed: "#B7F0E8"
  secondary-fixed-dim: "#4FD9C7"
  on-secondary-fixed: "#00201C"
  on-secondary-fixed-variant: "#00504A"
  tertiary-fixed: "#D7E3FF"
  tertiary-fixed-dim: "#A9C6FF"
  on-tertiary-fixed: "#001B3D"
  on-tertiary-fixed-variant: "#1D4E8F"
typography:
  display-sm:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: "600"
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: "600"
    lineHeight: 36px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: "600"
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: "600"
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: "600"
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "600"
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: "600"
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 8px
  DEFAULT: 12px
  lg: 16px
  xl: 24px
  full: 9999px
spacing:
  unit: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 40px
  3xl: 48px
  4xl: 64px
components:
  button-primary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-secondary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.full}"
    height: 48px
    padding: 0 24px
  button-outlined:
    backgroundColor: transparent
    textColor: "{colors.primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.full}"
    height: 48px
  card-standard:
    backgroundColor: "{colors.surface-container-low}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  input-field:
    backgroundColor: "{colors.surface-container-high}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
    rounded: "{rounded.DEFAULT}"
    height: 48px
    padding: "{spacing.md}"
  bottom-sheet:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    padding: "{spacing.lg}"
  chat-bubble-ai:
    backgroundColor: "{colors.surface-container}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
  chat-bubble-user:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
  badge-verified:
    backgroundColor: "{colors.success-container}"
    textColor: "{colors.on-success-container}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
  badge-unclaimed:
    backgroundColor: "{colors.warning-container}"
    textColor: "{colors.on-warning-container}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
---

## Overview

AI Marketplace is a utility, not a feed: search → AI-mediated match → direct contact, for customers finding local businesses and freelancers. The brand personality is **trustworthy, fast, and calm** — closer to a modern fintech or logistics tool than a social or marketplace-with-feed app. Every design decision should answer "does this make the user trust the platform and get to their next action faster," not "does this look impressive." Nothing here should read as playful, decorative, or attention-seeking — see Do's and Don'ts.

The product is mobile-first (Flutter, Material Design 3) and bilingual English/Arabic with full RTL support at launch, not as a later pass.

## Colors

The palette centers on **electric indigo** (`primary`) for structural chrome — app bars, active navigation state, headers — because it reads as technology-forward without the coldness of a pure corporate blue, and deliberately avoids the reds/oranges of legacy category-directory apps this product is not trying to resemble.

**Teal (`secondary`) is reserved for exactly one thing:** the single highest-emphasis call-to-action on any given screen — "Contact," "Get Started," "Submit." If a screen has more than one teal element, that's a signal something else should be demoted to `button-outlined`.

`tertiary` (blue) is informational only — banners, non-actionable status text — and must never be used for a tappable element, so it can never be mistaken for a link or button.

Two roles exist beyond the standard Material triad because this product's trust mechanics need them natively, not as an afterthought: `success` (verification approved, positive review) and `warning` (verification pending, unclaimed listing). Both ship with their own `-container`/`on-*` pairs so badges never rely on color alone — see Components.

Surface tokens follow standard Material 3 tonal elevation — very light, low-saturation neutrals in light theme. Dark theme is a separate, later token set (not included here) generated from the same seed; do not hand-pick dark values independently of it.

## Typography

**Inter** across the full scale. For Arabic, render every scale step (`display-sm` through `label-sm`) at identical `fontSize`/`lineHeight` values using **IBM Plex Sans Arabic** — matched x-height and weight so the UI's "personality" doesn't visibly shift when a user switches languages. This is a hard requirement, not a fallback-font accommodation, since bilingual UI is a locked launch scope item.

Scale is intentionally shallow — nine steps, not Material's full default set — because this app rarely needs true display-scale text (no marketing hero screens); `display-sm` is the largest size used, for verification-status headlines and similar single-moment emphasis.

## Layout & Spacing

8px base grid throughout (`spacing.unit`). One primary action per screen, always placed at the bottom in a sticky bar or as the final element in scroll order — never buried mid-screen or duplicated.

Navigation is two mode-scoped 3-tab bottom bars (Customer: Home/Activity/Profile; Provider: Dashboard/Leads/Storefront) with text+icon labels, never icon-only. A persistent bell icon in the app bar — not a fourth tab — opens Notifications. Screens with a `card-standard` list (search results, leads, activity) use `spacing.md` between cards and `spacing.lg` for section margins.

## Elevation & Depth

Deliberately restrained — this is the opposite of a glassmorphic or heavily-blurred aesthetic. Surfaces are distinguished by the `surface-container-*` tonal steps (flat color, no blur, no transparency layering), not by shadow depth or frosted-glass effects. Where a shadow is used at all (floating action elements, the sticky bottom action bar), keep it soft and minimal — a shadow should separate a surface from the one behind it, never add visual weight or drama.

## Shapes

Buttons use `rounded.full` (pill/stadium shape) — the one place a strong rounded shape signals "tap me" clearly. Cards use `rounded.lg` (16px), standard inputs and smaller elements use `rounded.DEFAULT` (12px), and bottom sheets use `rounded.xl` (24px) on their top corners only. Icons are outlined Material Symbols, not filled — a lighter, more "utility" feel than solid icon fills.

## Components

- **`button-primary`** — the one-per-screen teal CTA, pill-shaped, `label-lg` typography.
- **`button-outlined`** — every other action on a screen with a `button-primary` present; transparent fill, indigo text/border.
- **`card-standard`** — the base container for list items (provider cards, activity rows, lead rows).
- **`input-field`** — form inputs; note the OTP input variant is six individual square boxes, not a single `input-field`.
- **`chat-bubble-ai`** / **`chat-bubble-user`** — the AI Conversation screen only; AI left-aligned in a neutral tone, user right-aligned in the primary-tinted tone. Never introduce a third bubble style for this screen.
- **`bottom-sheet`** — used for Contact Reveal and the Outcome Tag prompt specifically, per `docs/AI/07_UI_GUIDELINES.md`'s preference for sheets over full screens or dialogs for contextual actions.
- **`badge-verified`** / **`badge-unclaimed`** — always paired with a text label ("Verified" / "Unclaimed"), never an icon alone; an unclaimed listing must be visually distinct at a glance, not a small badge easily missed.

## Do's and Don'ts

**Do:**
- Keep exactly one `button-primary` visible per screen.
- Pair every status badge (verified, unclaimed, verification pending/approved/rejected) with a text label, not just a color or icon.
- Use real photography for provider portfolios; use simple single-color line art for empty states.
- Validate every screen in both LTR/English and RTL/Arabic before calling it done.
- Show rating and review count together ("4.8 (56)"), never rating alone.

**Don't:**
- Don't use glassmorphism, heavy blur, or drop shadows beyond subtle separation — this system is flat and calm, not the "atmospheric glass" aesthetic some design tools default to.
- Don't use `tertiary` (info blue) on anything tappable.
- Don't surface internal domain terms as UI copy — no "Contact View," "Outcome Tag," or raw confidence scores in user-facing text; see `docs/AI/16_UX_GUIDELINES.md` for the full internal-term → user-facing-copy mapping.
- Don't add a fourth or fifth bottom-nav tab — Notifications lives behind the bell icon, not a tab, by deliberate choice.
- Don't invent new badge colors outside `success`/`warning`/`error` — a fourth ad hoc status color undermines the "user always knows what a color means" rule.

---

Related: `docs/AI/07_UI_GUIDELINES.md`, `docs/AI/15_SCREEN_INVENTORY.md`, `docs/AI/16_UX_GUIDELINES.md`, `docs/design/STITCH_UI_PROMPTS.md`
