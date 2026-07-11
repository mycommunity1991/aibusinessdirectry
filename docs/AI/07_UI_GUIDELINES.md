# MyCommunity UI/UX Guidelines

**Document ID:** AI-07  
**Version:** 1.0.0  
**Status:** Active  
**Owner:** CTO & Product Owner  
**Audience:** UI/UX Designers, Flutter Developers, AI Assistants  
**Last Updated:** 2026-07-03

---

# Purpose

This document defines the design system, UI principles, interaction patterns, accessibility standards, and implementation guidelines for the MyCommunity mobile application.

Every screen, component, and interaction must follow these standards to ensure consistency across the application.

---

# Design Philosophy

MyCommunity is built around one fundamental principle:

**Trust through simplicity.**

Users should feel:

- Safe
- Familiar
- Comfortable
- Confident
- Fast

The interface should never feel crowded, distracting, or overwhelming.

---

# Design Principles

## Mobile First

The mobile application is the primary product.

Every feature should be designed for mobile before considering tablets or desktop.

---

## Simplicity

Interfaces should present only the information users need.

Remove unnecessary options.

Reduce cognitive load.

---

## Consistency

Identical actions should always look and behave the same throughout the application.

---

## Clarity

Users should immediately understand:

- Where they are
- What they can do
- What happens next

---

## Accessibility

The application should be usable by everyone regardless of ability.

Accessibility is a requirement, not an enhancement.

---

## Performance

Animations, transitions, and UI effects should enhance usability without reducing responsiveness.

---

# Design Language

Design System

Material Design 3

Platform

Flutter

Navigation

Bottom Navigation

App Bars

Material 3

Icons

Material Symbols

Typography

Material Typography

---

# Visual Identity

The application's visual identity should communicate:

- Trust
- Community
- Modern technology
- Simplicity
- Professionalism

Avoid flashy or overly decorative designs.

---

# Color System

Primary

Brand Primary

Secondary

Brand Secondary

Success

Green

Warning

Amber

Error

Red

Information

Blue

Surface

Material Surface

Background

Material Background

The exact color palette is maintained in the Design Tokens document.

Colors should never be hardcoded.

---

# Typography

Use Material 3 typography.

Hierarchy

- Display
- Headline
- Title
- Body
- Label

Text should remain readable on all supported devices.

Avoid excessive font sizes.

---

# Spacing

Use an 8-point spacing system.

Examples

```
4

8

16

24

32

40

48

64
```

Avoid arbitrary spacing values.

---

# Border Radius

Standard

```
12
```

Small

```
8
```

Large Cards

```
16
```

Bottom Sheets

```
24
```

Maintain consistency throughout the application.

---

# Elevation

Use subtle elevation.

Avoid excessive shadows.

Prefer clean surfaces over heavy visual effects.

---

# Icons

Use Material Symbols.

Icons should always communicate meaning.

Avoid decorative icons without functional value.

---

# Images

Images should:

- Load progressively
- Support caching
- Maintain aspect ratio
- Be optimized for mobile

Placeholder images should appear while loading.

---

# Navigation

Primary navigation

Bottom Navigation Bar

Secondary navigation

App Bar

Contextual navigation

Bottom Sheets

Dialogs

Navigation Drawer (future)

Avoid deep navigation hierarchies.

---

# Screen Structure

Every screen follows:

```
App Bar

↓

Content

↓

Primary Action

↓

Bottom Navigation
```

Maintain consistent layouts across all features.

---

# Component Standards

Reusable components should be created for:

- Buttons
- Text Fields
- Cards
- Dialogs
- Bottom Sheets
- Loading Indicators
- Error States
- Empty States
- Avatars
- Badges
- Chips
- Lists

Duplicate UI components are prohibited.

---

# Buttons

Primary

Main action

Secondary

Alternative action

Text Button

Low emphasis

Icon Button

Utility action

Danger Button

Destructive action

Button behavior must remain consistent.

---

# Forms

Forms should include:

- Labels
- Helper text
- Validation messages
- Disabled state
- Loading state

Validation should occur:

- During input
- Before submission

Error messages should explain how to fix the problem.

---

# Lists

Lists should support:

- Infinite scrolling
- Pull to refresh
- Empty state
- Error state
- Loading state

Avoid pagination buttons.

---

# Cards

Cards are the primary content container.

Cards should contain:

- Clear hierarchy
- Limited actions
- Appropriate spacing
- Consistent elevation

---

# Dialogs

Dialogs are used only for:

- Confirmation
- Critical information
- Destructive actions

Avoid stacking dialogs.

---

# Bottom Sheets

Bottom Sheets are preferred over dialogs for:

- Selection
- Contextual actions
- Additional information

---

# Loading States

Every asynchronous operation must provide feedback.

Use:

- Skeleton loaders
- Progress indicators
- Button loading states

Never freeze the interface.

---

# Empty States

Every empty screen should explain:

- Why it is empty
- What users can do next

Include a clear primary action.

---

# Error States

Error screens should include:

- Friendly explanation
- Retry action
- Support action (when appropriate)

Never expose technical errors to users.

---

# Notifications

Use:

- Snackbars
- Banners
- Push Notifications

Avoid intrusive popups.

---

# Search

Search should include:

- Instant feedback
- Recent searches
- Empty results
- Filters

Search should feel fast.

---

# Accessibility

Support:

- Screen readers
- Dynamic text sizing
- High contrast
- Touch targets ≥ 44px
- Keyboard navigation where applicable

Accessibility should be tested throughout development.

---

# Animation

Animations should be:

- Fast
- Purposeful
- Smooth

Use Material Motion guidelines.

Avoid unnecessary animations.

---

# Performance

The UI should:

- Maintain 60 FPS
- Minimize rebuilds
- Lazy load content
- Cache images
- Avoid unnecessary rendering

---

# Localization

The application supports:

- English
- Arabic

Layouts must support RTL.

All text must use localization resources.

Hardcoded strings are prohibited.

---

# Responsive Design

Primary target

Phones

Secondary

Tablets

Future

Desktop

Layouts should adapt gracefully to different screen sizes.

---

# Theme

Support:

- Light Theme
- Dark Theme

All components must automatically adapt.

Hardcoded colors are prohibited.

---

# Flutter Implementation

UI should be organized using Feature-First architecture.

Shared UI components belong in:

```
core/ui

shared/widgets
```

Feature-specific widgets remain inside their respective feature modules.

---

# Design Tokens

The following values should be centralized:

- Colors
- Typography
- Radius
- Spacing
- Shadows
- Icons
- Animation durations

No design values should be duplicated throughout the application.

---

# UI Principles

Every screen should answer three questions immediately:

1. Where am I?
2. What can I do?
3. What should I do next?

If users cannot answer these questions within a few seconds, the interface should be simplified.

---

# AI Development Rules

AI-generated UI must:

- Reuse existing widgets
- Follow Material 3
- Use design tokens
- Support localization
- Support dark mode
- Be responsive
- Follow accessibility guidelines
- Avoid duplicated components

AI must never introduce inconsistent UI patterns.

---

# Related Documents

- 00_PROJECT_CONTEXT.md
- 01_ENGINEERING_PLAYBOOK.md
- 02_ARCHITECTURE.md
- 03_DOMAIN_MODEL.md
- 04_DATABASE.md
- 05_API_GUIDELINES.md
- 06_SECURITY.md
- 08_CODING_STANDARDS.md
- 09_DECISIONS.md
- 10_GLOSSARY.md

---

**End of Document**