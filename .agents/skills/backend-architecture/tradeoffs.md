# Rule: Architectural Trade-Offs

## Directive
Architecture is the act of balancing competing priorities. You must explicitly evaluate and document trade-offs when making design decisions. You must never assume a pattern is universally correct without context.

## Standard Trade-Off Evaluations

1.  **Simplicity vs. Flexibility:** Always default to Simplicity (KISS). Do not introduce abstractions (Flexibility) until a second or third concrete use case demands it (Rule of Three).
2.  **Performance vs. Readability:** Always default to Readability. Do not approve micro-optimizations, bitwise operations, or complex caching that degrades code clarity unless there is a proven, measured performance bottleneck.
3.  **Duplication vs. Coupling:** Accept minor code duplication if extracting a shared library or utility class would create tight coupling between two otherwise independent Bounded Contexts. (It is better to duplicate a small DTO than to force two distinct modules to depend on the same shared package).
4.  **Consistency vs. Availability:** In distributed components or asynchronous event handling, explicitly define whether the business process requires strong consistency (immediate database locks) or eventual consistency (event-driven, highly available). 

## Anti-Patterns to Reject
* **Hiding the Compromise:** Reject architectural proposals that claim to have "no downsides." Force the identification of what is being sacrificed.