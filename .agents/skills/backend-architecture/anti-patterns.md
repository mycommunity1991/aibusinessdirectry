# Rule: Anti-Patterns

## Directive
You must proactively scan for and reject common architectural anti-patterns. These patterns degrade maintainability, increase coupling, and must be blocked during code generation and code review.

## Critical Anti-Patterns to Reject

1.  **The God Class / God Module:** Reject any class, module, or service that aggregates unrelated business functions. Specifically, reject naming conventions like `Common`, `Util`, `Manager`, `Processor`, or `Helper`. Enforce splitting by exact business capability.
2.  **Framework Coupling:** Reject business logic (Application or Domain layer) that inherits from framework-specific base classes or uses framework-specific decorators/annotations for core execution.
3.  **Shotgun Surgery:** If a single, conceptually simple business requirement change forces modifications across multiple unrelated modules, flag the architecture as highly coupled and demand a redesign of the boundaries.
4.  **Sequential Coupling:** Reject APIs or services that require a consumer to call methods in a strict, undocumented order to achieve a valid state (e.g., calling `init()`, then `load()`, then `process()`). Enforce valid state upon object instantiation.
5.  **Exception-Driven Logic:** Reject code that uses `try/catch` blocks for regular control flow or standard business rule validation. Exceptions must be reserved for exceptional, unexpected system failures.