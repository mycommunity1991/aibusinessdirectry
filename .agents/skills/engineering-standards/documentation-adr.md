# Rule: Architecture Decision Records (ADR)

## Purpose of ADRs
Any time a significant technical choice is made (e.g., introducing a new library, changing a database schema strategy, altering a module boundary), it must be documented using an Architecture Decision Record.

## ADR Format
Every ADR must be saved as a markdown file in the `docs/architecture/decisions/` directory and include the following sections:

1. **Title:** A short noun phrase (e.g., "Use Redis for Session Caching").
2. **Status:** Proposed, Accepted, Deprecated, or Superseded.
3. **Context:** What is the technical or business problem that prompted this decision? Be objective and factual.
4. **Decision:** What is the specific change or pattern being adopted?
5. **Consequences:** * **Positive:** What becomes easier or better?
   * **Negative:** What trade-offs are we accepting? (e.g., increased infrastructure cost, added complexity).