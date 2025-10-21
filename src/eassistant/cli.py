import uuid

import typer
from rich.console import Console
from rich.prompt import Prompt

from eassistant.graph.builder import build_graph
from eassistant.graph.state import GraphState

app = typer.Typer()


def get_initial_state(session_id: uuid.UUID) -> GraphState:
    """Creates a fresh state for a new session."""
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
        "save_target": None,
        "conversation_summary": None,
    }


@app.command()
def shell() -> None:
    """Starts the e-assistant interactive shell."""
    console = Console()
    console.print("[bold green]Welcome to the e-assistant shell![/bold green]")
    console.print("Enter an email, a file path, or ask for help.")

    graph = build_graph()
    session_id = uuid.uuid4()
    state: GraphState = get_initial_state(session_id)

    while True:
        try:
            if not state.get("draft_history"):
                prompt = "[bold yellow]New Email >>> [/bold yellow]"
            else:
                prompt = "[bold yellow]Feedback >>> [/bold yellow]"

            user_input = Prompt.ask(prompt, console=console)

            if user_input.lower() in ["exit", "quit"]:
                break

            # The graph now handles all conversational logic
            current_input_state = state.copy()
            current_input_state["user_input"] = user_input

            # Special handling for 'save' command for better UX
            if user_input.lower() == "save":
                if not state.get("draft_history"):
                    console.print("[bold yellow]No draft to save.[/bold yellow]")
                    continue  # Skip graph invocation and re-prompt

            final_state = graph.invoke(current_input_state)

            if final_state:
                state.update(final_state)

                # Handle and display errors from the graph
                if error_message := state.get("error_message"):
                    console.print(f"[bold red]Error:[/bold red] {error_message}")
                    # Clear the error after displaying it
                    state["error_message"] = None
                # Display the latest draft if one exists
                elif draft_history := state.get("draft_history"):
                    # Avoid re-printing the draft if it was just saved
                    if user_input.lower() != "save":
                        latest_draft = draft_history[-1]
                        console.print("\n[bold green]-- Latest Draft --[/bold green]")
                        console.print(latest_draft["content"])
                        console.print("[bold green]--------------------[/bold green]\n")

        except (KeyboardInterrupt, EOFError):  # pragma: no cover
            break

    console.print("[bold green]Goodbye![/bold green]")


if __name__ == "__main__":  # pragma: no cover
    app()
