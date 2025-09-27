import json

from ..services.llm import LLMService
from .state import Draft, GraphState

# Use a single, module-level instance for the LLM service.
# This allows for easier mocking during tests.
llm_service = LLMService()


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

    prompt = f"""
        Analyze the following email and extract the following information:
        1.  **sender_name**: The sender's name.
        2.  **sender_contact**: The sender's contact details (email or phone).
        3.  **receiver_name**: The receiver's name.
        4.  **receiver_contact**: The receiver's contact details (email or phone).
        5.  **subject**: The subject line of the email.
        6.  **summary**: A concise one-paragraph summary of the entire email.

        Return the information as a single, minified JSON object with the
        keys "sender_name", "sender_contact", "receiver_name",
        "receiver_contact", "subject", and "summary".

        Email content:
        ---
        {email_content}
        ---
    """

    try:
        response_text = llm_service.invoke(prompt)
        response_json = json.loads(response_text)

        state["key_info"] = {
            "sender_name": response_json.get("sender_name"),
            "sender_contact": response_json.get("sender_contact"),
            "receiver_name": response_json.get("receiver_name"),
            "receiver_contact": response_json.get("receiver_contact"),
            "subject": response_json.get("subject"),
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
    entities = state.get("key_info")

    if not summary or not entities:
        state["error_message"] = "Missing summary or entities to generate a draft."
        return state

    prompt = f"""
        Based on the following summary and extracted entities from an email,
        write a professional and helpful reply.

        The reply should be concise and address all key points.

        Summary:
        ---
        {summary}
        ---

        Sender: {entities.get("sender_name")} ({entities.get("sender_contact")})
        Receiver: {entities.get("receiver_name")} ({entities.get("receiver_contact")})

        Subject: {entities.get("subject")}

        Draft the email reply below:
    """

    try:
        draft_content = llm_service.invoke(prompt)
        new_draft: Draft = {
            "content": draft_content,
            "tone": state.get("current_tone") or "professional",
        }
        if state.get("draft_history") is None:
            state["draft_history"] = []
        # mypy doesn't know that the above line guarantees draft_history is a list
        state["draft_history"].append(new_draft)  # type: ignore

    except Exception as e:
        state["error_message"] = f"Failed to generate draft: {e}"

    return state
