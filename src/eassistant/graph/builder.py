from langgraph.graph import END, StateGraph

from .nodes import (
    display_summary,
    extract_and_summarize,
    generate_initial_draft,
    handle_error,
    parse_input,
    refine_draft,
)
from .state import GraphState


def check_for_errors(state: GraphState) -> str:
    """If an error is present, route to the error handler. Otherwise, continue."""
    if state.get("error_message"):
        return "handle_error"
    return "continue"


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
    workflow.add_node("display_summary", display_summary)
    workflow.add_node("generate_initial_draft", generate_initial_draft)
    workflow.add_node("refine_draft", refine_draft)
    workflow.add_node("handle_error", handle_error)

    # Define control flow
    workflow.set_conditional_entry_point(
        route_initial_request,
        {
            "refine_draft": "refine_draft",
            "parse_input": "parse_input",
        },
    )

    # Each step checks for errors. If an error is found, it goes to the error
    # handler. Otherwise, it proceeds to the next step.
    workflow.add_conditional_edges(
        "parse_input",
        check_for_errors,
        {"continue": "extract_and_summarize", "handle_error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "extract_and_summarize",
        check_for_errors,
        {"continue": "display_summary", "handle_error": "handle_error"},
    )
    workflow.add_edge("display_summary", "generate_initial_draft")
    workflow.add_conditional_edges(
        "generate_initial_draft",
        check_for_errors,
        {"continue": END, "handle_error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "refine_draft",
        check_for_errors,
        {"continue": END, "handle_error": "handle_error"},
    )

    # After an error is handled, the graph ends.
    workflow.add_edge("handle_error", END)

    return workflow.compile()
