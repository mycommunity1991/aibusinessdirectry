# Rule: Architectural Decision Making

## Directive
You must evaluate every architectural choice using a strict priority matrix. You must articulate the trade-offs of your decisions and enforce objective, business-driven engineering over hype-driven or speculative development.

## Core Rules

1.  **The Evaluation Matrix:** Force all architectural decisions through this exact priority order: `Business Correctness > Security > Simplicity > Maintainability > Testability > Scalability > Performance`. Never sacrifice a higher-priority attribute for a lower-priority one without explicit instruction.
2.  **Trade-Off Justification:** Whenever you propose a design or pattern, you must explicitly state what is being optimized and what is being sacrificed (e.g., "Optimizing for read performance at the cost of eventual consistency").
3.  **YAGNI (You Aren't Gonna Need It) Enforcement:** Refuse to build abstractions, generic interfaces, or extension points for hypothetical future requirements. Only implement solutions for verified, current requirements.
4.  **Technology Independence:** Make architectural decisions assuming the underlying framework, cloud provider, or database will eventually be replaced. 

## Anti-Patterns to Reject

* **Resume-Driven Development:** Reject proposals that introduce complex distributed systems (e.g., Kafka, Microservices) for simple, low-traffic CRUD applications. Enforce the Modular Monolith by default.
* **Optimization Without Measurement:** Reject complex caching, multi-threading, or denormalization patterns unless there is an explicitly stated performance bottleneck. 
* **The Golden Hammer:** Reject forcing a single design pattern (e.g., Event Sourcing) onto every bounded context just because it worked well in one specific context.