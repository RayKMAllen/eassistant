from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from eassistant.graph.builder import build_graph

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
    draft_history: list[str] = []


@app.get("/healthz")  # type: ignore[misc]
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke")  # type: ignore[misc]
def invoke(request: InvokeRequest) -> InvokeResponse:
    """Invokes the assistant with the given input."""
    config = {"configurable": {"session_id": request.session_id}}
    output = assistant.invoke({"user_input": request.user_input}, config=config)
    return InvokeResponse(output=output, draft_history=output.get("draft_history", []))
