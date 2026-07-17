# Rule: Prompt Grounding & RAG

## Retrieval Before Generation
* **Query Real Data First:** Before the LLM drafts a recommendation, retrieve candidate Providers via the Search/Matching service (category + service-area filter). Pass only retrieved records into the prompt context — never let the model recall from training data.
* **No Invented Attributes:** If a retrieved Provider record has a null field (e.g. no price range set), the AI must say so, not infer or estimate a value.

## Prompt Construction
* **System Prompt Ownership:** System prompts live in version-controlled files under the Conversation module, not inline strings scattered across services — treat them as reviewable artifacts, same as SQL migrations.
* **Structured Output:** Require the LLM to return structured JSON matching the `Search Request` schema (`structured_criteria`), validated through a Pydantic v2 model before persistence. Free-text-only responses must be rejected and retried.

## Bilingual Handling
* **Language-Aware Prompting:** Detect or read the customer's `preferred_language` (en/ar) and prompt/respond in that language; do not silently default to English for Arabic-speaking customers.
