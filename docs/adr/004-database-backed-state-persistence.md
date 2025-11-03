# ADR-004: Database-Backed State Persistence

**Status:** Accepted

**Date:** 2025-11-03

**Supersedes:** [ADR-002: Conversational Storage Target](002-conversational-storage-target.md)

---

## Context

The initial architecture for the Conversational Email Assistant was designed to be stateless, with the full `GraphState` held in memory for the duration of a single API request. While this is simple for a proof-of-concept, it has critical limitations for a real-world conversational application:
1.  **No Session Continuity:** Each request is isolated. A user cannot continue a conversation across multiple interactions.
2.  **No Auditability:** There is no record of past conversations, messages, or generated drafts.
3.  **Scalability Issues:** The in-memory approach does not scale beyond a single, ephemeral instance.

The [Chatbot Architecture Refactor Summary](../Chatbot_Architecture_Refactor_Summary.md) identified these gaps and recommended a pivot to a more traditional, database-centric chatbot architecture.

---

## Decision

We will adopt a persistent, database-backed architecture for managing all structured conversational data.

1.  **Introduce a Relational Database:** A database (SQLite for local development, PostgreSQL for production) will be added as a core component of the architecture.
2.  **Centralize State:** The database will be the single source of truth for:
    -   `users`
    -   `sessions`
    -   `messages` (user and assistant)
    -   `graph_state` (the serialized state of the LangGraph machine for each session)
3.  **Stateless Orchestrator:** The LangGraph orchestrator itself will remain stateless. On each API request, the system will:
    a. Load the relevant session and its latest `graph_state` from the database.
    b. Execute the graph for a single turn.
    c. Save the updated `graph_state` and any new messages back to the database.
4.  **S3 for Artifacts Only:** S3 storage will be used exclusively for storing large, unstructured data (e.g., email drafts, file attachments). Metadata about these artifacts will be stored in the database and linked to the relevant session or message.

---

## Consequences

### Positive:
-   **Enables Session Continuity:** Users can have multi-turn conversations that persist over time.
-   **Improves Observability & Auditability:** All interactions are logged in a structured, queryable format.
-   **Provides a Foundation for Future Features:** This architecture supports future development of analytics, multi-user support, and retrieval-augmented generation (RAG).
-   **Aligns with Industry Standards:** The proposed architecture is a standard, well-understood pattern for building scalable chatbots.

### Negative:
-   **Increased Complexity:** Introduces a new database service and requires more complex state management logic in the API layer.
-   **Requires Data Modeling:** A clear database schema must be designed and maintained.
-   **Introduces a New Dependency:** The application now depends on a running database instance.

This decision makes the initial setup more complex but provides a much more robust and scalable foundation for the project's long-term goals.