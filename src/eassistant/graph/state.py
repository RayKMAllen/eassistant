from typing import List, Optional, TypedDict
from uuid import UUID


class ExtractedEntities(TypedDict):
    """Structured information extracted from an email."""

    sender_name: Optional[str]
    sender_contact: Optional[str]
    receiver_name: Optional[str]
    receiver_contact: Optional[str]
    subject: Optional[str]


class Draft(TypedDict):
    """A single draft of a reply."""

    content: str
    tone: str


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    This TypedDict is the central data structure that flows between nodes in the
    LangGraph state machine. It accumulates information as the process progresses.
    """

    session_id: UUID
    user_input: Optional[str]  # Raw user input from the CLI
    intent: Optional[str]  # Classified intent of the user
    original_email: Optional[str]
    email_path: Optional[str]
    key_info: Optional[ExtractedEntities]
    summary: Optional[str]
    draft_history: Optional[List[Draft]]
    current_tone: Optional[str]
    user_feedback: Optional[str]
    error_message: Optional[str]
    save_target: Optional[str]  # e.g., 'local', 's3'
    # A running summary of the conversation for context-aware routing.
    conversation_summary: Optional[str]
