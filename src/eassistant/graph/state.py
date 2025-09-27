from typing import List, Optional, TypedDict
from uuid import UUID


class ExtractedEntities(TypedDict):
    """Structured information extracted from an email."""

    sender: Optional[str]
    subject: Optional[str]
    key_points: List[str]


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
    original_email: Optional[str]
    email_path: Optional[str]
    extracted_entities: Optional[ExtractedEntities]
    summary: Optional[str]
    draft_history: Optional[List[Draft]]
    current_tone: Optional[str]
    user_feedback: Optional[str]
    error_message: Optional[str]
