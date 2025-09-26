from .state import GraphState


def hello_node(state: GraphState) -> GraphState:
    """
    A simple node that returns a hello world message.
    """
    user_input = state.get("user_input", "World")
    return {"result": f"Hello, {user_input}!"}
