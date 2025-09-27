from langgraph.graph import END, StateGraph

from .nodes import (
    extract_and_summarize,
    generate_initial_draft,
    parse_input,
    refine_draft,
)
from .state import GraphState


def route_initial_request(state: GraphState) -> str:
    """
    Determines the starting point of the graph.
    If there's user feedback and a draft history, we refine.
    Otherwise, we start a new email flow.
    """
    if state.get("user_feedback") and state.get("draft_history"):
        return "refine_draft"
    return "parse_input"


def build_graph() -> StateGraph:
    """
    Creates the conversational assistant graph.
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("extract_and_summarize", extract_and_summarize)
    workflow.add_node("generate_initial_draft", generate_initial_draft)
    workflow.add_node("refine_draft", refine_draft)

    # Define control flow
    workflow.set_conditional_entry_point(
        route_initial_request,
        {
            "refine_draft": "refine_draft",
            "parse_input": "parse_input",
        },
    )

    workflow.add_edge("parse_input", "extract_and_summarize")
    workflow.add_edge("extract_and_summarize", "generate_initial_draft")

    # After generating or refining, the process ends for this turn,
    # waiting for the next user input from the CLI.
    workflow.add_edge("generate_initial_draft", END)
    workflow.add_edge("refine_draft", END)

    return workflow.compile()
