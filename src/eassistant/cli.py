import uuid

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from eassistant.graph.builder import build_graph
from eassistant.graph.state import GraphState
from eassistant.services.storage import StorageService

app = typer.Typer()

storage_service = StorageService()


def get_initial_state(session_id: uuid.UUID) -> GraphState:
    """Creates a fresh state for a new email, preserving the session."""
    return {
        "session_id": session_id,
        "original_email": None,
        "email_path": None,
        "key_info": None,
        "summary": None,
        "draft_history": [],
        "current_tone": "professional",
        "user_feedback": None,
        "error_message": None,
    }


@app.command()  # type: ignore
def shell() -> None:
    """Starts the e-assistant interactive shell."""
    console = Console()
    console.print("[bold green]Welcome to the e-assistant shell![/bold green]")
    console.print("Enter email content, a file path, or type 'new' to start over.")

    graph = build_graph()
    session_id = uuid.uuid4()
    state = get_initial_state(session_id)

    while True:
        try:
            # Determine prompt based on whether we expect a new email or feedback
            if not state.get("draft_history"):
                prompt = "[bold yellow]New Email >>> [/bold yellow]"
            else:
                prompt = "[bold yellow]Feedback ('new' to reset) >>> [/bold yellow]"

            user_input = Prompt.ask(prompt, console=console)

            if user_input.lower() in ["exit", "quit"]:
                break

            if user_input.lower() == "new":
                state = get_initial_state(session_id)
                console.print(
                    "[cyan]Resetting session. Please enter new email content.[/cyan]"
                )
                continue

            if user_input.lower().startswith("save"):
                parts = user_input.split()
                if len(parts) > 1:
                    filename = parts[1]
                    draft_history = state.get("draft_history")
                    if draft_history:
                        latest_draft_content = draft_history[-1]["content"]
                        try:
                            storage_service.save(latest_draft_content, filename)
                            console.print(
                                f"[bold green]Draft saved to {filename}[/bold green]"
                            )
                        except Exception as e:
                            console.print(
                                f"[bold red]Error saving file: {e}[/bold red]"
                            )
                    else:
                        console.print("[bold red]No draft to save.[/bold red]")
                else:
                    console.print("[bold red]Usage: save <filename>[/bold red]")
                continue

            # Prepare the state for the graph invocation
            current_input_state = state.copy()
            if not state.get("draft_history"):
                current_input_state["original_email"] = user_input
                current_input_state["user_feedback"] = None
            else:
                current_input_state["user_feedback"] = user_input
                # We don't need to pass original_email again for refinement
                current_input_state["original_email"] = None

            # Run the graph
            final_state = graph.invoke(current_input_state)

            if final_state:
                # Check if this is the first time a draft has been created
                is_first_draft = not state.get("draft_history") and final_state.get(
                    "draft_history"
                )

                state.update(final_state)

                if state.get("error_message"):
                    console.print(
                        f"[bold red]Error: {state['error_message']}[/bold red]"
                    )
                    # Reset error message after displaying it
                    state["error_message"] = None

                # If we just generated the first draft, show the summary that led to it.
                if is_first_draft:
                    key_info = state.get("key_info")
                    summary = state.get("summary")
                    if key_info and summary:
                        table = Table(show_header=False, box=None, padding=(0, 1))
                        table.add_column(style="cyan")
                        table.add_column()

                        table.add_row("Sender:", key_info.get("sender_name", "N/A"))
                        table.add_row(
                            "Recipient:", key_info.get("receiver_name", "N/A")
                        )
                        table.add_row("Subject:", key_info.get("subject", "N/A"))

                        summary_panel = Panel(
                            summary,
                            title="[bold]Summary[/bold]",
                            border_style="green",
                            expand=False,
                        )

                        console.print(
                            "\n[bold green]-- Extracted Information --[/bold green]"
                        )
                        console.print(table)
                        console.print(summary_panel)
                        console.print(
                            "[bold green]---------------------------[/bold green]\n"
                        )

                draft_history = state.get("draft_history")
                if draft_history:
                    latest_draft = draft_history[-1]
                    console.print("\n[bold green]-- Latest Draft --[/bold green]")
                    console.print(latest_draft["content"])
                    console.print("[bold green]--------------------[/bold green]\n")

        except (KeyboardInterrupt, EOFError):  # pragma: no cover
            break

    console.print("[bold green]Goodbye![/bold green]")


if __name__ == "__main__":  # pragma: no cover
    app()
