import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from eassistant.graph.builder import build_graph
from eassistant.models import Draft

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Add CORS middleware to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity in this context
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = build_graph()


class InvokeRequest(BaseModel):
    """Request model for the invoke endpoint."""

    user_input: str
    session_id: str | None = None


class InvokeResponse(BaseModel):
    """Response model for the invoke endpoint."""

    output: dict[str, Any]
    draft_history: list[Draft] = []


@app.get("/healthz")  # type: ignore[misc]
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke")  # type: ignore[misc]
def invoke(request: InvokeRequest) -> InvokeResponse:
    """Invokes the assistant with the given input."""
    config = {"configurable": {"session_id": request.session_id}}
    final_state = {}
    # The stream yields events, each being a dict like {'node_name': state}.
    # We iterate through the stream and keep the state from the last event.
    for event in assistant.stream({"user_input": request.user_input}, config=config):
        # The event dictionary has one key: the name of the node that just ran.
        # The value is the current state of the graph.
        current_state = list(event.values())[0]
        if isinstance(current_state, dict):
            final_state = current_state

    return InvokeResponse(
        output=final_state, draft_history=final_state.get("draft_history", [])
    )
