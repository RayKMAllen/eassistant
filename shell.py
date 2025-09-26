import typer
from rich.console import Console

from eassistant.graph.builder import get_hello_world_graph

app = typer.Typer()
console = Console()


@app.command()  # type: ignore[misc]
def main() -> None:
    """
    Starts the conversational email assistant shell.
    """
    console.print(
        "[bold green]Welcome to the Conversational Email Assistant![/bold green]"
    )
    console.print("Type 'exit' to quit.")

    graph = get_hello_world_graph()

    while True:
        try:
            user_input = typer.prompt("\n> ")
            if user_input.lower() == "exit":
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            # Invoke the graph with the user's input
            initial_state = {"message": user_input}
            final_state = graph.invoke(initial_state)
            console.print(final_state)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Goodbye![/bold yellow]")
            break


if __name__ == "__main__":
    app()
