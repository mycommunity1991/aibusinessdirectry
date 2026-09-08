/// A coarse, shared summary of the caller's own verification status --
/// deliberately independent of `features/verification/`'s full
/// `VerificationRecord`/`VerificationRecordStatus` model
/// (`docs/AI/02_ARCHITECTURE.md`: "Features must not depend directly on
/// each other. Shared functionality belongs in shared modules.").
///
/// Any feature that only needs "what should a status chip/badge show" --
/// not the full record (rejection reason, documents, timestamps) --
/// should depend on this instead of importing `features/verification/`.
///
/// `pending`/`under_review` from the backend both collapse to
/// [underReview] here, mirroring how they were already treated
/// identically wherever this summary is rendered.
enum VerificationStatusSummary { notStarted, underReview, approved, rejected }
