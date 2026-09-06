# Audit module (AUTH-004).
#
# Cross-cutting audit-event recording, backing `audit.audit_logs` — see
# `docs/AI/02_ARCHITECTURE.md` "Core Business Modules" and
# `docs/AI/04_DATABASE.md` "Audit Domain". Other modules (currently
# `identity`) depend on this module's `AuditService`, never its
# repository directly, per the "modules communicate through services
# only" rule.
