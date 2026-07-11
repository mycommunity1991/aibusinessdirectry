# Clean Architecture

## Overview
Clean Architecture (championed by Robert C. Martin) is our standard for structuring backend services. Its primary goal is the separation of concerns, ensuring that business logic is completely isolated from delivery mechanisms (UI/API) and tools (Databases/Message Brokers).

## The Dependency Rule
**Source code dependencies must point only inward, toward higher-level policies.** Nothing in an inner circle can know anything at all about something in an outer circle. This includes variables, classes, functions, and frameworks.

## The Layers (From Inside Out)

### 1. Domain Layer (Enterprise Business Rules)
* **Contents:** Entities, Value Objects, Domain Events, Domain Exceptions.
* **Rules:** Encapsulates the most general and high-level business rules. This layer relies on absolutely zero external frameworks or libraries (except the core language standard library).

### 2. Application Layer (Application Business Rules)
* **Contents:** Use Cases (Interactors), Application Services, Data Transfer Objects (DTOs), Port Interfaces (Repository Interfaces, External Service Interfaces).
* **Rules:** Orchestrates the flow of data to and from the domain entities. It directs those entities to use their domain logic to achieve the goal of the use case. It knows nothing about HTTP or the SQL database.

### 3. Interface Adapters (Controllers, Presenters, Gateways)
* **Contents:** REST Controllers, gRPC Handlers, ViewModels, Repository Implementations.
* **Rules:** Converts data from the format most convenient for the use cases (DTOs) into the format most convenient for external agencies (e.g., JSON for web, table structures for DB).

### 4. Infrastructure & Frameworks (External Interfaces)
* **Contents:** Database engines, Web frameworks (e.g., Spring, Express, FastAPI), external API clients.
* **Rules:** Where all the details go. We keep these things on the outside where they can do little harm.

## Key Benefits & Verification
When reviewing a PR for Clean Architecture adherence, verify the following:
1.  **Testability:** Can the business rules (Use Cases and Entities) be tested entirely without the UI, Database, Web Server, or any other external element?
2.  **UI Independence:** Can the web API be swapped for a CLI or a message queue listener without changing a single line of business logic?
3.  **Database Independence:** Can you swap PostgreSQL for MongoDB, or a mock in-memory database, without the Domain or Application layers noticing?