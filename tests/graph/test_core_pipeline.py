import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from eassistant.graph.builder import build_graph
from eassistant.graph.state import GraphState
from eassistant.services.llm import LLMService


@pytest.fixture()  # type: ignore
def mocked_llm_service() -> MagicMock:
    """Fixture to create a mocked LLMService with no default behaviors."""
    return MagicMock(spec=LLMService)


def mocked_ask_for_tone(state: GraphState) -> GraphState:
    """A mock version of ask_for_tone that bypasses user input."""
    state["current_tone"] = "professional"
    return state


def test_core_pipeline_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for the M1 core pipeline.

    It verifies that the graph correctly processes a plain text email,
    extracts information, summarizes, and generates a draft using a mocked LLM.
    """
    # 1. Replace the actual LLMService with our mock
    from eassistant.graph import builder, nodes

    mocked_llm_service.invoke.side_effect = [
        json.dumps({"intent": "process_new_email"}),  # 1. route_action
        json.dumps(  # 2. extract_and_summarize
            {
                "sender_name": "Test Sender",
                "sender_contact": "test@example.com",
                "receiver_name": "Test Receiver",
                "receiver_contact": "receiver@example.com",
                "subject": "Test Subject",
                "summary": "This is a test summary.",
            }
        ),
        "This is a test draft.",  # 3. generate_initial_draft
    ]
    nodes.llm_service = mocked_llm_service
    builder.ask_for_tone = mocked_ask_for_tone

    # 2. Build the graph
    app = build_graph()

    # 3. Define the initial state
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input=(
            "From: test@example.com\nSubject: Test Subject\n\nThis is a test email."
        ),
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
    assert mocked_llm_service.invoke.call_count == 3


def test_refinement_pipeline_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for the M2 refinement pipeline.

    It verifies that the graph can correctly route user feedback to the
    refinement node and generate a new draft.
    """
    # 1. Arrange: Set up the mocked LLM service for a two-turn conversation
    from eassistant.graph import builder, nodes

    nodes.llm_service = mocked_llm_service
    builder.ask_for_tone = mocked_ask_for_tone
    mocked_llm_service.invoke.side_effect = [
        json.dumps({"intent": "process_new_email"}),  # 1. route (initial)
        json.dumps(  # 2. extract
            {
                "sender_name": "Test Sender",
                "sender_contact": "test@example.com",
                "receiver_name": "Test Receiver",
                "receiver_contact": "receiver@example.com",
                "subject": "Test Subject",
                "summary": "This is a test summary.",
            }
        ),
        "This is the initial draft.",  # 3. generate
        json.dumps({"intent": "refine_draft"}),  # 4. route (refine)
        "This is the refined draft.",  # 5. refine
    ]

    # 2. Build the graph
    app = build_graph()

    # 3. First turn: Generate the initial draft
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="A test email.",
    )
    first_turn_state = app.invoke(initial_state)

    # 4. Assert the state after the first turn
    assert first_turn_state["draft_history"] is not None
    assert len(first_turn_state["draft_history"]) == 1
    assert (
        first_turn_state["draft_history"][0]["content"] == "This is the initial draft."
    )

    # 5. Second turn: Provide feedback to refine the draft
    # 5. Second turn: Provide feedback to refine the draft
    # The user's raw input goes into the 'user_input' field
    second_turn_input_state = first_turn_state.copy()
    second_turn_input_state["user_input"] = "Make it more formal."
    second_turn_state = app.invoke(second_turn_input_state)

    # 6. Assert the final state after refinement
    assert second_turn_state["draft_history"] is not None
    assert len(second_turn_state["draft_history"]) == 2
    assert (
        second_turn_state["draft_history"][1]["content"] == "This is the refined draft."
    )

    # 7. Verify that the LLM service was called three times
    assert mocked_llm_service.invoke.call_count == 5


def test_multi_email_session_integration(mocked_llm_service: MagicMock) -> None:
    """
    Integration test for handling multiple emails in a single session.

    It verifies that after completing a draft, the user can start a new email
    and the state is correctly managed.
    """
    # 1. Arrange: Set up the mocked LLM for two separate email flows
    from eassistant.graph import builder, nodes

    nodes.llm_service = mocked_llm_service
    builder.ask_for_tone = mocked_ask_for_tone
    mocked_llm_service.invoke.side_effect = [
        # First email flow
        json.dumps({"intent": "process_new_email"}),
        json.dumps(
            {
                "summary": "First email summary.",
                "sender_name": "User1",
                "receiver_name": "Support",
                "subject": "Query",
            }
        ),
        "First email draft.",
        # Second email flow
        json.dumps({"intent": "process_new_email"}),
        json.dumps(
            {
                "summary": "Second email summary.",
                "sender_name": "User2",
                "receiver_name": "Sales",
                "subject": "Inquiry",
            }
        ),
        "Second email draft.",
    ]

    # 2. Build the graph
    app = build_graph()

    # 3. First email: Run the graph to completion
    first_email_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="This is the first email.",
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
    second_email_initial_state["user_input"] = "This is the second email."
    # Reset fields as if starting a new conversation
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
    assert mocked_llm_service.invoke.call_count == 6


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
        from eassistant.graph import builder, nodes

        mocked_llm_service.invoke.side_effect = [
            json.dumps({"intent": "process_new_email"}),
            json.dumps({"summary": "This is a test summary."}),
            "This is a test draft.",
        ]
        nodes.llm_service = mocked_llm_service
        builder.ask_for_tone = mocked_ask_for_tone

        # 3. Build the graph
        app = build_graph()

        # 4. Define the initial state with a path to a PDF
        initial_state = GraphState(
            session_id=uuid.uuid4(),
            user_input="dummy/test.pdf",  # Input is a file path
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
        assert mocked_llm_service.invoke.call_count == 3


def test_error_handling_integration(capsys) -> None:
    """
    Integration test for the M3 error handling pipeline.

    It verifies that if a node raises an exception, the graph routes
    to the handle_error node and terminates gracefully.
    """
    # 1. Arrange: Mock the LLM service to raise an exception
    from eassistant.graph import nodes

    mock_llm = MagicMock(spec=LLMService)
    error_message = "LLM is down!"
    # The first call to the router should succeed, but the second
    # to the extractor should fail
    mock_llm.invoke.side_effect = [
        json.dumps({"intent": "process_new_email"}),
        Exception(error_message),
    ]
    nodes.llm_service = mock_llm

    # 2. Build the graph
    app = build_graph()

    # 3. Define the initial state
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="A test email that will cause a failure.",
    )

    # 4. Run the graph
    final_state = app.invoke(initial_state)

    # 5. Assert the final state and output
    assert final_state is not None
    # The error message should be cleared by the handle_error node
    assert final_state.get("error_message") is None

    # 6. Verify that the error message was printed to the console
    captured = capsys.readouterr()
    # The error is caught in extract_and_summarize and wrapped
    expected_output = "An error occurred: An unexpected error occurred: LLM is down!"
    assert expected_output in captured.out
    # Verify the LLM was called twice (router succeeded, extractor failed)
    assert mock_llm.invoke.call_count == 2


def test_invalid_file_path_error_handling(capsys) -> None:
    """
    Tests that the graph correctly handles a path to a non-existent file.
    """
    # 1. Arrange: Mock the Path object to indicate the file doesn't exist
    with patch("eassistant.graph.nodes.Path") as mock_path:
        mock_path.return_value.is_file.return_value = False
        mock_path.return_value.suffix = ".pdf"
        # Also need to mock the __str__ to ensure the error message is correct
        mock_path.return_value.__str__.return_value = "nonexistent/file.pdf"

        # This test does not mock the LLM, but the router node still needs to run.
        # We need a mock LLM that can be called by the router.
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.invoke.return_value = json.dumps({"intent": "process_new_email"})
        from eassistant.graph import nodes

        nodes.llm_service = mock_llm

        # 2. Build the graph
        app = build_graph()

        # 3. Define initial state with the invalid path
        initial_state = GraphState(
            session_id=uuid.uuid4(),
            user_input="nonexistent/file.pdf",
        )

        # 4. Run the graph
        final_state = app.invoke(initial_state)

        # 5. Assert that the error was caught and handled
        assert final_state is not None
        assert final_state.get("error_message") is None  # Error is handled and cleared

        captured = capsys.readouterr()
        expected_output = "An error occurred: File not found: nonexistent/file.pdf"
        assert expected_output in captured.out


def test_malformed_llm_json_response_error_handling(
    mocked_llm_service: MagicMock, capsys
) -> None:
    """
    Tests that the graph handles a malformed JSON response from the LLM.
    """
    # 1. Arrange: Set up the mock to return a non-JSON string
    from eassistant.graph import nodes

    # First call (router) is OK, second call (extractor) is malformed.
    mocked_llm_service.invoke.side_effect = [
        json.dumps({"intent": "process_new_email"}),
        "This is not valid JSON.",
    ]
    nodes.llm_service = mocked_llm_service

    # 2. Build the graph
    app = build_graph()

    # 3. Define initial state
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="A test email.",
    )

    # 4. Run the graph
    final_state = app.invoke(initial_state)

    # 5. Assert that the error was caught and handled
    assert final_state is not None
    assert final_state.get("error_message") is None

    captured = capsys.readouterr()
    assert "Failed to parse LLM response as JSON" in captured.out


def test_empty_user_input_is_handled(capsys) -> None:
    """
    Tests that the graph handles empty or whitespace-only user input gracefully.
    """
    # 1. Arrange: No LLM mocking is needed as the router should handle this.
    app = build_graph()

    # 2. Define initial state with empty input
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="   ",  # Whitespace only
    )

    # 3. Run the graph
    final_state = app.invoke(initial_state)

    # 4. Assert that the intent was classified as 'unclear'
    assert final_state is not None
    assert final_state.get("intent") == "unclear"

    # 5. Verify the user is prompted appropriately
    captured = capsys.readouterr()
    assert "I'm not sure what you mean." in captured.out


def test_idle_chat_pipeline_integration(mocked_llm_service: MagicMock, capsys) -> None:
    """
    Integration test for the idle chat scenario.

    Verifies that the graph correctly routes conversational filler to the
    `handle_idle_chat` node and that no other part of the pipeline is triggered.
    """
    # 1. Arrange: Mock the LLM service to return the 'handle_idle_chat' intent
    from eassistant.graph import nodes

    mocked_llm_service.invoke.return_value = json.dumps({"intent": "handle_idle_chat"})
    nodes.llm_service = mocked_llm_service

    # 2. Build the graph
    app = build_graph()

    # 3. Define the initial state
    initial_state = GraphState(
        session_id=uuid.uuid4(),
        user_input="Hey, how are you?",
    )

    # 4. Run the graph
    final_state = app.invoke(initial_state)

    # 5. Assert the final state and output
    assert final_state is not None
    # The intent should be set correctly
    assert final_state.get("intent") == "handle_idle_chat"
    # No other state should have changed (no summary, no draft)
    assert final_state.get("summary") is None
    assert not final_state.get("draft_history")

    # 6. Verify the user gets a conversational response
    captured = capsys.readouterr()
    assert "Hello! How can I help you with your email?" in captured.out

    # 7. Verify that the LLM was only called once (for routing)
    mocked_llm_service.invoke.assert_called_once()
