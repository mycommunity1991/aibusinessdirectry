# Rule: Notification Channels (WhatsApp / SMS / Email)

## Delivery
* **Async Dispatch:** Notification sends must never block the triggering request (new lead, verification status change) — dispatch via a background task and record the outcome in `notification_delivery`.
* **Idempotent Sends:** Include an idempotency key per notification attempt so a retried background job cannot double-send the same WhatsApp/SMS message to a Customer or Provider.

## Preference Enforcement
* **Preferences Are Binding:** Check `notification_preferences` (channel + per-category toggles) before every send — a disabled channel or muted category is a hard stop, not a soft suggestion.
* **PII in Payloads:** Notification bodies must not leak more PII than the receiving channel needs (e.g. don't put a full phone number in a push notification title).
