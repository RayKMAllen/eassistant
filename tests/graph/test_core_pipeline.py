import json
import uuid
from unittest.mock import MagicMock

import pytest

from eassistant.graph.builder import build_graph
from eassistant.graph.state import GraphState
from eassistant.services.llm import LLMService


@pytest.fixture()  # type: ignore
def mocked_llm_service() -> MagicMock:
    """Fixture to create a mocked LLMService."""
    mock_service = MagicMock(spec=LLMService)
    mock_service.invoke.side_effect = [
        json.dumps(
            {
                "sender": "test@example.com",
                "subject": "Test Subject",
                "key_points": ["This is a key point."],
                "summary": "This is a test summary.",
            }
        ),
        "This is a test draft.",
    ]
    return mock_service


def test_core_pipeline_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for the M1 core pipeline.

    It verifies that the graph correctly processes a plain text email,
    extracts information, summarizes, and generates a draft using a mocked LLM.
    """
    # 1. Replace the actual LLMService with our mock
    from eassistant.graph import nodes

    nodes.llm_service = mocked_llm_service

    # 2. Build the graph
    app = build_graph()

    # 3. Define the initial state, providing all required fields
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        original_email=(
            "From: test@example.com\nSubject: Test Subject\n\nThis is a test email."
        ),
        email_path=None,
        extracted_entities=None,
        summary=None,
        draft_history=None,
        current_tone=None,
        user_feedback=None,
        error_message=None,
    )

    # 4. Run the graph
    final_state = app.invoke(initial_state)

    # 5. Assert the final state is as expected
    assert final_state is not None
    assert final_state["summary"] == "This is a test summary."
    assert final_state["extracted_entities"] is not None
    assert final_state["extracted_entities"]["sender"] == "test@example.com"
    assert final_state["draft_history"] is not None
    assert len(final_state["draft_history"]) == 1
    assert final_state["draft_history"][0]["content"] == "This is a test draft."

    # 6. Verify that the LLM service was called correctly
    assert mocked_llm_service.invoke.call_count == 2
