from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from eassistant.graph.builder import build_graph

app = FastAPI()

assistant = build_graph()


class InvokeRequest(BaseModel):
    """Request model for the invoke endpoint."""

    user_input: str
    session_id: str | None = None


class InvokeResponse(BaseModel):
    """Response model for the invoke endpoint."""

    output: dict[str, Any]


@app.get("/healthz")  # type: ignore[misc]
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke")  # type: ignore[misc]
def invoke(request: InvokeRequest) -> InvokeResponse:
    """Invokes the assistant with the given input."""
    config = {"configurable": {"session_id": request.session_id}}
    output = assistant.invoke({"user_input": request.user_input}, config=config)
    return InvokeResponse(output=output)
