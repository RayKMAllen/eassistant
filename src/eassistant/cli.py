import typer
from rich.console import Console

from eassistant.graph.builder import create_graph

app = typer.Typer()


@app.command()  # type: ignore
def shell() -> None:
    """
    Starts the e-assistant interactive shell.
    """
    console = Console()
    console.print("[bold green]Welcome to the e-assistant shell![/bold green]")
    graph = create_graph()
    while True:
        try:
            user_input = console.input("[bold yellow]>>> [/bold yellow]")
            if user_input.lower() in ["exit", "quit"]:
                break

            inputs = {"user_input": user_input}
            for event in graph.stream(inputs):
                console.print(event)

        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    app()
