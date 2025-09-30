# ADR-002: Conversational Storage Target Extraction

*   **Status**: Accepted
*   **Date**: 2025-09-29

## Context and Problem Statement

User commands like "save to cloud" or "save to s3" are not being correctly interpreted. Instead of saving to the specified cloud storage (S3), the system defaults to saving the draft locally. The initial implementation did not account for extracting the storage target conversationally.

## Options Considered

1.  **Keyword Matching**: Implement a simple keyword search in the `save_draft` node. This is brittle and goes against the project's conversational architecture.
2.  **Enhance Conversational Router**: Improve the `route_action` node's LLM prompt and data extraction model to recognize and extract the desired storage target (e.g., 'local', 's3') from the user's natural language command.

## Decision

We will enhance the conversational router (`route_action`). This aligns with our core architectural principle (ADR-001) of using a state-aware LLM for intent classification.

## Rationale

This approach is more robust and scalable. It keeps all intent-parsing logic centralized in the `route_action` node, rather than scattering it across different nodes. It treats the storage target as another piece of data to be extracted from the user's intent, just like `user_feedback` or `original_email`.

## Consequences

### Affected Components

*   `eassistant.graph.nodes.route_action`: The LLM prompt and the Pydantic model it populates will be updated to include an optional `save_target` field.
*   `eassistant.graph.state.GraphState`: The state will be updated to hold the `save_target`.
*   `eassistant.graph.nodes.save_draft`: This node will be updated to read the `save_target` from the state and pass it to the storage service.
*   `eassistant.services.storage.StorageService`: The service's `save` method will be updated to accept a target parameter.
*   `tests/`: New tests are required to verify the conversational extraction and correct routing to the storage service.

### Affected Milestones

*   A new milestone `M7` will be created.
*   Task `M6.2` ("Ensure 100% of tests are passing") will be blocked by `M7`.