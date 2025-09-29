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
        assert call_args["original_email"] == "This is a test email."


def test_shell_refine_draft_flow(mock_graph):
    """Test the flow for refining an existing draft."""
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        # First invocation to establish a draft
        mock_graph.invoke.return_value = {
            "draft_history": [{"content": "Initial draft."}],
            "error_message": None,
        }

        # Second invocation for refinement
        def invoke_side_effect(state):
            if state.get("user_feedback"):
                return {
                    "draft_history": [
                        {"content": "Initial draft."},
                        {"content": "Refined draft."},
                    ],
                    "error_message": None,
                }
            return {
                "draft_history": [{"content": "Initial draft."}],
                "error_message": None,
            }

        mock_graph.invoke.side_effect = invoke_side_effect

        user_input = "Initial email\nMake it better\nexit\n"
        result = runner.invoke(app, input=user_input)
        assert result.exit_code == 0
        assert result.exception is None
        assert "Feedback ('new' to reset) >>>" in result.stdout
        assert "Refined draft." in result.stdout
        assert mock_graph.invoke.call_count == 2
        # Check the state passed during the refinement call
        last_call_args = mock_graph.invoke.call_args[0][0]
        assert last_call_args["user_feedback"] == "Make it better"
        assert last_call_args["original_email"] is None


def test_shell_new_command_resets_state(mock_graph):
    """Test that the 'new' command resets the state."""
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "Initial email\nnew\nAnother email\nexit\n"
        result = runner.invoke(app, input=user_input)
        assert result.exit_code == 0
        assert result.exception is None
        assert "Resetting session." in result.stdout
        # The prompt should revert to "New Email" after "new"
        # This is tricky to test with a single stdout, but we can check call args
        assert mock_graph.invoke.call_count == 2
        first_call_args = mock_graph.invoke.call_args_list[0][0][0]
        second_call_args = mock_graph.invoke.call_args_list[1][0][0]
        assert first_call_args["original_email"] == "Initial email"
        assert second_call_args["original_email"] == "Another email"
        assert first_call_args["session_id"] == second_call_args["session_id"]


def test_shell_handles_graph_error(mock_graph):
    """Test that the shell displays errors from the graph."""
    mock_graph.invoke.return_value = {"error_message": "Something went wrong"}
    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "This will cause an error\nexit\n"
        result = runner.invoke(app, input=user_input)
        assert result.exit_code == 0
        assert result.exception is None
        assert "Error: Something went wrong" in result.stdout


def test_shell_displays_summary_on_first_draft(mock_graph):
    """Test that the summary is displayed only before the first draft."""
    # Simulate the graph returning summary info and then a draft
    mock_graph.invoke.return_value = {
        "key_info": {
            "sender_name": "John Doe",
            "receiver_name": "Jane Smith",
            "subject": "Test Subject",
        },
        "summary": "This is a test summary.",
        "draft_history": [{"content": "This is the first draft."}],
        "error_message": None,
    }

    with patch("eassistant.cli.build_graph", return_value=mock_graph):
        user_input = "This is a test email.\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert result.exception is None
        # Check that the summary and key info are in the output
        assert "-- Extracted Information --" in result.stdout
        assert "Sender:" in result.stdout
        assert "John Doe" in result.stdout
        assert "Summary" in result.stdout
        assert "This is a test summary." in result.stdout
        # Check that the draft is also there
        assert "-- Latest Draft --" in result.stdout
        assert "This is the first draft." in result.stdout

        # Now, simulate a refinement, which should NOT show the summary again
        mock_graph.invoke.return_value = {
            "draft_history": [
                {"content": "This is the first draft."},
                {"content": "This is the refined draft."},
            ],
            "error_message": None,
        }

        user_input = "Initial email\nRefine it\nexit\n"
        result = runner.invoke(app, input=user_input)

        # The summary should not be printed a second time
        assert "-- Extracted Information --" not in result.stdout
        assert "This is the refined draft." in result.stdout


def test_shell_save_command(mock_graph):
    """Test the 'save' command."""
    with (
        patch("eassistant.cli.build_graph", return_value=mock_graph),
        patch("eassistant.cli.storage_service") as mock_storage,
    ):
        # Simulate a flow where a draft is created, then saved
        user_input = "Create a draft\nsave my_draft.txt\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert result.exception is None
        assert "Draft saved to my_draft.txt" in result.stdout

        # Verify that the storage service's save method was called correctly
        mock_storage.save.assert_called_once_with(
            "This is a test draft.", "my_draft.txt"
        )


def test_shell_save_command_no_draft(mock_graph):
    """Test the 'save' command when there is no draft to save."""
    with (
        patch("eassistant.cli.build_graph", return_value=mock_graph),
        patch("eassistant.cli.storage_service") as mock_storage,
    ):
        # Set up the mock graph to return an empty draft history initially
        mock_graph.invoke.return_value = {"draft_history": []}

        user_input = "save my_draft.txt\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert result.exception is None
        assert "No draft to save." in result.stdout
        mock_storage.save.assert_not_called()


def test_shell_save_command_no_filename(mock_graph):
    """Test the 'save' command without providing a filename."""
    with (
        patch("eassistant.cli.build_graph", return_value=mock_graph),
        patch("eassistant.cli.storage_service") as mock_storage,
    ):
        user_input = "Create a draft\nsave\nexit\n"
        result = runner.invoke(app, input=user_input)

        assert result.exit_code == 0
        assert result.exception is None
        assert "Usage: save <filename>" in result.stdout
        mock_storage.save.assert_not_called()
