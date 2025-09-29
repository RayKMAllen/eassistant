from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from eassistant.cli import app

runner = CliRunner()


@pytest.fixture
def mock_graph():
    """Fixture to mock the graph and its invoke method."""
    mock = MagicMock()
    # Simulate a successful draft generation
    mock.invoke.return_value = {
        "draft_history": [{"content": "This is a test draft."}],
        "error_message": None,
    }
    return mock


def test_shell_exit():
    """Test that the shell exits cleanly."""
    with patch("eassistant.cli.build_graph"):
        result = runner.invoke(app, input="exit\n")
        assert result.exit_code == 0
        assert result.exception is None
        assert "Welcome to the e-assistant shell!" in result.stdout


def test_shell_new_email_flow(mock_graph):
    """Test the flow for a new email."""
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        # Simulate entering a new email, then exiting
        user_input = "This is a test email.\nexit\n"
        result = runner.invoke(app, input=user_input)
        assert result.exit_code == 0
        assert result.exception is None
        assert "New Email >>>" in result.stdout
        assert "-- Latest Draft --" in result.stdout
        assert "This is a test draft." in result.stdout
        # Verify the graph was called with the correct state
        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["user_input"] == "This is a test email."


def test_shell_feedback_prompt(mock_graph):
    """Test that the prompt changes after a draft has been created."""
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        # Simulate the graph returning a draft history
        mock_graph.invoke.return_value = {
            "draft_history": [{"content": "A draft."}],
            "error_message": None,
        }

        user_input = "First email\nSome feedback\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert "Feedback >>>" in result.stdout


def test_shell_handles_graph_error(mock_graph):
    """Test that the shell displays errors from the graph."""
    mock_graph.invoke.return_value = {"error_message": "Something went wrong"}
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "This will cause an error\nexit\n"
        result = runner.invoke(app, input=user_input)
        assert result.exit_code == 0
        assert result.exception is None
        assert "Error: Something went wrong" in result.stdout


def test_shell_save_command_with_draft(mock_graph):
    """Test the 'save' command when a draft exists."""
    # Simulate the graph having a draft, then receiving the 'save' command
    mock_graph.invoke.side_effect = [
        {"draft_history": [{"content": "A draft."}], "error_message": None},
        {"draft_history": [{"content": "A draft."}], "error_message": None},
    ]

    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "First email\nsave\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        # Ensure the draft is printed once, but not again after saving
        assert result.stdout.count("-- Latest Draft --") == 1
        # Check that the 'save' input was passed to the graph
        last_call_args = mock_graph.invoke.call_args[0][0]
        assert last_call_args["user_input"] == "save"


def test_shell_save_command_no_draft(mock_graph):
    """Test the 'save' command when no draft exists."""
    # The graph is never invoked because the CLI handles this case
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "save\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert "No draft to save." in result.stdout
        mock_graph.invoke.assert_not_called()


# The complex multi-turn and command-specific tests are removed from the CLI
# tests because this logic now resides in the graph nodes, which are tested
# separately in `test_nodes.py`. The CLI is only responsible for the main
# loop, passing input to the graph, and displaying the final draft.
