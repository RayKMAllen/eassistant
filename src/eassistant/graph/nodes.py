import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..services.llm import LLMService
from ..services.storage import StorageService
from ..utils.files import extract_text_from_pdf
from .state import Draft, GraphState

# Use single, module-level instances for services.
# This allows for easier mocking during tests.
llm_service = LLMService()
storage_service = StorageService()
console = Console()


def route_action(state: GraphState) -> GraphState:
    """
    Dynamically classifies user intent based on a rich context summary.
    """
    print("Routing action...")
    user_input = (state.get("user_input") or "").strip()
    draft_history = state.get("draft_history")
    conversation_summary = state.get("conversation_summary", "")

    if not user_input:
        state["intent"] = "unclear"
        return state

    # Construct a rich context for the LLM
    context = f"""
        You are an AI assistant helping a user draft emails.
        The user's latest input is: "{user_input}"

        Conversation Summary:
        ---
        {conversation_summary if conversation_summary else "No summary yet."}
        ---

        Current State:
        - Is there a draft in progress? {"Yes" if draft_history else "No"}
        - Latest draft content (if any):
          {draft_history[-1]["content"] if draft_history else "N/A"}
    """

    prompt = f"""
        Based on the provided context and user input, classify the user's
        primary intent into ONE of the following categories:
        - process_new_email: User wants to start a new email, either by
          providing raw text or by asking to load a file (e.g.,
          'load my_document.pdf').
        - refine_draft: User wants to change the existing draft.
        - show_info: User wants to see the extracted summary/info.
        - save_draft: User wants to save the current draft.
        - reset_session: User wants to start over completely.
        - handle_idle_chat: User is making small talk or asking for help.
        - unclear: The intent cannot be determined.

        Here are some examples of user input and the correct classification:
        - User input: "load report.pdf" -> Intent: "process_new_email"
        - User input: "Can you look at C:\\Users\\Me\\file.pdf"
          -> Intent: "process_new_email"
        - User input: "make it more formal" -> Intent: "refine_draft"
        - User input: "show me the summary again" -> Intent: "show_info"

        Context:
        {context}

        User Input: "{user_input}"

        Return a single JSON object with the key "intent" and the determined
        category. For example: {{"intent": "refine_draft"}}
    """

    try:
        response_text = llm_service.invoke(prompt)
        response_json = json.loads(response_text)
        intent = response_json.get("intent", "unclear")

        # Update state based on intent
        if intent == "process_new_email":
            state["original_email"] = user_input
        elif intent == "refine_draft":
            state["user_feedback"] = user_input

        state["intent"] = intent

        # Update conversation summary
        new_summary_entry = (
            f"User said: '{user_input}' -> AI classified intent as: '{intent}'"
        )
        updated_summary = (
            f"{conversation_summary}\n- {new_summary_entry}"
            if conversation_summary
            else f"- {new_summary_entry}"
        )
        state["conversation_summary"] = updated_summary

    except (json.JSONDecodeError, Exception) as e:
        state["intent"] = "unclear"
        state["error_message"] = f"Error during intent routing: {e}"

    return state


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

    # Handle 'load <filename>' command
    potential_path = user_input
    if user_input.lower().startswith("load ") and len(user_input.split()) > 1:
        potential_path = user_input.split(maxsplit=1)[1]

    input_path = Path(potential_path)

    # Check if the input looks like a path before checking if it's a file
    # This avoids treating a sentence with a period as a file path.
    is_potential_path = "." in potential_path and " " not in potential_path

    if is_potential_path and input_path.suffix.lower() == ".pdf":
        if not input_path.is_file():
            state["error_message"] = f"File not found: {potential_path}"
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


def ask_for_tone(state: GraphState) -> GraphState:
    """
    Asks the user for the desired tone of the email draft.
    """
    print("\n---")
    key_info = state.get("key_info")
    summary = state.get("summary")

    if key_info:
        sender_info = (
            f"[bold]Sender:[/bold] {key_info.get('sender_name', 'N/A')} "
            f"({key_info.get('sender_contact', 'N/A')})"
        )
        recipient_info = (
            f"[bold]Recipient:[/bold] {key_info.get('receiver_name', 'N/A')} "
            f"({key_info.get('receiver_contact', 'N/A')})"
        )
        subject_info = f"[bold]Subject:[/bold] {key_info.get('subject', 'N/A')}"
        content = f"{sender_info}\n{recipient_info}\n{subject_info}"
        info_panel = Panel(
            content,
            title="Extracted Information",
            border_style="green",
        )
        console.print(info_panel)

    if summary:
        summary_panel = Panel(
            summary,
            title="Summary",
            border_style="blue",
        )
        console.print(summary_panel)

    try:
        prompt = (
            "Enter the desired tone for the draft (e.g., formal, casual, "
            "friendly) [default: professional]: "
        )
        tone = console.input(prompt)
        state["current_tone"] = tone.strip() if tone.strip() else "professional"
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C or Ctrl+D gracefully
        print("\nOperation cancelled by user.")
        state["error_message"] = "User cancelled the operation."
        state["current_tone"] = "professional"  # Default on cancel

    console.print(f"Tone set to: [bold cyan]{state['current_tone']}[/bold cyan]")
    print("---\n")
    return state


def generate_initial_draft(state: GraphState) -> GraphState:
    """
    Generates an initial email draft based on the extracted summary and entities.
    """
    print("Generating initial draft...")
    summary = state.get("summary")
    entities = state.get("key_info")
    tone = state.get("current_tone") or "professional"

    if not summary or not entities:
        state["error_message"] = "Missing summary or entities to generate a draft."
        return state

    prompt = f"""
        Based on the following summary and extracted entities from an email,
        write a helpful reply with a "{tone}" tone.

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


def show_info(state: GraphState) -> GraphState:
    """
    Displays the extracted key info and summary.
    """
    print("Showing extracted information...")
    key_info = state.get("key_info")
    summary = state.get("summary")

    if not key_info or not summary:
        console.print("[bold yellow]No information extracted yet.[/bold yellow]")
        return state

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column()

    table.add_row("Sender:", key_info.get("sender_name", "N/A"))
    table.add_row("Sender Contact:", key_info.get("sender_contact", "N/A"))
    table.add_row("Recipient:", key_info.get("receiver_name", "N/A"))
    table.add_row("Recipient Contact:", key_info.get("receiver_contact", "N/A"))
    table.add_row("Subject:", key_info.get("subject", "N/A"))

    summary_panel = Panel(
        summary,
        title="[bold]Summary[/bold]",
        border_style="green",
        expand=False,
    )

    console.print("\n[bold green]-- Extracted Information --[/bold green]")
    console.print(table)
    console.print(summary_panel)
    console.print("[bold green]---------------------------[/bold green]\n")

    return state


def reset_session(state: GraphState) -> GraphState:
    """
    Resets the graph state to its initial values, preserving the session ID.
    """
    print("Resetting session...")
    session_id = state.get("session_id")
    if not session_id:
        # This should theoretically never happen if the graph is initialized correctly.
        raise ValueError("Session ID is missing and cannot be reset.")

    console.print("[cyan]Resetting session. Please enter new email content.[/cyan]")
    # This is a simplified version of get_initial_state from cli.py
    return {
        "session_id": session_id,
        "user_input": None,
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
        "intent": None,
        "conversation_summary": None,
    }


def handle_unclear(state: GraphState) -> GraphState:
    """
    Handles cases where the user's intent is unclear.
    """
    print("Handling unclear intent...")
    console.print(
        "[bold yellow]I'm not sure what you mean. You can:\n"
        "- Provide a new email or file path.\n"
        "- Ask to 'show info'.\n"
        "- Ask to 'save draft'.\n"
        "- Type 'new' to start over.[/bold yellow]"
    )
    state["intent"] = "unclear"
    return state


def handle_idle_chat(state: GraphState) -> GraphState:
    """
    Handles idle chat by providing a simple conversational response.
    """
    print("Handling idle chat...")
    console.print("Hello! How can I help you with your email?")
    return state
