# Rule: Confidence Scoring & Wizard-of-Oz Fallback

## Scoring
* **Persist Every Score:** Write each computed confidence value to `confidence_scores`, and cache the latest on `conversation_sessions.final_confidence_score` — never compute a score without persisting it, since it's an auditable input to a routing decision.
* **Model-Version Tagging:** Tag each score with the prompt/model version that produced it (`model_version`), so a routing regression can be traced to a specific prompt change.

## Fallback Routing
* **Below-Threshold = Manual, Not Blocked:** Sessions below the confidence threshold must create a `manual_match_assignments` row and notify an Admin — never leave the customer without a next step and never silently downgrade to a lower-quality automated match instead of routing.
* **No Silent Retries:** Do not retry the LLM call in a loop hoping for a higher score; a low score is a legitimate signal, not a failure to be masked.
