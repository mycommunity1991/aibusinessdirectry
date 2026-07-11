# Rule: Feature-First Architecture

## Module Boundaries
* **Strict Encapsulation:** Code is organized by feature (e.g., `lib/features/communities/`), not by layer (e.g., `lib/models/`).
* [cite_start]**Shared Kernel:** Shared functionality (e.g., networking client, generic UI components, core utilities) exists only inside a dedicated `lib/shared/` or `lib/core/` module.
* **Cross-Feature Communication:** Features must not depend on each other directly. If Feature A needs data from Feature B, it must be accessed via shared Riverpod providers or a routing parameter.

## Routing with GoRouter
* [cite_start]**Declarative Navigation:** Strictly use `GoRouter` for all application navigation. Never use the legacy `Navigator.push()` or `Navigator.pop()`.
* **Type-Safe Routes:** Define route names as constants. Pass complex data between routes using object IDs in the path or query parameters, fetching the actual object from a local provider, rather than passing heavy objects directly through the router.