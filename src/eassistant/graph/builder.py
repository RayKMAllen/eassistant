from langgraph.graph import END, StateGraph
from langgraph.prebuilt import CompiledGraph

from .nodes import hello_node
from .state import GraphState


def create_graph() -> CompiledGraph:
    """
    Creates the conversational assistant graph.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("hello", hello_node)
    workflow.set_entry_point("hello")
    workflow.add_edge("hello", END)

    app = workflow.compile()
    return app
