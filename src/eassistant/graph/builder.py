from langgraph.graph import END, StateGraph

from .nodes import (
    ask_for_tone,
    extract_and_summarize,
    generate_initial_draft,
    handle_error,
    handle_unclear,
    parse_input,
    refine_draft,
    reset_session,
    route_action,
    save_draft,
    show_info,
)
from .state import GraphState


def check_for_errors(state: GraphState) -> str:
    """If an error is present, route to the error handler. Otherwise, continue."""
    if state.get("error_message"):
        return "handle_error"
    return "continue"


def route_by_intent(state: GraphState) -> str:
    """Routes to the appropriate node based on the user's intent."""
    intent = state.get("intent")
    if intent == "process_new_email":
        return "parse_input"
    if intent == "refine_draft":
        return "refine_draft"
    if intent == "show_info":
        return "show_info"
    if intent == "save_draft":
        return "save_draft"
    if intent == "reset_session":
        return "reset_session"
    return "handle_unclear"


def build_graph() -> StateGraph:
    """
    Creates the conversational assistant graph with intent-based routing.
    """
    workflow = StateGraph(GraphState)

    # Add all nodes
    workflow.add_node("route_action", route_action)
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("extract_and_summarize", extract_and_summarize)
    workflow.add_node("ask_for_tone", ask_for_tone)
    workflow.add_node("generate_initial_draft", generate_initial_draft)
    workflow.add_node("refine_draft", refine_draft)
    workflow.add_node("show_info", show_info)
    workflow.add_node("save_draft", save_draft)
    workflow.add_node("reset_session", reset_session)
    workflow.add_node("handle_unclear", handle_unclear)
    workflow.add_node("handle_error", handle_error)

    # Set the entry point to the intent router
    workflow.set_entry_point("route_action")

    # Add conditional edges from the intent router
    workflow.add_conditional_edges(
        "route_action",
        route_by_intent,
        {
            "parse_input": "parse_input",
            "refine_draft": "refine_draft",
            "show_info": "show_info",
            "save_draft": "save_draft",
            "reset_session": "reset_session",
            "handle_unclear": "handle_unclear",
        },
    )

    # Define the rest of the control flow with error checking
    workflow.add_conditional_edges(
        "parse_input",
        check_for_errors,
        {"continue": "extract_and_summarize", "handle_error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "extract_and_summarize",
        check_for_errors,
        {"continue": "ask_for_tone", "handle_error": "handle_error"},
    )
    workflow.add_conditional_edges(
        "ask_for_tone",
        check_for_errors,
        {"continue": "generate_initial_draft", "handle_error": "handle_error"},
    )
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

    # Edges for single-action nodes
    workflow.add_edge("show_info", END)
    workflow.add_edge("save_draft", END)
    workflow.add_edge("reset_session", END)
    workflow.add_edge("handle_unclear", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()
