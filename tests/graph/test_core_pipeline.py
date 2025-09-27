import json
import uuid
from unittest.mock import MagicMock, patch

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
                "sender_name": "Test Sender",
                "sender_contact": "test@example.com",
                "receiver_name": "Test Receiver",
                "receiver_contact": "receiver@example.com",
                "subject": "Test Subject",
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
        key_info=None,
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
    assert final_state["key_info"] is not None
    assert final_state["key_info"]["sender_contact"] == "test@example.com"
    assert final_state["draft_history"] is not None
    assert len(final_state["draft_history"]) == 1
    assert final_state["draft_history"][0]["content"] == "This is a test draft."

    # 6. Verify that the LLM service was called correctly
    assert mocked_llm_service.invoke.call_count == 2


def test_refinement_pipeline_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for the M2 refinement pipeline.

    It verifies that the graph can correctly route user feedback to the
    refinement node and generate a new draft.
    """
    # 1. Arrange: Set up the mocked LLM service for a two-turn conversation
    from eassistant.graph import nodes

    nodes.llm_service = mocked_llm_service
    mocked_llm_service.invoke.side_effect = [
        json.dumps(
            {
                "sender_name": "Test Sender",
                "sender_contact": "test@example.com",
                "receiver_name": "Test Receiver",
                "receiver_contact": "receiver@example.com",
                "subject": "Test Subject",
                "summary": "This is a test summary.",
            }
        ),
        "This is the initial draft.",
        "This is the refined draft.",  # The third call is for refinement
    ]

    # 2. Build the graph
    app = build_graph()

    # 3. First turn: Generate the initial draft
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        original_email="A test email.",
        email_path=None,
        key_info=None,
        summary=None,
        draft_history=[],
        current_tone="professional",
        user_feedback=None,
        error_message=None,
    )
    first_turn_state = app.invoke(initial_state)

    # 4. Assert the state after the first turn
    assert first_turn_state["draft_history"] is not None
    assert len(first_turn_state["draft_history"]) == 1
    assert (
        first_turn_state["draft_history"][0]["content"] == "This is the initial draft."
    )

    # 5. Second turn: Provide feedback to refine the draft
    second_turn_input_state = first_turn_state.copy()
    second_turn_input_state["user_feedback"] = "Make it more formal."
    second_turn_state = app.invoke(second_turn_input_state)

    # 6. Assert the final state after refinement
    assert second_turn_state["draft_history"] is not None
    assert len(second_turn_state["draft_history"]) == 2
    assert (
        second_turn_state["draft_history"][1]["content"] == "This is the refined draft."
    )

    # 7. Verify that the LLM service was called three times
    assert mocked_llm_service.invoke.call_count == 3


def test_multi_email_session_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for handling multiple emails in a single session.

    It verifies that after completing a draft, the user can start a new email
    and the state is correctly managed.
    """
    # 1. Arrange: Set up the mocked LLM for two separate email flows
    from eassistant.graph import nodes

    nodes.llm_service = mocked_llm_service
    mocked_llm_service.invoke.side_effect = [
        # First email
        json.dumps({"summary": "First email summary."}),
        "First email draft.",
        # Second email
        json.dumps({"summary": "Second email summary."}),
        "Second email draft.",
    ]

    # 2. Build the graph
    app = build_graph()

    # 3. First email: Run the graph to completion
    first_email_state = GraphState(
        session_id=uuid.uuid4(),
        original_email="This is the first email.",
        draft_history=[],
        user_feedback=None,
    )
    final_state_first_email = app.invoke(first_email_state)

    # 4. Assert the state after the first email
    assert final_state_first_email["summary"] == "First email summary."
    assert len(final_state_first_email["draft_history"]) == 1
    assert (
        final_state_first_email["draft_history"][0]["content"] == "First email draft."
    )

    # 5. Second email: Simulate starting a new email by resetting the relevant state
    # In the CLI, this would be handled by the 'new' command logic.
    second_email_initial_state = final_state_first_email.copy()
    second_email_initial_state["original_email"] = "This is the second email."
    second_email_initial_state["draft_history"] = []
    second_email_initial_state["user_feedback"] = None
    second_email_initial_state["summary"] = None
    second_email_initial_state["key_info"] = None

    final_state_second_email = app.invoke(second_email_initial_state)

    # 6. Assert the state after the second email
    assert final_state_second_email["summary"] == "Second email summary."
    assert len(final_state_second_email["draft_history"]) == 1
    assert (
        final_state_second_email["draft_history"][0]["content"] == "Second email draft."
    )

    # 7. Verify the LLM was called for both emails
    assert mocked_llm_service.invoke.call_count == 4


def test_pdf_parsing_pipeline_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for the M2 PDF parsing pipeline.

    It verifies that the graph correctly identifies a PDF path, extracts text,
    and then proceeds with the standard pipeline.
    """
    # 1. Arrange: Mock the file system and PDF extraction
    with (
        patch("eassistant.graph.nodes.Path") as mock_path,
        patch("eassistant.graph.nodes.extract_text_from_pdf") as mock_extract,
    ):
        # Configure the mock Path object
        mock_path.return_value.is_file.return_value = True
        mock_path.return_value.suffix = ".pdf"
        mock_path.return_value.__str__.return_value = "dummy/test.pdf"

        # Configure the mock PDF extractor
        mock_extract.return_value = "This is the extracted PDF text."

        # 2. Replace the actual LLMService with our mock
        from eassistant.graph import nodes

        nodes.llm_service = mocked_llm_service

        # 3. Build the graph
        app = build_graph()

        # 4. Define the initial state with a path to a PDF
        initial_state = GraphState(
            session_id=uuid.uuid4(),
            original_email="dummy/test.pdf",  # Input is a file path
            email_path=None,
            key_info=None,
            summary=None,
            draft_history=[],
            current_tone=None,
            user_feedback=None,
            error_message=None,
        )

        # 5. Run the graph
        final_state = app.invoke(initial_state)

        # 6. Assert the final state
        assert final_state is not None
        # Verify the PDF text was used for the summary
        assert final_state["summary"] == "This is a test summary."
        assert final_state["email_path"] == "dummy/test.pdf"
        assert final_state["draft_history"] is not None
        assert len(final_state["draft_history"]) == 1
        assert final_state["draft_history"][0]["content"] == "This is a test draft."

        # 7. Verify mocks were called
        mock_path.assert_called_with("dummy/test.pdf")
        mock_extract.assert_called_with(mock_path.return_value)
        assert mocked_llm_service.invoke.call_count == 2
