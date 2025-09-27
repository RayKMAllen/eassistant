import json
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from eassistant.services.llm import LLMService


def test_llm_service_invoke_success(mocker: MockerFixture) -> None:
    """
    Tests that the LLMService can successfully invoke the Bedrock model
    and parse a valid response.
    """
    # Arrange
    mock_boto_client = MagicMock()
    mocker.patch("boto3.client", return_value=mock_boto_client)

    prompt = "Hello, world!"
    expected_response_text = "This is the LLM's answer."
    mock_response_body = {"content": [{"type": "text", "text": expected_response_text}]}
    mock_response = {
        "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode("utf-8"))
    }
    mock_boto_client.invoke_model.return_value = mock_response

    # Act
    llm_service = LLMService()
    response = llm_service.invoke(prompt)

    # Assert
    assert response == expected_response_text
    mock_boto_client.invoke_model.assert_called_once()
    call_args, call_kwargs = mock_boto_client.invoke_model.call_args
    body = json.loads(call_kwargs["body"])
    assert body["messages"][0]["content"][0]["text"] == prompt


def test_llm_service_invoke_empty_response(mocker: MockerFixture) -> None:
    """
    Tests that the LLMService handles an empty or malformed response from Bedrock.
    """
    # Arrange
    mock_boto_client = MagicMock()
    mocker.patch("boto3.client", return_value=mock_boto_client)

    prompt = "Hello, world!"
    mock_response_body = {"content": []}  # Empty content list
    mock_response = {
        "body": MagicMock(read=lambda: json.dumps(mock_response_body).encode("utf-8"))
    }
    mock_boto_client.invoke_model.return_value = mock_response

    # Act
    llm_service = LLMService()
    response = llm_service.invoke(prompt)

    # Assert
    assert response == ""


def test_llm_service_invoke_boto_error(mocker: MockerFixture) -> None:
    """
    Tests that the LLMService propagates exceptions from the boto3 client.
    """
    # Arrange
    mock_boto_client = MagicMock()
    mocker.patch("boto3.client", return_value=mock_boto_client)
    error_message = "Bedrock is unavailable"
    mock_boto_client.invoke_model.side_effect = Exception(error_message)

    # Act & Assert
    llm_service = LLMService()
    with pytest.raises(Exception, match=error_message):
        llm_service.invoke("A prompt that will fail")
