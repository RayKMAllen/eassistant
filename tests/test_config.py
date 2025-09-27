from unittest.mock import mock_open, patch

from eassistant.config import get_config


def test_get_config():
    """Test that get_config reads and returns the config object."""
    mock_yaml_content = """
    llm:
      provider: bedrock
      model: anthropic.claude-3-sonnet-20240229-v1:0
    """
    with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
        mock_return = {
            "llm": {
                "provider": "bedrock",
                "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            }
        }
        with patch("yaml.safe_load", return_value=mock_return):
            config = get_config()
            assert config["llm"]["provider"] == "bedrock"
            assert config["llm"]["model"] == "anthropic.claude-3-sonnet-20240229-v1:0"
