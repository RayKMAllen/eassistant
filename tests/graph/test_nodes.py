import json
from unittest.mock import MagicMock
from uuid import UUID

from pytest_mock import MockerFixture

from eassistant.graph.nodes import extract_and_summarize
from eassistant.graph.state import GraphState


def test_extract_and_summarize_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for the extract_and_summarize node.
    """
    # Arrange
    mock_llm_service = MagicMock()
    mock_response = {
        "sender": "test@example.com",
        "subject": "Test Subject",
        "key_points": ["point 1", "point 2"],
        "summary": "This is a test summary.",
    }
    mock_llm_service.invoke_claude.return_value = json.dumps(mock_response)
    mocker.patch("eassistant.graph.nodes.LLMService", return_value=mock_llm_service)

    initial_state: GraphState = {
        "original_email": "This is a test email body.",
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "email_path": None,
        "extracted_entities": None,
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
    extracted_entities = result_state.get("extracted_entities")
    assert extracted_entities is not None
    assert extracted_entities.get("sender") == mock_response["sender"]
    assert extracted_entities.get("subject") == mock_response["subject"]
    assert extracted_entities.get("key_points") == mock_response["key_points"]
    mock_llm_service.invoke_claude.assert_called_once()


def test_extract_and_summarize_json_decode_error(mocker: MockerFixture) -> None:
    """
    Tests the case where the LLM returns a malformed JSON string.
    """
    # Arrange
    mock_llm_service = MagicMock()
    mock_llm_service.invoke_claude.return_value = "this is not json"
    mocker.patch("eassistant.graph.nodes.LLMService", return_value=mock_llm_service)

    initial_state: GraphState = {
        "original_email": "This is a test email body.",
        "session_id": UUID("12345678-1234-5678-1234-567812345678"),
        "email_path": None,
        "extracted_entities": None,
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
    assert result_state.get("extracted_entities") is None
