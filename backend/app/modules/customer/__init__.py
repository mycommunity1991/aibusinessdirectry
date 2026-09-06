# Customer module (CUS-001).
#
# Covers the Customer profile/preferences domain: auto-provisioning a
# `customer_profiles`/`customer_preferences` row for every new Account
# (triggered by `identity.AuthService` on registration) and the
# `GET`/`PATCH /customers/me` self-service endpoints — see
# `docs/AI/02_ARCHITECTURE.md` "Core Business Modules" > "Customer".
