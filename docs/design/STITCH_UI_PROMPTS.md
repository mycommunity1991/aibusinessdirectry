# Stitch UI Generation Prompts — AI Marketplace

**Source documents:** `docs/AI/07_UI_GUIDELINES.md`, `docs/AI/14_USER_FLOWS.md`, `docs/AI/15_SCREEN_INVENTORY.md`, `docs/AI/16_UX_GUIDELINES.md`
**Status:** Working artifact — regenerate/update if the palette, screen inventory, or flows change
**Last Updated:** 15 July 2026

---

# How to Use This

**Load `DESIGN.md` (repo root) into your Stitch project first.** It's the canonical, portable design-token file (Google's open `DESIGN.md` format) — colors, typography, spacing, and component tokens for this product. Once it's loaded, Stitch already has the visual system as persistent context, so the repeated **Theme** line in every prompt below becomes a redundant safety net rather than the only source of truth — keep it in each prompt anyway for reproducibility outside this specific Stitch project, but `DESIGN.md` is what should govern if the two ever disagree after a palette update.

**Before pasting anything, set Stitch's App/Web toggle (beneath the prompt input box) to "App," not "Web."** This is a separate canvas-level setting from the text prompt — Qivo is a Flutter mobile app, and every screen in `15_SCREEN_INVENTORY.md` was designed for a phone, but Stitch won't infer that from prompt text alone if the toggle itself is left on "Web." Check it before every new screen, not just the first one — some Stitch flows reset the toggle per generation.

Each prompt follows Stitch's own three-line shape: **Idea** (what the screen is), **Theme** (visual style), **Content** (what must appear on it). Paste one block at a time, in order — generate the onboarding screens first so Stitch's early output anchors a consistent look before you move to the rest.

Prompts below use **Qivo** as the working product name — chosen after a first-pass collision check (see conversation history), but not yet formally cleared. Treat it as provisional until a real UAE/GCC trademark and domain search closes out `13_OPEN_DECISIONS.md` item 8; if the name changes, re-run a find-and-replace on "Qivo" across this file before generating further screens.

The **Theme** line is identical across every prompt on purpose — copy it exactly each time so Stitch produces one consistent design system across all 28 screens rather than 28 slightly different ones.

**Not covered below, by design:** dark mode and Arabic/RTL variants. Once a screen's light/English version looks right, run one short follow-up in the same Stitch thread — "Now generate the dark mode version, same layout" or "Now generate the Arabic RTL-mirrored version" — rather than folding all three into one prompt. Both are launch requirements per `16_UX_GUIDELINES.md`, just handled as a second pass.

---

# A. Onboarding & Auth

### S-01 — Splash

Idea: A splash screen for Qivo, an AI-powered local services marketplace app.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A centered logo and a small loading indicator beneath it. Nothing else on screen.

### S-02 — Language Selection

Idea: A first-run language selection screen for Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Headline "Choose your language," two large tappable options — "English" and "العربية" — and a Continue button.

### S-03 — Sign In / Sign Up

Idea: An authentication landing screen for Qivo, with no guest access.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A short tagline "Find trusted local pros, instantly," a "Continue with Google" button, a "Continue with Apple" button, a "Continue with Mobile Number" button, and a small Terms & Privacy footnote.

### S-04 — Mobile OTP Entry

Idea: A one-time-code verification screen for Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: The entered phone number at the top, six OTP input boxes, a "resend code in 00:45" timer, and a Verify button.

### S-05 — Add Your First Address

Idea: A skippable location-setup screen for Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: An address search field, a "Use current location" button, a small map preview with a pin, and a "Save & Continue" button, with a Skip link at the top.

---

# B. Customer — Core Loop

### S-06 — Home

Idea: The Home tab of Qivo, where a customer starts describing a service they need.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A greeting header with a notification bell icon, a large search input reading "What do you need help with?" with a mic icon, a row of quick-start category chips (Plumber, AC Repair, Cleaning, Electrician), and a 3-tab bottom navigation bar — Home, Activity, Profile.

### S-07 — AI Conversation

Idea: A full-screen AI chat interface for Qivo where an assistant asks follow-up questions about a customer's request.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A chat transcript with AI messages on the left and user messages on the right, quick-reply chips under one AI question, a typing indicator, and a bottom text input with mic and send icons.

### S-08 — Search Results

Idea: A ranked list of matched local service providers on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A vertical list of provider cards, each with a photo, name, category tag, star rating with review count, distance, and a green "Verified" badge on one card.

### S-09 — Provider Profile

Idea: A provider's profile screen on Qivo, viewed by a customer before contacting them.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A photo carousel, provider name and category, star rating with a "Verified" badge, service area and hours, a description paragraph, a small portfolio grid, and a sticky bottom "Contact" button.

### Contact Reveal (bottom sheet)

Idea: A bottom sheet on Qivo revealing a provider's phone number after a customer taps Contact.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: The provider's name and photo, a large phone number, a Call button, a WhatsApp button, and a small note that contact happens outside the app.

### Outcome Tag Prompt (bottom sheet)

Idea: A bottom sheet on Qivo asking a customer whether they hired a provider.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: The headline "Did you hire [Provider Name]?" with Yes and No buttons, and a small "Maybe later" link.

### S-10 — Write a Review

Idea: A review screen on Qivo, shown only after a customer confirms they hired a provider.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: The provider's name, a 5-star rating selector, a comment text field, and a "Submit Review" button.

---

# C. Customer — Activity, Profile, Settings

### S-11 — My Activity

Idea: The Activity tab of Qivo, showing a customer's past and ongoing requests.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Filter chips for "In Progress," "Contacted," and "Reviewed," and a list of activity rows each with a status chip and timestamp, plus a 3-tab bottom navigation bar.

### S-12 — Saved Addresses

Idea: An address management screen on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A list of saved address cards with a "Default" badge on one, edit and delete icons, and an "Add Address" button.

### S-13 — Notifications Inbox

Idea: A notifications screen on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Notifications grouped under "New" and "Earlier" headers, each row with an icon, title, short description, and timestamp.

### S-14 — Profile & Settings

Idea: The Profile tab of Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: An avatar and display name at the top, settings rows for Language, Notification Preferences, and Saved Addresses, a highlighted "List Your Business" card, and Log Out / Delete Account links at the bottom, plus a 3-tab bottom navigation bar.

---

# D. Provider — Onboarding & Verification

### S-15 — List Your Business (Intro)

Idea: An intro screen inviting a customer of Qivo to also list their business or service.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A storefront icon, the headline "Your free digital storefront," one line of supporting copy, and a "Get Started" button.

### S-16 — Choose Provider Type

Idea: A provider-type selection screen on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Two selectable cards, "Business" and "Freelancer," each with an icon and short description, and a Continue button.

### S-17 — Basic Info

Idea: Step 1 of provider onboarding on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A "Step 1 of 3" indicator, and form fields for business/service name, phone number, WhatsApp number, category, and description, with a Continue button.

### S-18a — Business Details

Idea: Step 2 of Business-type provider onboarding on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A "Step 2 of 3" indicator, an address map picker, a weekly operating-hours list with toggles, a delivery-radius slider, and an optional trade license field, with a Continue button.

### S-18b — Freelancer Details

Idea: Step 2 of Freelancer-type provider onboarding on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A "Step 2 of 3" indicator, a base-location map picker, a service-radius slider, removable skill tag chips, and a years-of-experience field, with a Continue button.

### S-19 — Verification Upload

Idea: Step 3 of provider onboarding on Qivo, for identity verification.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A "Step 3 of 3" indicator, a document upload area with camera and gallery buttons, and a confirmation card showing extracted fields like Name, ID Number, and Expiry Date, with a "Submit for Review" button.

### S-20 — Verification Status

Idea: A status screen on Qivo showing a provider's verification progress.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A large amber status badge, the headline "We're reviewing your documents," and one paragraph of supporting text.

### S-21 — Claim Your Listing

Idea: A search screen on Qivo letting a business owner find their existing unclaimed listing.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A search field and a list of result cards, each with a business name, address snippet, and an amber "Unclaimed" badge.

### S-22 — Claim OTP Verification

Idea: An ownership-verification screen on Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Explanatory text naming the phone number on record, six OTP input boxes, a Verify button, and a "this isn't my number" link.

---

# E. Provider — Ongoing Management

### S-23 — Provider Dashboard

Idea: The Dashboard tab for a provider using Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Summary cards for New Leads, Verification status, and Profile Views, quick links to Leads and Storefront, and a 3-tab bottom navigation bar — Dashboard, Leads, Storefront.

### S-24 — Leads

Idea: The Leads tab for a provider using Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: A list of leads, each with a category tag, timestamp, and an outcome status chip like "Hired" or "Not hired."

### S-25 — Storefront / Edit Profile

Idea: The Storefront tab for a provider using Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Editable sections for Basic Info, a Portfolio photo grid with an add-photo tile, Availability, and Business/Freelancer Details.

### S-26 — Visibility Analytics

Idea: An analytics screen for a provider using Qivo.
Theme: Native mobile app screen, iOS/Android, portrait phone aspect ratio — not a website, not a desktop or responsive web layout. Modern, clean, and trustworthy — like a fintech or logistics utility app, not a playful social app. Material Design 3, Inter typeface, soft neutral light background, electric indigo (#2F54EB) for structural chrome, teal (#14B8A6) reserved for the one primary call-to-action button, outlined icons, generous whitespace, flat surfaces with no blur or glassmorphism and minimal soft shadow, fully rounded (pill-shaped) primary button, 16px rounded cards.
Content: Stat cards for "Search Appearances" and "Contact Views," a 30-day trend chart, and a short list of top-searched categories.

---

# F. Brand Mark (Logo)

**Concept:** the mark is a location pin (the "nearby" core of the product) with its usual empty pinhole replaced by a small solid teal dot — the dot reads simultaneously as a map "ping," a connection point, and a full stop of certainty (trust). No literal robot/AI iconography — per `16_UX_GUIDELINES.md`, the AI should feel like a competent assistant, not a novelty chatbot, and that restraint should show up in the brand mark too, not just the UI. Flat, single-weight geometry, no gradients or bevels, consistent with `DESIGN.md`'s "flat surfaces, no glassmorphism" rule.

**Wordmark:** "qivo" set in Inter (the same typeface as the product UI, not a separate display font), medium weight, lowercase, tight tracking, in electric indigo (#2F54EB) — except the dot of the "i," which is replaced with the same solid teal (#14B8A6) used in the pin mark, tying the wordmark and the icon together with one shared accent instead of two unrelated details.

**Lockups needed:** (1) icon-only mark for the app store / launcher icon — pin + dot centered on a plain white or very light indigo-tinted rounded-square background, no wordmark; (2) horizontal lockup — pin mark to the left, wordmark to the right, for splash screens and in-app headers.

Idea: An app icon and horizontal logo lockup for Qivo, a trustworthy AI-mediated local services marketplace.
Theme: Minimal, geometric, flat — no gradients, no drop shadow, no glassmorphism, no literal robot/AI/chatbot imagery. Electric indigo (#2F54EB) as the dominant color, a single teal (#14B8A6) accent color used only for the pin's center dot and the dot of the "i," Inter typeface for the wordmark, generous negative space.
Content: A location-pin silhouette in electric indigo with a small solid teal dot at its center instead of the usual empty pinhole. One version as an icon-only app-store mark on a plain rounded-square background. One version as a horizontal lockup: the pin mark on the left, and the lowercase wordmark "qivo" in Inter on the right, where the dot of the "i" is the same teal as the pin's center dot.

**Note on tool fit:** Stitch is built for app/web screens, not vector logo files — its output here is a useful visual direction to react to, not a production-ready icon. Once you like a direction, take it to a dedicated icon/vector tool (or a general image model) to produce the final scalable mark, and get it re-drawn as clean vector rather than shipping a raster export.

---

# Related Documents

- `DESIGN.md` (repo root) — portable design-token file, load this into Stitch directly
- `docs/AI/07_UI_GUIDELINES.md` — design system these prompts are derived from
- `docs/AI/14_USER_FLOWS.md` — journeys each screen belongs to
- `docs/AI/15_SCREEN_INVENTORY.md` — screen list, IA, and palette source of truth
- `docs/AI/16_UX_GUIDELINES.md` — interaction/content rules to check generated screens against after Stitch output

---

**End of Document**
