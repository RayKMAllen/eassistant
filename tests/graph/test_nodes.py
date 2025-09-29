import json
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from eassistant.graph.nodes import (
    ask_for_tone,
    extract_and_summarize,
    generate_initial_draft,
    handle_error,
    handle_idle_chat,
    handle_unclear,
    parse_input,
    refine_draft,
    reset_session,
    route_action,
    save_draft,
    show_info,
)
from eassistant.graph.state import GraphState


@pytest.mark.parametrize(
    (
        "user_input",
        "has_draft_history",
        "expected_intent",
        "expected_original_email",
        "expected_user_feedback",
    ),
    [
        (
            "This is a new email.",
            False,
            "process_new_email",
            "This is a new email.",
            None,
        ),
        ("Show me the info", True, "show_info", None, None),
        ("save the draft", True, "save_draft", None, None),
        ("make it better", True, "refine_draft", None, "make it better"),
        ("new", True, "reset_session", None, None),
        ("gibberish", False, "unclear", None, None),
        ("", False, "unclear", None, None),  # Empty input
        ("   ", False, "unclear", None, None),  # Whitespace input
    ],
)
def test_route_action(
    mocker: MockerFixture,
    user_input,
    has_draft_history,
    expected_intent,
    expected_original_email,
    expected_user_feedback,
) -> None:
    """
    Tests that the route_action node correctly classifies user input.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = json.dumps({"intent": expected_intent})

    initial_state: GraphState = {
        "user_input": user_input,
        "draft_history": [{"content": "A draft", "tone": "professional"}]
        if has_draft_history
        else [],
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = route_action(initial_state)

    # Assert
    assert result_state["intent"] == expected_intent
    assert result_state["original_email"] == expected_original_email
    assert result_state["user_feedback"] == expected_user_feedback


def test_route_action_handles_json_decode_error(mocker: MockerFixture) -> None:
    """
    Tests that route_action handles LLM responses that are not valid JSON.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = "not json"
    initial_state: GraphState = {
        "user_input": "some input",
        "draft_history": [],
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
        "conversation_summary": None,
    }

    # Act
    result_state = route_action(initial_state)

    # Assert
    assert result_state["intent"] == "unclear"
    assert "Error during intent routing" in result_state["error_message"]


def test_route_action_llm_exception(mocker: MockerFixture) -> None:
    """
    Tests that route_action handles exceptions from the LLM service.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    error_message = "LLM is down"
    mock_llm.invoke.side_effect = Exception(error_message)
    initial_state: GraphState = {
        "user_input": "some input",
        "draft_history": [],
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
        "conversation_summary": None,
    }

    # Act
    result_state = route_action(initial_state)

    # Assert
    assert result_state["intent"] == "unclear"
    assert error_message in result_state["error_message"]


def test_show_info_success(capsys) -> None:
    """
    Tests that show_info correctly displays the extracted information.
    """
    # Arrange
    initial_state: GraphState = {
        "key_info": {
            "sender_name": "John Doe",
            "sender_contact": "john@example.com",
            "receiver_name": "Jane Doe",
            "receiver_contact": "jane@example.com",
            "subject": "Test",
        },
        "summary": "This is a test summary.",
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": None,
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    show_info(initial_state)

    # Assert
    captured = capsys.readouterr()
    assert "-- Extracted Information --" in captured.out
    assert "John Doe" in captured.out
    assert "This is a test summary." in captured.out


def test_show_info_no_info(capsys) -> None:
    """
    Tests that show_info handles the case where no information is available.
    """
    # Arrange
    initial_state: GraphState = {
        "key_info": None,
        "summary": None,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": None,
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    show_info(initial_state)

    # Assert
    captured = capsys.readouterr()
    assert "No information extracted yet." in captured.out


def test_reset_session() -> None:
    """
    Tests that reset_session correctly clears the state.
    """
    # Arrange
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    initial_state: GraphState = {
        "session_id": session_id,
        "user_input": "new",
        "original_email": "some email",
        "summary": "a summary",
        "draft_history": [{"content": "a draft", "tone": "casual"}],
        "intent": "reset_session",
        "email_path": None,
        "key_info": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
    }

    # Act
    result_state = reset_session(initial_state)

    # Assert
    assert result_state["session_id"] == session_id
    assert result_state["original_email"] is None
    assert result_state["summary"] is None
    assert result_state["draft_history"] == []
    assert result_state["intent"] is None


def test_reset_session_no_session_id() -> None:
    """
    Tests that reset_session raises a ValueError if the session_id is missing.
    """
    # Arrange
    initial_state: GraphState = {
        "session_id": None,  # type: ignore
        "user_input": "new",
        "original_email": "some email",
        "summary": "a summary",
        "draft_history": [{"content": "a draft", "tone": "casual"}],
        "intent": "reset_session",
        "email_path": None,
        "key_info": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Session ID is missing"):
        reset_session(initial_state)


def test_handle_unclear(capsys) -> None:
    """
    Tests that handle_unclear prints the correct help message.
    """
    # Arrange
    initial_state: GraphState = {
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    handle_unclear(initial_state)

    # Assert
    captured = capsys.readouterr()
    assert "I'm not sure what you mean." in captured.out


def test_generate_initial_draft_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for the generate_initial_draft node.
    """
    # Arrange
    mock_draft_content = "This is the generated draft."
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = mock_draft_content

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {
            "sender_name": "Test Sender",
            "sender_contact": "sender@example.com",
            "receiver_name": "Test Receiver",
            "receiver_contact": "receiver@example.com",
            "subject": "Test Subject",
        },
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = generate_initial_draft(initial_state)

    # Assert
    assert result_state.get("error_message") is None
    draft_history = result_state.get("draft_history")
    assert draft_history is not None
    assert len(draft_history) == 1
    first_draft = draft_history[0]
    assert first_draft["content"] == mock_draft_content
    assert first_draft["tone"] == "professional"
    mock_llm.invoke.assert_called_once()


def test_extract_and_summarize_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for the extract_and_summarize node.
    """
    # Arrange
    mock_response = {
        "sender_name": "Test Sender",
        "sender_contact": "sender@example.com",
        "receiver_name": "Test Receiver",
        "receiver_contact": "receiver@example.com",
        "subject": "Test Subject",
        "summary": "This is a test summary.",
    }
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = json.dumps(mock_response)

    initial_state: GraphState = {
        "original_email": "This is a test email body.",
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = extract_and_summarize(initial_state)

    # Assert
    assert result_state.get("error_message") is None
    assert result_state.get("summary") == mock_response["summary"]
    key_info = result_state.get("key_info")
    assert key_info is not None
    assert key_info.get("sender_name") == mock_response["sender_name"]
    assert key_info.get("sender_contact") == mock_response["sender_contact"]
    assert key_info.get("receiver_name") == mock_response["receiver_name"]
    assert key_info.get("receiver_contact") == mock_response["receiver_contact"]
    assert key_info.get("subject") == mock_response["subject"]
    mock_llm.invoke.assert_called_once()


def test_extract_and_summarize_json_decode_error(mocker: MockerFixture) -> None:
    """
    Tests the case where the LLM returns a malformed JSON string.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = "this is not json"

    initial_state: GraphState = {
        "original_email": "This is a test email body.",
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = extract_and_summarize(initial_state)

    # Assert
    assert result_state.get("error_message") == "Failed to parse LLM response as JSON."
    assert result_state.get("summary") is None
    assert result_state.get("key_info") is None


def test_parse_input_with_text() -> None:
    """
    Tests that the parse_input node handles plain text correctly.
    """
    # Arrange
    initial_state: GraphState = {
        "original_email": "This is a test email.",
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["original_email"] == "This is a test email."
    assert result_state["email_path"] is None


def test_parse_input_with_pdf(mocker: MockerFixture, tmp_path) -> None:
    """
    Tests that the parse_input node correctly parses a PDF file.
    """
    # Arrange
    pdf_content = "This is text from a PDF."
    pdf_file = tmp_path / "test.pdf"
    # A simple way to create a dummy PDF for testing text extraction.
    # In a real scenario, you might use a library to create a valid PDF.
    # For this test, we mock the extraction function.
    mocker.patch(
        "eassistant.graph.nodes.extract_text_from_pdf", return_value=pdf_content
    )
    # We need the file to exist for `is_file()` to pass.
    pdf_file.touch()

    initial_state: GraphState = {
        "original_email": str(pdf_file),
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["original_email"] == pdf_content
    assert result_state["email_path"] == str(pdf_file)


def test_parse_input_with_non_pdf_file(tmp_path) -> None:
    """
    Tests that a non-PDF file is treated as plain text.
    """
    # Arrange
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is a text file.")

    initial_state: GraphState = {
        "original_email": str(txt_file),
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["original_email"] == str(txt_file)
    assert result_state["email_path"] is None


def test_parse_input_not_a_file_path() -> None:
    """
    Tests that a sentence with a period is not treated as a file path.
    """
    # Arrange
    input_text = "This is a sentence. It is not a file."
    initial_state: GraphState = {
        "original_email": input_text,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["original_email"] == input_text
    assert result_state["email_path"] is None


def test_parse_input_pdf_not_found(tmp_path) -> None:
    """
    Tests that parse_input handles a non-existent PDF file path.
    """
    # Arrange
    non_existent_file = tmp_path / "ghost.pdf"
    initial_state: GraphState = {
        "original_email": str(non_existent_file),
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert f"File not found: {non_existent_file}" in result_state["error_message"]


def test_refine_draft_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for the refine_draft node.
    """
    # Arrange
    mock_refined_content = "This is the refined draft."
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = mock_refined_content

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {
            "sender_name": "Test Sender",
            "sender_contact": "sender@example.com",
            "receiver_name": "Test Receiver",
            "receiver_contact": "receiver@example.com",
            "subject": "Test Subject",
        },
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [
            {"content": "This is the first draft.", "tone": "professional"}
        ],
        "current_tone": "professional",
        "user_feedback": "Make it more friendly.",
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = refine_draft(initial_state)

    # Assert
    assert result_state.get("error_message") is None
    draft_history = result_state.get("draft_history")
    assert draft_history is not None
    assert len(draft_history) == 2
    latest_draft = draft_history[-1]
    assert latest_draft["content"] == mock_refined_content
    assert latest_draft["tone"] == "professional"
    mock_llm.invoke.assert_called_once()


def test_save_draft_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for the save_draft node.
    """
    # Arrange
    mock_storage = mocker.patch("eassistant.graph.nodes.storage_service")
    initial_state: GraphState = {
        "draft_history": [
            {"content": "This is the first draft.", "tone": "professional"},
            {"content": "This is the final draft.", "tone": "friendly"},
        ],
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "friendly",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = save_draft(initial_state)

    # Assert
    assert result_state.get("error_message") is None
    mock_storage.save.assert_called_once()
    # Get the arguments passed to the mock
    args, kwargs = mock_storage.save.call_args
    assert kwargs.get("content") == "This is the final draft."
    file_path = kwargs.get("file_path")
    assert file_path is not None
    # Normalize path separators for OS-agnostic check
    normalized_path = file_path.replace("\\", "/")
    assert "outputs/draft-" in normalized_path
    assert ".txt" in normalized_path


def test_save_draft_no_history() -> None:
    """
    Tests that the save_draft node handles the case where there is no draft history.
    """
    # Arrange
    initial_state: GraphState = {
        "draft_history": [],
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = save_draft(initial_state)

    # Assert
    assert result_state.get("error_message") == "No draft to save."


def test_handle_error(capsys) -> None:
    """
    Tests that the handle_error node prints the error message from the state.
    """
    # Arrange
    error_message = "Something went wrong!"
    initial_state: GraphState = {
        "error_message": error_message,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "intent": None,
    }

    # Act
    result_state = handle_error(initial_state)

    # Assert
    captured = capsys.readouterr()
    assert f"An error occurred: {error_message}" in captured.out
    assert result_state.get("error_message") is None  # Error should be cleared


def test_parse_input_no_input() -> None:
    """
    Tests that parse_input handles the case where no input is provided.
    """
    # Arrange
    initial_state: GraphState = {
        "original_email": None,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["error_message"] == "Input email cannot be empty."


def test_parse_input_pdf_extraction_error(mocker: MockerFixture, tmp_path) -> None:
    """
    Tests that parse_input handles errors during PDF text extraction.
    """
    # Arrange
    pdf_file = tmp_path / "test.pdf"
    pdf_file.touch()
    error_message = "Failed to extract text"
    mocker.patch(
        "eassistant.graph.nodes.extract_text_from_pdf",
        side_effect=ValueError(error_message),
    )

    initial_state: GraphState = {
        "original_email": str(pdf_file),
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["error_message"] == error_message


def test_extract_and_summarize_llm_exception(mocker: MockerFixture) -> None:
    """
    Tests that extract_and_summarize handles exceptions from the LLM service.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    error_message = "LLM is down"
    mock_llm.invoke.side_effect = Exception(error_message)

    initial_state: GraphState = {
        "original_email": "Test email",
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = extract_and_summarize(initial_state)

    # Assert
    assert f"An unexpected error occurred: {error_message}" in str(
        result_state["error_message"]
    )


def test_extract_and_summarize_no_content() -> None:
    """
    Tests that extract_and_summarize handles the case where there is no email content.
    """
    # Arrange
    initial_state: GraphState = {
        "original_email": None,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = extract_and_summarize(initial_state)

    # Assert
    assert result_state["error_message"] == "No email content to process."


def test_generate_initial_draft_missing_data() -> None:
    """
    Tests that generate_initial_draft handles missing summary or key_info.
    """
    # Arrange
    initial_state: GraphState = {
        "summary": None,
        "key_info": None,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = generate_initial_draft(initial_state)

    # Assert
    assert (
        result_state["error_message"]
        == "Missing summary or entities to generate a draft."
    )


def test_generate_initial_draft_llm_exception(mocker: MockerFixture) -> None:
    """
    Tests that generate_initial_draft handles exceptions from the LLM service.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    error_message = "LLM is down"
    mock_llm.invoke.side_effect = Exception(error_message)

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {"sender_name": "Test"},
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = generate_initial_draft(initial_state)

    # Assert
    assert f"Failed to generate draft: {error_message}" in str(
        result_state["error_message"]
    )


def test_refine_draft_no_history() -> None:
    """
    Tests that refine_draft handles the case with no draft history.
    """
    # Arrange
    initial_state: GraphState = {
        "draft_history": [],
        "user_feedback": "Make it better.",
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = refine_draft(initial_state)

    # Assert
    assert result_state["error_message"] == "No draft to refine."


def test_refine_draft_no_feedback() -> None:
    """
    Tests that refine_draft handles the case with no user feedback.
    """
    # Arrange
    initial_state: GraphState = {
        "draft_history": [{"content": "A draft.", "tone": "professional"}],
        "user_feedback": None,
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = refine_draft(initial_state)

    # Assert
    assert (
        result_state["error_message"]
        == "No user feedback provided to refine the draft."
    )


def test_refine_draft_llm_exception(mocker: MockerFixture) -> None:
    """
    Tests that refine_draft handles exceptions from the LLM service.
    """
    # Arrange
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    error_message = "LLM is down"
    mock_llm.invoke.side_effect = Exception(error_message)

    initial_state: GraphState = {
        "draft_history": [{"content": "A draft.", "tone": "professional"}],
        "user_feedback": "Make it better.",
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = refine_draft(initial_state)

    # Assert
    assert f"Failed to refine draft: {error_message}" in str(
        result_state["error_message"]
    )


def test_save_draft_storage_exception(mocker: MockerFixture) -> None:
    """
    Tests that save_draft handles exceptions from the storage service.
    """
    # Arrange
    mock_storage = mocker.patch("eassistant.graph.nodes.storage_service")
    error_message = "Disk is full"
    mock_storage.save.side_effect = Exception(error_message)

    initial_state: GraphState = {
        "draft_history": [{"content": "A draft.", "tone": "professional"}],
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = save_draft(initial_state)

    # Assert
    assert f"Failed to save draft: {error_message}" in str(
        result_state["error_message"]
    )


def test_ask_for_tone_with_input(mocker: MockerFixture) -> None:
    """
    Tests that ask_for_tone correctly captures user input.
    """
    # Arrange
    mock_console = mocker.patch("eassistant.graph.nodes.console")
    mock_console.input.return_value = "casual"

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {"sender_name": "Test Sender"},
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": None,
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = ask_for_tone(initial_state)

    # Assert
    assert result_state["current_tone"] == "casual"
    mock_console.input.assert_called_once()


def test_ask_for_tone_no_input_defaults_to_professional(
    mocker: MockerFixture,
) -> None:
    """
    Tests that ask_for_tone defaults to 'professional' when no input is given.
    """
    # Arrange
    mock_console = mocker.patch("eassistant.graph.nodes.console")
    mock_console.input.return_value = ""  # Simulate user pressing Enter

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {"sender_name": "Test Sender"},
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": None,
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = ask_for_tone(initial_state)

    # Assert
    assert result_state["current_tone"] == "professional"


def test_ask_for_tone_user_cancellation(mocker: MockerFixture) -> None:
    """
    Tests that ask_for_tone handles user cancellation (e.g., Ctrl+C).
    """
    # Arrange
    mock_console = mocker.patch("eassistant.graph.nodes.console")
    mock_console.input.side_effect = KeyboardInterrupt

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {"sender_name": "Test Sender"},
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": None,
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    result_state = ask_for_tone(initial_state)

    # Assert
    assert result_state["current_tone"] == "professional"  # Defaults on cancel
    assert result_state["error_message"] == "User cancelled the operation."


def test_ask_for_tone_displays_contact_details(mocker: MockerFixture, capsys) -> None:
    """
    Tests that ask_for_tone correctly displays all key info, including contacts.
    """
    # Arrange
    mock_console = mocker.patch("eassistant.graph.nodes.console")
    mock_console.input.return_value = "casual"

    initial_state: GraphState = {
        "summary": "A test summary.",
        "key_info": {
            "sender_name": "John Doe",
            "sender_contact": "john@example.com",
            "receiver_name": "Jane Doe",
            "receiver_contact": "jane@example.com",
            "subject": "Important Update",
        },
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": None,
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": None,
        "user_feedback": None,
        "error_message": None,
        "intent": None,
    }

    # Act
    ask_for_tone(initial_state)

    # Assert
    # We inspect the arguments passed to rich.console.print
    # to see what would have been rendered.
    print_calls = mock_console.print.call_args_list
    assert len(print_calls) > 0

    # The first call should be the Panel with the extracted info
    info_panel = print_calls[0].args[0]

    # Convert the renderable to a string to check its content
    captured_output = str(info_panel.renderable)
    assert "Sender:" in captured_output
    assert "John Doe" in captured_output
    assert "john@example.com" in captured_output
    assert "Recipient:" in captured_output
    assert "Jane Doe" in captured_output
    assert "jane@example.com" in captured_output
    assert "Subject:" in captured_output
    assert "Important Update" in captured_output


def test_handle_idle_chat(capsys) -> None:
    """
    Tests that handle_idle_chat prints a simple conversational response.
    """
    # Arrange
    initial_state: GraphState = {
        "session_id": UUID("11111111-1111-1111-1111-111111111111"),
        "user_input": "hello",
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": "handle_idle_chat",
    }

    # Act
    handle_idle_chat(initial_state)

    # Assert
    captured = capsys.readouterr()
    assert "Hello! How can I help you with your email?" in captured.out
