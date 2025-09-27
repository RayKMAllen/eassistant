import json
from typing import Any, Dict, List

import boto3

from eassistant.config import config


class LLMService:
    """
    A service to interact with LLMs on AWS Bedrock.
    """

    def __init__(self) -> None:
        """
        Initializes the Bedrock client.
        """
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime", region_name=config["region_name"]
        )

    def invoke(self, prompt: str) -> str:
        """
        Invokes the configured LLM.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The model's response text.
        """
        model_id = config["model_id"]

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
        )

        response = self.bedrock_runtime.invoke_model(body=body, modelId=model_id)

        response_body: Dict[str, Any] = json.loads(response.get("body").read())
        content: List[Dict[str, str]] = response_body.get("content", [])

        if content and "text" in content[0]:
            return content[0]["text"]

        return ""
