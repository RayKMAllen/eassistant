# ADR 001: State-Aware Conversational Routing

**Date**: 2023-10-27

**Status**: Proposed

## Context

The initial architecture of the conversational assistant uses a single LangGraph node, `route_user_intent`, as its entry point. This node uses an LLM call to classify the user's intent based on their raw input and a minimal check for the existence of a draft.

This design has proven to be inflexible and error-prone. It fails to handle different conversational contexts correctly because the LLM is not provided with sufficient context about the state of the conversation. For example, it may misinterpret a request to load a new file as feedback on an existing draft.

The core problem is that the routing decision is **stateless** and lacks true **context awareness**.

## Decision

We will evolve the routing mechanism to be **context-aware**, retaining the LLM's ability to understand natural language while providing it with a rich, dynamic context to ensure accurate decisions. The `route_user_intent` node will be replaced by a more intelligent `route_action` node.

1.  **Rich Context Construction**: The `route_action` node will be responsible for dynamically constructing a comprehensive context summary to send to the LLM. This context will include:
    *   A concise summary of the recent user-assistant conversation turns.
    *   The full content of the most recent draft, if one exists.
    *   Other key state variables that might influence the user's intent (e.g., the current `tone`).

2.  **Context-Steered Prompting**: The prompt will instruct the LLM to act as a "conversational router," using the provided rich context to select the most appropriate action from a list of state-dependent valid actions.

3.  **New `conversation_summary` State Field**: To support this, a `conversation_summary: Optional[str]` field will be added to the `GraphState`. This field will be managed by the graph to maintain a running summary of the interaction.

4.  **`handle_idle_chat` Node**: A new node will be added to gracefully handle conversational filler, preventing the system from unnecessarily triggering the full email processing pipeline.

This "context-steered" approach empowers the LLM to make a much more accurate, flexible, and truly conversational routing decision.

## Consequences

### Positive

-   **Greatly Increased Accuracy**: By providing a rich summary of the conversation and state, the LLM can make highly accurate, context-aware routing decisions, virtually eliminating the identified failure modes.
-   **Enhanced Conversational Flow**: The user experience will be significantly more natural and robust, as the assistant will understand nuanced requests and context shifts.
-   **Maintained Flexibility**: We retain the LLM's strength in understanding natural language, avoiding the brittleness of rigid, keyword-based systems.

### Negative

-   **Increased Complexity**: The logic for managing and summarizing the conversation history within the `route_action` node is more complex than the original static prompt.
-   **Marginal Latency/Cost Increase**: The prompt sent to the LLM will be larger due to the added context. This may marginally increase latency and token cost per turn, but this is a necessary trade-off for the significant gain in accuracy.

This decision refines the architecture to provide the routing LLM with the comprehensive state and history needed for intelligent, context-aware, and truly conversational user interaction.