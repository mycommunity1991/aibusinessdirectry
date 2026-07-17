# Rule: Verification Lifecycle

## Status Transitions
* **Enforce the State Machine:** `pending → under_review → approved | rejected` only. No status transition may skip `under_review` for a Freelancer, and no code path may move a record backward from `approved` without creating a new record (append a new verification cycle rather than mutating history).
* **Cache Sync in One Transaction:** Any write to `verification_records.status` must update `providers.verification_status` and recompute `providers.is_discoverable` in the same database transaction — never leave the cache stale even momentarily on the write path.

## Admin Review
* **Reviewer Attribution:** Every `approved`/`rejected` transition records `reviewed_by` and, when rejected, a `rejection_reason` — an unattributed status change is a defect.
* **Notify on Change:** A verification status change must trigger a Notification to the affected Provider (per the Notification domain) — status changes are not "check later" events.
