from typing import NotRequired, TypedDict


class GraphState(TypedDict):
    """Represents the state of our graph."""

    user_input: NotRequired[str]
    result: NotRequired[str]
