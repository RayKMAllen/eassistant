from typing import TypedDict

from langgraph.graph import END, CompiledGraph, StateGraph


class HelloWorldState(TypedDict):
    message: str


def hello_node(state: HelloWorldState) -> HelloWorldState:
    """
    A simple node that appends ' world!' to the message.
    """
    return {"message": state["message"] + " world!"}


def get_hello_world_graph() -> CompiledGraph:
    """
    Builds the 'hello world' LangGraph instance.
    """
    workflow = StateGraph(HelloWorldState)
    workflow.add_node("hello", hello_node)
    workflow.set_entry_point("hello")
    workflow.add_edge("hello", END)
    return workflow.compile()


if __name__ == "__main__":
    # Example of how to run the graph
    graph = get_hello_world_graph()
    initial_state = {"message": "hello"}
    final_state = graph.invoke(initial_state)
    print(final_state)
