import json
from uuid import UUID

from pytest_mock import MockerFixture

from eassistant.graph.nodes import extract_and_summarize, generate_initial_draft
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
