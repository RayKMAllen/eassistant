import json
from datetime import datetime
from pathlib import Path

from ..services.llm import LLMService
from ..services.storage import StorageService
from ..utils.files import extract_text_from_pdf
from .state import Draft, GraphState

# Use single, module-level instances for services.
# This allows for easier mocking during tests.
llm_service = LLMService()
storage_service = StorageService()


def parse_input(state: GraphState) -> GraphState:
    """
    Parses user input. If it's a file path, it extracts the text.
    Otherwise, it treats the input as the email content itself.
    """
    print("Parsing input...")
    user_input_raw = state.get("original_email")
    user_input = user_input_raw.strip() if user_input_raw else ""

    if not user_input:
        state["error_message"] = "Input email cannot be empty."
        return state

    # After stripping, the original_email in the state should be updated
    state["original_email"] = user_input
    input_path = Path(user_input)

    # Check if the input looks like a path before checking if it's a file
    # This avoids treating a sentence with a period as a file path.
    is_potential_path = "." in user_input and " " not in user_input

    if is_potential_path and input_path.suffix.lower() == ".pdf":
        if not input_path.is_file():
            state["error_message"] = f"File not found: {user_input}"
            return state
        try:
            state["original_email"] = extract_text_from_pdf(input_path)
            state["email_path"] = str(input_path)
        except ValueError as e:
            state["error_message"] = str(e)

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
        draft_history = state.get("draft_history")
        if draft_history is None:
            draft_history = []
        draft_history.append(new_draft)
        state["draft_history"] = draft_history

    except Exception as e:
        state["error_message"] = f"Failed to generate draft: {e}"

    return state


def refine_draft(state: GraphState) -> GraphState:
    """
    Refines an existing draft based on user feedback.
    """
    print("Refining draft...")
    draft_history = state.get("draft_history")
    user_feedback = state.get("user_feedback")
    current_tone = state.get("current_tone") or "professional"

    if not draft_history:
        state["error_message"] = "No draft to refine."
        return state

    if not user_feedback:
        state["error_message"] = "No user feedback provided to refine the draft."
        return state

    latest_draft = draft_history[-1]["content"]

    prompt = f"""
        A user wants to refine an email draft.

        Original Draft:
        ---
        {latest_draft}
        ---

        User Feedback:
        ---
        {user_feedback}
        ---

        Current Tone: {current_tone}

        Please generate a new version of the draft that incorporates the user's
        feedback and maintains the specified tone.
    """

    try:
        refined_content = llm_service.invoke(prompt)
        new_draft: Draft = {
            "content": refined_content,
            "tone": current_tone,
        }
        draft_history.append(new_draft)
        state["draft_history"] = draft_history
        state["user_feedback"] = None  # Clear feedback after using it

    except Exception as e:
        state["error_message"] = f"Failed to refine draft: {e}"

    return state


def save_draft(state: GraphState) -> GraphState:
    """
    Saves the latest draft to a file using the StorageService.
    """
    print("Saving draft...")
    draft_history = state.get("draft_history")

    if not draft_history:
        state["error_message"] = "No draft to save."
        return state

    latest_draft = draft_history[-1]["content"]

    # Generate a filename with a timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"draft-{timestamp}.txt"

    # For now, save to a local 'outputs' directory.
    # This could be configured later.
    output_path = Path("outputs") / filename

    try:
        storage_service.save(content=latest_draft, file_path=str(output_path))
        print(f"Draft saved to {output_path}")
    except Exception as e:
        state["error_message"] = f"Failed to save draft: {e}"

    return state


def handle_error(state: GraphState) -> GraphState:
    """
    Handles errors by printing a user-friendly message.
    Clears the error message from the state after handling.
    """
    error_message = state.get("error_message")
    if error_message:
        print(f"An error occurred: {error_message}")
        state["error_message"] = None  # Clear the error
    return state
