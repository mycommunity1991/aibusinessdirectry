from app.shared.schemas.response import ErrorDetail


class BusinessException(Exception):  # noqa: N818
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        errors: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        self.headers = headers
        super().__init__(self.message)


class InvalidTokenError(BusinessException):
    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ExpiredTokenError(BusinessException):
    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthenticationRequiredError(BusinessException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidOtpError(BusinessException):
    """
    Raised whenever an OTP code cannot be verified — whether it is wrong,
    expired, already used, or simply doesn't exist for that phone number.

    Deliberately generic (AC5/AC10): the message never reveals which of
    those conditions applied, and never reveals whether the phone number
    is registered.
    """

    def __init__(
        self,
        message: str = "That code didn't work — check the digits and try again.",
    ):
        super().__init__(message=message, status_code=400)


class OtpLockedError(BusinessException):
    """Raised when an OTP has reached its maximum verification attempts."""

    def __init__(
        self,
        message: str = (
            "Too many incorrect attempts. Please request a new code and try again."
        ),
    ):
        super().__init__(message=message, status_code=429)


class InvalidIdentityTokenError(BusinessException):
    """
    Raised whenever a Google/Apple ID token cannot be verified -- whether
    the signature, issuer, audience, or expiry check failed, the token
    was malformed, or the provider's JWKS could not be fetched.

    Deliberately generic (AC6, AUTH-002): the message never reveals which
    of those conditions applied, mirroring `InvalidOtpError`'s
    non-revealing design.
    """

    def __init__(
        self,
        message: str = "We couldn't verify your sign-in. Please try again.",
    ):
        super().__init__(message=message, status_code=401)


class InvalidRefreshTokenError(BusinessException):
    """
    Raised whenever a refresh token cannot be used to mint a new
    access/refresh pair -- whether it doesn't exist, is expired, was
    already revoked, or was already rotated away and is being replayed
    (AUTH-003, AC5).

    Deliberately generic, mirroring `InvalidOtpError`/
    `InvalidIdentityTokenError`'s non-revealing design: the message never
    reveals which of those conditions applied.
    """

    def __init__(
        self,
        message: str = "That session could not be refreshed. Please sign in again.",
    ):
        super().__init__(
            message=message,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class SessionNotFoundError(BusinessException):
    """
    Raised by `DELETE /auth/sessions/{id}` (and any other session lookup)
    when a session either doesn't exist at all, or exists but is not
    owned by the requesting user (AUTH-003, AC8/AC10).

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- consistent with this project's existing
    non-revealing-error philosophy (Decision 9,
    `Plan_S02_AUTH-003.md`).
    """

    def __init__(self, message: str = "Session not found."):
        super().__init__(message=message, status_code=404)


class SavedAddressNotFoundError(BusinessException):
    """
    Raised by `GET`/`PATCH`/`DELETE /customers/me/addresses/{id}` when a
    saved address either doesn't exist at all, or exists but is not
    owned by the requesting customer (CUS-002, AC8).

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- mirrors `SessionNotFoundError`'s
    non-revealing design exactly (Decision 1, `Plan_S03_CUS-002.md`).
    """

    def __init__(self, message: str = "Address not found."):
        super().__init__(message=message, status_code=404)


class InsufficientRoleError(BusinessException):
    """
    Raised by `require_role()` (AUTH-004, AC3) when a caller is
    authenticated (a valid, unexpired token was already accepted by
    `get_current_user`) but their `roles` claim does not intersect the
    endpoint's allowed set.

    Deliberately distinct from every 401 exception above: this is only
    ever raised for a *validly authenticated* caller, so 401 and 403 are
    never used interchangeably (AC2/AC3). Deliberately generic -- never
    reveals which role(s) were required, mirroring this project's
    established non-revealing-error philosophy.
    """

    def __init__(
        self,
        message: str = "You don't have permission to perform this action.",
    ):
        super().__init__(message=message, status_code=403)


class ProviderAlreadyExistsError(BusinessException):
    """
    Raised by `POST /providers/me` (PRO-001, AC8/AC10) when the caller's
    Account already has a Provider -- regardless of the newly-requested
    `provider_type`. This single check is what makes `provider_type`
    immutable: a second call with a *different* type is rejected exactly
    like a second call with the *same* type (Decision 3,
    `Plan_S04_PRO-001.md`).

    A plain 409, not the non-revealing-ownership pattern used elsewhere
    (e.g. `SavedAddressNotFoundError`) -- this is always about the
    caller's own resource, never another account's data.
    """

    def __init__(self, message: str = "You already have a provider listing."):
        super().__init__(message=message, status_code=409)


class ProviderNotFoundError(BusinessException):
    """
    Raised by `GET /providers/me` (PRO-001, Decision 9) when the caller
    has not yet created a Provider. Plain, not non-revealing -- this is
    always the caller's own account, never another user's data.
    """

    def __init__(self, message: str = "Provider not found."):
        super().__init__(message=message, status_code=404)


class InvalidPortfolioUploadError(BusinessException):
    """
    Raised by `POST /providers/me/portfolio` (PRO-002, AC2) when an
    uploaded photo fails size, extension, or MIME/magic-byte validation
    (`image_validation.validate_image_upload`).

    Deliberately generic (Decision 2, `Plan_S04_PRO-002.md`) -- mirrors
    `InvalidOtpError`'s non-revealing pattern: never states exactly which
    check failed (size vs. type), to avoid giving a bad actor a probing
    oracle.
    """

    def __init__(
        self,
        message: str = "That photo couldn't be uploaded. Please try a different file.",
    ):
        super().__init__(message=message, status_code=422)


class PortfolioPhotoNotFoundError(BusinessException):
    """
    Raised by `DELETE /providers/me/portfolio/{portfolio_id}` (PRO-002,
    AC7/AC8) when a portfolio photo either doesn't exist at all, or
    exists but is not owned by the requesting provider.

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- mirrors `SavedAddressNotFoundError`'s
    non-revealing design exactly (ADR-015).
    """

    def __init__(self, message: str = "Portfolio photo not found."):
        super().__init__(message=message, status_code=404)


class PortfolioLimitExceededError(BusinessException):
    """
    Raised by `POST /providers/me/portfolio` (PRO-002, Decision 3,
    `Plan_S04_PRO-002.md`) when a provider already has
    `MAX_PORTFOLIO_PHOTOS_PER_PROVIDER` active photos.
    """

    def __init__(
        self,
        message: str = "You've reached the maximum number of portfolio photos.",
    ):
        super().__init__(message=message, status_code=409)


class InvalidPortfolioReorderError(BusinessException):
    """
    Raised by `PUT /providers/me/portfolio/order` (PRO-002, Decision 4,
    `Plan_S04_PRO-002.md`) when the submitted `ordered_ids` set does not
    exactly match the caller's own active photo ids (a foreign id, a
    missing id, or a duplicate) -- rejected before any row is touched,
    never a partial reorder. Not explicitly named in the Plan's item 16
    exception list, but required by Decision 4's literal "rejected
    (422)" text; added here as the minimal, consistently-styled
    exception that satisfies it.
    """

    def __init__(
        self,
        message: str = (
            "The submitted photo order does not match your current photos."
        ),
    ):
        super().__init__(message=message, status_code=422)


class InvalidCategoryLabelsError(BusinessException):
    """
    Raised by `PATCH /providers/me` (PRO-002, AC4) when a submitted
    `category_labels` list has zero or more than one `is_primary: true`
    entry, or exceeds the 5-label cap (Decision 1, `Plan_S04_PRO-002.md`).
    """

    def __init__(
        self,
        message: str = (
            "Category labels must include exactly one primary label, "
            "up to a maximum of 5."
        ),
    ):
        super().__init__(message=message, status_code=422)


class SubtypeDetailsMismatchError(BusinessException):
    """
    Raised by `PATCH /providers/me` (PRO-002, Decision 8,
    `Plan_S04_PRO-002.md`) when the payload's `business_details`/
    `freelancer_details` object does not match the provider's actual,
    already-established `provider_type` -- `provider_type` itself remains
    immutable (PRO-001, Decision 3), so this is always a payload error,
    not a state change.
    """

    def __init__(
        self,
        message: str = (
            "This provider's type does not match the submitted details object."
        ),
    ):
        super().__init__(message=message, status_code=400)


class VerificationRecordNotFoundError(BusinessException):
    """
    Raised by `GET /providers/me/verification` (VER-001, AC6) when the
    caller has never submitted a verification cycle. Plain, not
    non-revealing -- this is always the caller's own status, never
    another user's data.
    """

    def __init__(self, message: str = "No verification submission found."):
        super().__init__(message=message, status_code=404)


class VerificationDocumentNotFoundError(BusinessException):
    """
    Raised by `GET /providers/me/verification/documents/{document_id}/file`
    (VER-001, Decision 4/7) when a document either doesn't exist at all,
    or exists but its parent record is not owned by the requesting
    provider.

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- mirrors `PortfolioPhotoNotFoundError`'s
    non-revealing design exactly (ADR-015).
    """

    def __init__(self, message: str = "Verification document not found."):
        super().__init__(message=message, status_code=404)


class VerificationSubmissionNotAllowedError(BusinessException):
    """
    Raised by `POST /providers/me/verification` (VER-001, Decision 4,
    `Plan_S05_VER-001.md`) when the caller's latest existing verification
    record is anything other than absent or `rejected` -- i.e. a
    `pending`/`under_review`/`approved` cycle is already active, so a
    duplicate submission is rejected rather than creating a second
    concurrent cycle.
    """

    def __init__(
        self,
        message: str = (
            "You already have an active verification submission in progress."
        ),
    ):
        super().__init__(message=message, status_code=409)


class VerificationDocumentRequiredError(BusinessException):
    """
    Raised by `POST /providers/me/verification` (VER-001, AC2) when the
    resolved `verification_type` requires a document (always true for
    Freelancer; configurable for Business) but no pending-slot file
    exists for the caller -- i.e. `POST .../documents/preview` was never
    called, or was called with a different `document_type` than the one
    the submission actually requires (AC2's Freelancer-must-submit-
    Emirates-ID rule).
    """

    def __init__(
        self,
        message: str = "Please upload and confirm your document before submitting.",
    ):
        super().__init__(message=message, status_code=422)


class VerificationDocumentTooLargeError(BusinessException):
    """
    Raised by `document_validation.validate_verification_document_upload`
    (VER-001, Decision 8, AC3) when an uploaded document is empty or
    exceeds `MAX_VERIFICATION_DOCUMENT_SIZE_BYTES`. Deliberately distinct
    from `VerificationDocumentInvalidTypeError` -- AC3 requires a
    specific, actionable error per failure category, not one generic
    message.
    """

    def __init__(
        self,
        message: str = "This file is too large. The maximum size is 10 MB.",
    ):
        super().__init__(message=message, status_code=422)


class CustomerProfileNotFoundError(BusinessException):
    """
    Raised defensively by `ContactService.create_contact_view` (CON-001,
    Decision 1, `Plan_S08_CON-001.md`) if the calling, already-
    authenticated user somehow has no `customer_profiles` row. Not
    expected to occur in practice -- `AuthService` provisions a
    `customer_profiles` row for every account at registration
    (CUS-001) -- but this method never silently no-ops on a missing
    row, mirroring `apply_verification_outcome`'s identical defensive
    posture for a similarly-should-never-happen missing `Provider` row.
    """

    def __init__(self, message: str = "Customer profile not found."):
        super().__init__(message=message, status_code=404)


class SelfDealingContactError(BusinessException):
    """
    Raised by `ContactService.create_contact_view` (CON-001, AC3/AC4,
    Decision 10, `Plan_S08_CON-001.md`) when the requesting Customer's
    Account is the same Account that owns the target Provider -- i.e.
    `provider.user_id == current_user_id`. Enforced before any
    `contact_views` row is written.

    403, not 409 -- this is not a race or a timing issue, it is a
    permanent, identity-based authorization rule: this specific caller
    may never create this specific write, regardless of retry timing.
    No information-leakage concern applies (unlike claim-flow's masked
    404s) since the caller already knows they own the target listing.
    """

    def __init__(self, message: str = "You can't contact your own listing."):
        super().__init__(message=message, status_code=403)


class VerificationDocumentInvalidTypeError(BusinessException):
    """
    Raised by `document_validation.validate_verification_document_upload`
    (VER-001, Decision 8, AC3) when an uploaded document's extension is
    disallowed, or its actual content (magic bytes) does not match its
    declared extension/`Content-Type`. Deliberately distinct from
    `VerificationDocumentTooLargeError` (AC3).
    """

    def __init__(
        self,
        message: str = (
            "Unsupported file type. Please upload a JPG, PNG, WEBP, or PDF file."
        ),
    ):
        super().__init__(message=message, status_code=422)


class VerificationRecordNotActionableError(BusinessException):
    """
    Raised by `POST /admin/verification/records/{record_id}/approve`/
    `reject` (VER-002, Decision 6, `Plan_S05_VER-002.md`) when the
    record's current `status` is not `pending`/`under_review` -- i.e. it
    was already approved or rejected by an earlier action and cannot be
    re-acted on. No separate "start review" transition exists, so this
    is the only conflict state this pair of endpoints can be in.
    """

    def __init__(
        self,
        message: str = "This verification record has already been reviewed.",
    ):
        super().__init__(message=message, status_code=409)


class RateLimitExceededError(BusinessException):
    """
    Raised when a client exceeds a Redis-backed fixed-window rate limit
    (`05_API_GUIDELINES.md`/`06_SECURITY.md` "Rate Limiting").

    Distinct in *meaning* from `OtpLockedError` (which caps wrong-code
    attempts against a single, already-issued OTP): this caps how fast a
    client can hit an endpoint at all. Both currently map to the same 429
    status code and a similarly plain-language message, by design —
    `06_SECURITY.md` requires generic, non-technical error copy either way.
    """

    def __init__(
        self,
        message: str = "Too many requests. Please wait a moment and try again.",
    ):
        super().__init__(message=message, status_code=429)


class ClaimTargetNotFoundError(BusinessException):
    """
    Raised by `ClaimService` (CLM-001, Backend Proposed Changes item 5,
    `Plan_S06_CLM-001.md`) when the target `provider_id` either doesn't
    exist at all, or exists but is not a still-unclaimed Google-seeded
    listing (`listing_source=google_seeded_unclaimed`, `is_claimed=
    false`) -- a self-registered or already-claimed provider can never
    be a claim target, and both cases collapse into the same 404 rather
    than revealing which.
    """

    def __init__(self, message: str = "This listing is not available to claim."):
        super().__init__(message=message, status_code=404)


class ClaimPublicNumberUnavailableError(BusinessException):
    """
    Raised by `ClaimService.request_otp` (CLM-001, AC6) when the target
    listing has no public phone number on record
    (`phone_number is None`) -- the OTP-against-public-record trust gate
    is structurally unusable for this listing, so no OTP is ever sent;
    the caller is expected to fall back to `request_admin_review` with
    `reason="no_public_number"`.
    """

    def __init__(
        self,
        message: str = (
            "This listing has no public phone number on file. Please request "
            "manual review instead."
        ),
    ):
        super().__init__(message=message, status_code=409)


class ClaimAlreadyClaimedError(BusinessException):
    """
    Raised by `ClaimService._finalize_claim` (CLM-001, Decision 6,
    `Plan_S06_CLM-001.md`) when the target listing has already been
    claimed by the time finalization runs -- either re-checked
    immediately before the write (defends against two concurrent
    claimants racing the same listing) or because the claimant's own
    Account already owns a different Provider (the existing
    one-Provider-per-Account rule, PRO-001 AC8, reused unmodified via
    the same `ProviderAlreadyExistsError`-style 409 shape, under a
    claim-specific name/message).
    """

    def __init__(
        self,
        message: str = "This listing has already been claimed.",
    ):
        super().__init__(message=message, status_code=409)


class ClaimReviewRequestNotFoundError(BusinessException):
    """
    Raised by `AdminClaimService`/`ClaimReviewRequestService` (CLM-001,
    Decision 9) when a `claim_review_requests` row does not exist for
    the given id.
    """

    def __init__(self, message: str = "Claim review request not found."):
        super().__init__(message=message, status_code=404)


class ConversationSessionNotFoundError(BusinessException):
    """
    Raised by `ConversationService` (AI-001, ADR-015) when a
    `conversation_sessions` row either doesn't exist at all, or exists
    but is not owned by the requesting customer.

    Deliberately collapses both cases into the same 404 rather than a
    403 for the ownership case -- mirrors `SavedAddressNotFoundError`'s
    non-revealing design exactly.
    """

    def __init__(self, message: str = "Conversation session not found."):
        super().__init__(message=message, status_code=404)


class ConversationSessionNotActiveError(BusinessException):
    """
    Raised by `ConversationService.submit_turn` (AI-001, Decision 4) when
    a turn is submitted to a session whose `status` is anything other
    than `active` (`completed`/`routed_to_admin`/`abandoned`) -- a
    finished or superseded conversation cannot silently accept a new
    turn.
    """

    def __init__(
        self,
        message: str = "This conversation is no longer active.",
    ):
        super().__init__(message=message, status_code=409)


class AnswerNotRevisableError(BusinessException):
    """
    Raised by `ConversationService.revise_answer` (AI-001, Decision 5,
    AC8) when the targeted `message_id` either doesn't exist in the
    session at all, doesn't belong to `sender=customer`, or the session
    itself is `abandoned` (superseded by a newer session -- "Start over"
    is the intended path for a superseded conversation, not reviving it,
    which would otherwise let a customer have two `active` sessions at
    once).
    """

    def __init__(
        self,
        message: str = "That answer cannot be revised.",
    ):
        super().__init__(message=message, status_code=422)


class InvalidStructuredCriteriaError(BusinessException):
    """
    Raised by `ConversationService` (AI-001, Decision 1b, AC9) when the
    `StructuredCriteria` payload it built at session-completion time
    fails Pydantic validation. Should never occur in correct code --
    `ConversationService` constructs the payload itself from data it
    already trusts -- but the validation gate is real, not decorative,
    and this is surfaced as a distinct, loggable 500 rather than a raw
    `pydantic.ValidationError` leaking out of the service layer.
    """

    def __init__(
        self,
        message: str = "Could not finalize this conversation's summary.",
    ):
        super().__init__(message=message, status_code=500)


class ManualMatchAssignmentNotFoundError(BusinessException):
    """
    Raised by `ManualMatchAssignmentService`/`SearchRequestService`
    (AI-002, Decision 3, `Plan_S07_AI-002.md`) when a
    `manual_match_assignments` row does not exist for the given id.
    """

    def __init__(self, message: str = "Manual match assignment not found."):
        super().__init__(message=message, status_code=404)


class ManualMatchAssignmentAlreadyResolvedError(BusinessException):
    """
    Raised by `ManualMatchAssignmentService.resolve` (AI-002, Decision 3)
    when an assignment whose `status` is already `completed` is resolved
    again -- rejected rather than silently double-finalizing the
    underlying `search_requests`/`provider_matches` state (AC4/AC6's
    "identical shape, exactly once" guarantee).
    """

    def __init__(
        self,
        message: str = "This manual match assignment has already been resolved.",
    ):
        super().__init__(message=message, status_code=409)


class SearchRequestNotFoundError(BusinessException):
    """
    Raised by `SearchRequestService` (AI-002, Decision 6, ADR-015) when a
    `search_requests` row either doesn't exist at all, or exists but is
    not owned by the requesting customer -- collapses both cases into
    the same 404, mirroring `ConversationSessionNotFoundError`'s
    non-revealing design exactly.
    """

    def __init__(self, message: str = "Search request not found."):
        super().__init__(message=message, status_code=404)


class InvalidManualMatchProviderIdsError(BusinessException):
    """
    Raised by `SearchRequestService.resolve_manual_match` (AI-002) when
    the admin-supplied `provider_ids` list contains one or more ids that
    don't correspond to a real `providers` row -- validated **before**
    `_finalize_matches`/`ProviderMatchRepository.bulk_create` ever runs,
    so a bogus id is rejected as an actionable 422 rather than
    surfacing as an opaque 500 from the underlying FK constraint
    violation (`08_CODING_STANDARDS.md`'s "validate every endpoint's
    input" rule).
    """

    def __init__(
        self,
        message: str = ("One or more of the submitted provider ids does not exist."),
    ):
        super().__init__(message=message, status_code=422)


class InvalidSearchRadiusError(BusinessException):
    """
    Raised by `GET /search/providers` (DIR-001, Backend Proposed Changes
    item 13, `Plan_S06_DIR-001.md`) when the caller's `radius_km` query
    parameter is outside the configured bounds (`0 < radius_km <=
    settings.SEARCH_MAX_RADIUS_KM`) -- rejected before any repository
    query runs.
    """

    def __init__(
        self,
        message: str = "The requested search radius is invalid.",
    ):
        super().__init__(message=message, status_code=422)


class ContactViewNotFoundError(BusinessException):
    """
    Raised by `OutcomeTagService.submit_outcome_tag` (REV-001, AC2,
    Decision 2, `Plan_S09_REV-001.md`) when the target `contact_view_id`
    either doesn't exist at all, or exists but is not owned by the
    calling customer -- collapses both cases into the same 404,
    mirroring `SearchRequestNotFoundError`/`ConversationSessionNotFoundError`'s
    identical non-revealing-404 design (ADR-015), via the same
    `ensure_owner_or_not_found` helper CON-001's own `search_request_id`
    ownership check already uses. Deliberately a 404, never a 403 --
    a different shape from `SelfDealingContactError`, which is a
    permanent, identity-based rule rather than an ordinary
    `{id}`-addressable-resource ownership check.
    """

    def __init__(self, message: str = "Contact view not found."):
        super().__init__(message=message, status_code=404)


class OutcomeTagAlreadyExistsError(BusinessException):
    """
    Raised by `OutcomeTagService.submit_outcome_tag` (REV-001, AC1/AC6,
    Decision 3, `Plan_S09_REV-001.md`) when `OutcomeTagRepository.
    try_create`'s atomic `INSERT ... ON CONFLICT DO NOTHING ...
    RETURNING` finds a row already exists for the target
    `contact_view_id` -- a genuine timing conflict (e.g. a double-tap),
    mirroring `ClaimAlreadyClaimedError`'s existing 409 shape, not the
    self-dealing guard's 403 shape. An Outcome Tag is immutable and
    one-shot (Decision 4) -- this is also the only response a second,
    later, deliberate resubmission attempt will ever receive, since no
    update/resubmission path exists.
    """

    def __init__(self, message: str = "An outcome tag was already submitted."):
        super().__init__(message=message, status_code=409)


class ReviewAnchorNotVerifiedError(BusinessException):
    """
    Raised by `ReviewService.submit_review` (REV-002, AC2, Decision 5,
    `Plan_S09_REV-002.md`) when the anchoring `ContactView` has no
    `contact.outcome_tags` row at all, or has one with `hired=False` --
    AC2's own wording treats both cases identically ("attempting
    otherwise (no outcome tag, or `hired=false`) is rejected"), so one
    exception covers both, mirroring `VerificationSubmissionNotAllowedError`/
    `VerificationRecordNotActionableError`/
    `ManualMatchAssignmentAlreadyResolvedError`'s existing "resource
    exists, ownership isn't in question, but its current state blocks
    this specific write" 409 shape.

    409, not 403 -- unlike `SelfDealingContactError`, this is not a
    permanent, identity-based rule: a `hired=false` (or missing) outcome
    tag today doesn't mean this exact `contact_view_id` could never
    anchor a review under any circumstance, it means the current
    recorded outcome doesn't support one. Not a 404 either -- the
    `ContactView` itself is genuinely found and owned by the caller;
    nothing is being hidden.
    """

    def __init__(
        self,
        message: str = (
            "This contact view does not have a confirmed hire outcome yet."
        ),
    ):
        super().__init__(message=message, status_code=409)


class ReviewAlreadyExistsError(BusinessException):
    """
    Raised by `ReviewService.submit_review` (REV-002, AC1, Decision 3
    step 2/Decision 5, `Plan_S09_REV-002.md`) when `ReviewRepository.
    try_create`'s atomic `INSERT ... ON CONFLICT DO NOTHING ...
    RETURNING` finds a row already exists for the target
    `contact_view_id` -- a genuine timing conflict, mirroring
    `OutcomeTagAlreadyExistsError`/`ClaimAlreadyClaimedError`'s existing
    409 shape. A Review is immutable and one-shot (mirrors `OutcomeTag`'s
    precedent) -- this is also the only response a second, later,
    deliberate resubmission attempt will ever receive, since no update
    path exists.
    """

    def __init__(self, message: str = "A review was already submitted."):
        super().__init__(message=message, status_code=409)


class FeatureFlagNotFoundError(BusinessException):
    """
    Raised by `FeatureFlagService.toggle` (ADM-002, Decision 3,
    `Plan_S11_ADM-002.md`) when a `feature_flags` row does not exist for
    the given `key` -- feature-flag keys are code-defined and
    migration-seeded only (Decision 3), never created via the API, so an
    unknown key is always a genuine 404, mirroring
    `UnmatchedQueryReportNotFoundError`'s identical shape.
    """

    def __init__(self, message: str = "Feature flag not found."):
        super().__init__(message=message, status_code=404)


class SystemSettingNotFoundError(BusinessException):
    """
    Raised by `SystemSettingService.update_value` (ADM-002, Decision 3,
    `Plan_S11_ADM-002.md`) when a `system_settings` row does not exist
    for the given `key` -- mirrors `FeatureFlagNotFoundError`'s identical
    shape and reasoning.
    """

    def __init__(self, message: str = "System setting not found."):
        super().__init__(message=message, status_code=404)


class UnmatchedQueryReportNotFoundError(BusinessException):
    """
    Raised by `UnmatchedQueryReportService` (ADM-001, Decision 6,
    `Plan_S11_ADM-001.md`) when an `unmatched_query_reports` row does not
    exist for the given id -- mirrors `ManualMatchAssignmentNotFoundError`/
    `ClaimReviewRequestNotFoundError`'s identical 404 shape.
    """

    def __init__(self, message: str = "Unmatched query report not found."):
        super().__init__(message=message, status_code=404)


class UnmatchedQueryReportInvalidTransitionError(BusinessException):
    """
    Raised by `UnmatchedQueryReportService.mark_reviewed`/`mark_actioned`
    (ADM-001, Decision 8) when the report's current `status` does not
    allow the requested transition (a repeat call, or an attempted
    backward move) -- mirrors `ManualMatchAssignmentAlreadyResolvedError`'s
    409 shape (`ADR-053`'s "reuse for an identical underlying reason,
    add new only for a genuinely distinct reason": both failure paths
    here collapse to "this transition isn't valid from the report's
    current status", so one exception covers both entry points).
    """

    def __init__(
        self,
        message: str = (
            "This status transition is not valid from the report's current status."
        ),
    ):
        super().__init__(message=message, status_code=409)


class NotificationNotFoundError(BusinessException):
    """
    Raised by `NotificationService`/the `PATCH /notifications/{id}/read`
    route (`ENG-001`, Decision 10, `Plan_S12_ENG-001.md`) when the
    target notification either doesn't exist at all, or exists but is
    not owned by the calling user -- collapses both cases into the same
    404, mirroring `ContactViewNotFoundError`'s identical non-revealing-
    404 design (`ADR-015`), via the same `ensure_owner_or_not_found`
    helper. Deliberately a 404, never a 403.
    """

    def __init__(self, message: str = "Notification not found."):
        super().__init__(message=message, status_code=404)
