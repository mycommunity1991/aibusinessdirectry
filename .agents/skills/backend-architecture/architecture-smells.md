# Rule: Architecture Smells

## Directive
You must proactively detect and flag architectural smells during code generation and review. Smells are not always immediate bugs, but they indicate structural weaknesses that will degrade maintainability over time. 

## Critical Smells to Flag

1.  **Deep Call Chains:** Flag code where a request traverses more than the standard layers (Controller -> Service -> Domain -> Repository). Reject excessive nesting (e.g., `Controller -> Facade -> Coordinator -> Manager -> Repository`).
2.  **Data Clumps:** Flag instances where the exact same group of primitive variables (e.g., `startDate`, `endDate`, `currency`) are passed together across multiple methods or classes. Force the extraction of a Value Object.
3.  **Divergent Change:** Flag classes that have to be modified for multiple, unrelated reasons. This is a violation of the Single Responsibility Principle.
4.  **Primitive Obsession:** Flag the use of raw strings or integers for domain concepts that possess inherent validation rules (e.g., passing an email as a `string` instead of an `EmailAddress` Value Object).
5.  **Cyclic Dependencies:** Flag and reject any circular references between modules, packages, or bounded contexts. 

## Code Review Action
* When a smell is detected, you must clearly state: "Architectural Smell Detected: [Smell Name]" and provide the explicit refactoring steps to resolve it.