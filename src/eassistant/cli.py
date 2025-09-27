import typer
from rich.console import Console

from eassistant.graph.builder import build_graph

app = typer.Typer()


@app.command()  # type: ignore
def shell() -> None:
    """
    Starts the e-assistant interactive shell.
    """
    console = Console()
    console.print("[bold green]Welcome to the e-assistant shell![/bold green]")
    graph = build_graph()
    while True:
        try:
            user_input = console.input("[bold yellow]>>> [/bold yellow]")
            if user_input.lower() in ["exit", "quit"]:
                break

            inputs = {
                "session_id": "123",
                "original_email": user_input,
                "email_path": None,
                "key_info": None,
                "summary": None,
                "draft_history": [],
                "current_tone": "professional",
                "user_feedback": None,
                "error_message": None,
            }
            for event in graph.stream(inputs):
                console.print(event)

        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    app()
