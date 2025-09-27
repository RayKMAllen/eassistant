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
        "extracted_entities": {
            "sender": "test@example.com",
            "subject": "Test Subject",
            "key_points": ["point 1", "point 2"],
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
        "sender": "test@example.com",
        "subject": "Test Subject",
        "key_points": ["point 1", "point 2"],
        "summary": "This is a test summary.",
    }
    mock_llm = mocker.patch("eassistant.graph.nodes.llm_service")
    mock_llm.invoke.return_value = json.dumps(mock_response)

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
