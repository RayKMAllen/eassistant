import json

from ..services.llm import LLMService
from .state import Draft, GraphState


def parse_input(state: GraphState) -> GraphState:
    """
    Parses the user input and populates the `original_email` field in the state.
    """
    print("Parsing input...")
    # For M1, we just pass the input through. M2 will add file parsing.
    if "original_email" not in state or not state["original_email"]:
        state["original_email"] = "No input provided"
    return state


def extract_and_summarize(state: GraphState) -> GraphState:
    """
    Extracts key entities and summarizes the email content using an LLM.
    """
    print("Extracting and summarizing...")
    email_content = state.get("original_email")
    if not email_content:
        state["error_message"] = "No email content to process."
        return state

    llm_service = LLMService()

    prompt = f"""
        Analyze the following email and extract the following information:
        1.  **sender**: The sender's name or email address.
        2.  **subject**: The subject line of the email.
        3.  **key_points**: A list of the most important points or questions.
        4.  **summary**: A concise one-paragraph summary of the entire email.

        Return the information as a single, minified JSON object with the keys "sender",
        "subject", "key_points", and "summary".

        Email content:
        ---
        {email_content}
        ---
    """

    try:
        response_text = llm_service.invoke_claude(prompt)
        response_json = json.loads(response_text)

        state["extracted_entities"] = {
            "sender": response_json.get("sender"),
            "subject": response_json.get("subject"),
            "key_points": response_json.get("key_points", []),
        }
        state["summary"] = response_json.get("summary")

    except json.JSONDecodeError:
        state["error_message"] = "Failed to parse LLM response as JSON."
    except Exception as e:
        state["error_message"] = f"An unexpected error occurred: {e}"

    return state


def generate_initial_draft(state: GraphState) -> GraphState:
    """
    Generates an initial email draft based on the extracted summary and entities.
    """
    print("Generating initial draft...")
    summary = state.get("summary")
    entities = state.get("extracted_entities")

    if not summary or not entities:
        state["error_message"] = "Missing summary or entities to generate a draft."
        return state

    llm_service = LLMService()

    prompt = f"""
        Based on the following summary and extracted entities from an email,
        write a professional and helpful reply.

        The reply should be concise and address all key points.

        Summary:
        ---
        {summary}
        ---

        Key Points to Address:
        ---
        - {", ".join(entities.get("key_points", []))}
        ---

        Draft the email reply below:
    """

    try:
        draft_content = llm_service.invoke_claude(prompt)
        new_draft: Draft = {
            "content": draft_content,
            "tone": state.get("current_tone", "professional"),
        }
        if "draft_history" not in state:
            state["draft_history"] = []
        state["draft_history"].append(new_draft)

    except Exception as e:
        state["error_message"] = f"Failed to generate draft: {e}"

    return state
