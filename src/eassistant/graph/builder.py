from langgraph.graph import END, StateGraph

from .nodes import extract_and_summarize, generate_initial_draft, parse_input
from .state import GraphState


def build_graph() -> StateGraph:
    """
    Creates the conversational assistant graph.
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("extract_and_summarize", extract_and_summarize)
    workflow.add_node("generate_initial_draft", generate_initial_draft)

    # Define control flow
    workflow.set_entry_point("parse_input")
    workflow.add_edge("parse_input", "extract_and_summarize")
    workflow.add_edge("extract_and_summarize", "generate_initial_draft")
    workflow.add_edge("generate_initial_draft", END)

    return workflow.compile()
