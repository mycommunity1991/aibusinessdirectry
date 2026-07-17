# Rule: Matching Query Design

## Filter Order
* **Category → Geography → Availability:** Apply the cheapest, most selective filter first — Category, then the geospatial radius check, then Provider Availability/verification status — to keep the candidate set small before any scoring logic runs.
* **Discoverability Gate:** Never return a Provider where `is_discoverable = false` (unapproved Freelancer, unclaimed-and-hidden listing) from a customer-facing match, regardless of geographic fit.

## Ranking
* **Merit, Not Distance Alone:** Final ranking combines proximity with `provider_rating_summaries` and review volume per `03_DOMAIN_MODEL.md` — distance is one input, not the sole sort key.
* **Deterministic Ties:** Break ranking ties deterministically (e.g. by `provider_id`) so repeated identical searches return stable ordering for testing and customer trust.
