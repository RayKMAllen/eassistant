import json
from uuid import UUID

from pytest_mock import MockerFixture

from eassistant.graph.nodes import (
    extract_and_summarize,
    generate_initial_draft,
    handle_error,
    parse_input,
    refine_draft,
    save_draft,
)
from eassistant.graph.state import GraphState


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
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
    }

    # Act
    result_state = parse_input(initial_state)

    # Assert
    assert result_state["original_email"] == pdf_content
    assert result_state["email_path"] == str(pdf_file)


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
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [
            {"content": "This is the first draft.", "tone": "professional"}
        ],
        "current_tone": "professional",
        "user_feedback": "Make it more friendly.",
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "friendly",
        "user_feedback": None,
        "error_message": None,
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
        "original_email": "",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "original_email": "",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "error_message": None,
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
        "original_email": "Test email",
        "email_path": None,
        "key_info": None,
        "summary": None,
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
    }

    # Act
    result_state = save_draft(initial_state)

    # Assert
    assert f"Failed to save draft: {error_message}" in str(
        result_state["error_message"]
    )
