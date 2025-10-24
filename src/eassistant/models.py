from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal[
    "process_new_email",
    "refine_draft",
    "show_info",
    "save_draft",
    "reset_session",
    "handle_idle_chat",
    "unclear",
]

SaveTarget = Literal["local", "s3"]


class RouteActionOutput(BaseModel):
    """
    Defines the structured output for the route_action node.
    """

    intent: Intent = Field(..., description="The classified intent of the user.")
    save_target: Optional[SaveTarget] = Field(
        None,
        description="The target location for saving a draft, if specified.",
    )


class Draft(BaseModel):
    """A single draft of a reply."""

    content: str
    tone: str
