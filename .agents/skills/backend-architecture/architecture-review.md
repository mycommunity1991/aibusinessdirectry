# Rule: Architecture Review 

## Directive
When acting as a code reviewer, you must evaluate code strictly against structural boundaries, dependency direction, and testability. Do not focus solely on syntax or clean code; your primary goal is to prevent architectural degradation.

## Review Constraints

1.  **Boundary Check:** Verify that no imports cross forbidden layer boundaries. (e.g., The Domain layer importing an external HTTP client must trigger an immediate rejection).
2.  **Contract Stability Check:** Evaluate if the code changes public API contracts or inter-module interface signatures. Reject breaking changes to public contracts if an additive, backward-compatible change is possible.
3.  **Testability Check:** Verify that the core business rules added or modified can be tested 100% in-memory without a database, network call, or filesystem access.
4.  **Separation Check:** Ensure the responsibilities remain pure: Controllers only route, Services only orchestrate, Entities only enforce rules, and Repositories only persist.

## Feedback Rules

* **Be Direct:** State the exact architectural rule violated (e.g., "Violation of Dependency Inversion: Application service depends directly on SQL driver").
* **Provide the Fix:** Do not just point out the flaw. Provide the exact interface definition or DTO structure required to resolve the boundary violation.
* **Reject Silenced Warnings:** Do not allow developers to bypass architectural linter rules or suppress dependency warnings without a documented exception.