# Business domain modules package (Clean Architecture / Modular Monolith).
#
# Each subpackage is an independent business module following the
# `api/services/repositories/schemas/models/dependencies/events` layout
# documented in `docs/AI/02_ARCHITECTURE.md` ("Backend Architecture").
# Modules must communicate only through each other's services — never
# through another module's repositories (see "Communication Rules").
