# Implementation Prompt — Story PRO-002 — Manage My Provider Storefront

**Sprint:** 04 (Provider Storefront) | **Epic:** ML4-EP01 | **Priority:** High | **Depends On:** PRO-001 (done)

---

## Story (verbatim from `docs/AI/Project_Tracker.xlsx`, Stories sheet)

As a provider, I want to upload portfolio photos, set my weekly availability, and edit my listing after
onboarding, so that my storefront stays current and represents my work well.

This story completes the provider aggregate (portfolios, provider_availability, provider_categories,
service_areas) and delivers the ongoing Storefront screen, distinct from the one-time onboarding flow in
PRO-001. It frames the provider profile as the provider's free digital storefront, per the product's
positioning.

Scope boundary: does not include visibility analytics (LEAD-002) or leads (LEAD-001) — this story is limited to
editing the storefront's own content.

## Acceptance Criteria

1. `portfolios`, `provider_availability`, `provider_categories`, and `service_areas` tables exist via migration.
2. Provider can add, remove, and reorder portfolio photos; each upload is validated for MIME type, extension,
   and size, and stored under a generated (never user-supplied) filename.
3. Provider can set open/closed status and hours per weekday, plus a separate emergency/urgent-availability
   flag.
4. Provider can belong to one or more categories via `provider_categories`, with exactly one marked primary.
5. Storefront screen shows editable sections for basic info, subtype-specific details, portfolio, and
   availability, each independently saveable.
6. Edits to basic info, hours, or portfolio do not require re-submitting verification unless the change affects
   a verified field — that boundary is explicitly documented in this story's implementation notes.
7. A provider cannot edit another provider's storefront (ownership enforced).
8. Automated tests cover portfolio reordering persistence, availability CRUD, and the ownership boundary.

---

## Task Given to `tech-lead`

Read `app/.agents/agents.md` and the relevant `docs/AI/` documents (architecture, domain model, database,
API guidelines, security — especially file-upload security guidance, UI/UX guidelines, coding standards, open
decisions, user flows, screen inventory, existing ADRs). Read `Plan_S04_PRO-001.md` and
`Walkthrough_S04_PRO-001.md` in full — the immediately preceding story in the same module, establishing
conventions this story extends rather than reinvents. Explore the current codebase
(`backend/app/modules/provider/`, `mobile/lib/features/provider/`) as it exists after PRO-001, not as PRO-001's
Plan intended it. Check for any existing file-upload handling to reuse (none exists — this is the first story to
need one).

Two gaps must be reasoned through explicitly as Plan Decisions, not silently improvised:

1. **The `provider_categories`/Category-domain gap.** AC4 asks for a real `provider_categories` join table
   "with exactly one marked primary," but the Category domain (`category.categories`) does not exist yet
   (PRO-001 already worked around an equivalent gap with a temporary `providers.category_label` free-text
   column). Decide and document how AC4 is satisfiable without a real `categories` table — whether
   `provider_categories` ends up referencing something other than a real Category entity for now, whether AC4 is
   satisfied differently, or whether it needs to be flagged as blocked/descoped with clear rationale. Do not
   silently build a fake Category table to unblock this.
2. **File upload/storage design.** No file-upload capability exists anywhere in this codebase today. Decide and
   document: validation rules (MIME type, extension, size — per `06_SECURITY.md`), the generated-filename
   scheme (never user-supplied), and where files are actually stored in this environment (AWS is the approved
   cloud provider per `12_TECH_STACK.md`, but no S3/AWS credentials exist anywhere in this codebase or dev
   environment — local filesystem storage under a git-ignored directory is likely the only realistic option
   absent real AWS credentials; state this explicitly as a flagged decision, not a silent choice).

Also work out and document:
- How "ownership enforced" (AC7) applies now that the storefront has sub-resources (individual portfolio items,
  availability rows) needing their own addressing (e.g. deleting one specific photo, reordering photos) — confirm
  whether the existing bare-ownership `/me` pattern from PRO-001 (ADR-015) still applies cleanly, or whether some
  sub-resources need genuine `{id}`-addressable, `ensure_owner_or_not_found`-protected routes.
- AC6's verified-field boundary: since VER-001 (Verification) hasn't shipped, be explicit about what's realistic
  to enforce now (likely nothing) versus what must be deferred/documented as a placeholder rule for a future
  story.
- The portfolio-photo reordering mechanism (explicit `sort_order` column vs. a reorder endpoint accepting an
  ordered list of ids).

Produce `docs/implementation/prompts/Prompt_S04_PRO-002.md` (this file) and
`docs/implementation/plans/Plan_S04_PRO-002.md`, following the exact structure of `Plan_S04_PRO-001.md`. Do not
implement any code. Decide which specialist agents are needed and in what order.

---

## Resulting Plan Summary (see `Plan_S04_PRO-002.md` for full detail and rationale)

- **Category gap (Decision 1):** a new, distinctly-named interim table, `provider.provider_category_labels`
  (`provider_id`, `label`, `is_primary`), extends PRO-001's `category_label` stand-in to support multiplicity +
  exactly-one-primary without referencing a real `categories` table. Explicitly not named `provider_categories`
  to avoid conflation with the real join table `04_DATABASE.md` already reserves that name for.
- **File storage (Decision 2):** a new `FileStorage` protocol (`backend/app/shared/storage/`) with one concrete
  implementation, `LocalFileStorage`, writing to a git-ignored `uploads/` directory, served via a `/media`
  `StaticFiles` mount — explicitly interim, abstracted so a future `S3FileStorage` needs no changes to
  `PortfolioService`. Validation via size check, extension allow-list, and a dependency-free magic-byte MIME
  sniff (no new imaging library). Filenames always server-generated (`uuid4().hex` + validated extension).
- **Sub-resource endpoint shapes (Decision 3/4):** `/providers/me/portfolio` (list/create),
  `/providers/me/portfolio/{portfolio_id}` (delete — genuinely `{id}`-addressable, `ensure_owner_or_not_found`
  required here per ADR-015), `/providers/me/portfolio/order` (bulk reorder via an ordered-id-list body),
  `/providers/me/availability` (bulk `GET`/`PUT` upsert of all seven weekdays) — everything anchored under the
  existing `/me` singleton, no `{provider_id}` anywhere in this domain.
- **AC6 boundary (Decision 6):** no field is gated today (VER-001 doesn't exist); `trade_license_number` is
  flagged as the sole future candidate for a verification-status reset, documented as a placeholder rule, not
  implemented in code.
- **Auth gating (Decision 7):** bare authentication (not `require_role(ROLE_PROVIDER)`), avoiding ADR-016's
  documented token-refresh-lag edge case, relying on the existing `ProviderNotFoundError` 404 for equivalent
  protection.

**Delegation order:** `backend` → `frontend` → `tester` → `architect`, per the standard chain, pausing for user
sign-off once `tester`/`architect` both report clean.

---

## Related Documents

- `docs/implementation/plans/Plan_S04_PRO-002.md`
- `docs/implementation/plans/Plan_S04_PRO-001.md`
- `docs/implementation/walkthroughs/Walkthrough_S04_PRO-001.md`
