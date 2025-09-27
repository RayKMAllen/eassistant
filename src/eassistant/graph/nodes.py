from .state import GraphState


def parse_input(state: GraphState) -> GraphState:
    """
    Parses the user input and populates the `original_email` field in the state.
    """
    print("Parsing input...")
    # For M1, we just pass the input through. M2 will add file parsing.
    if "original_email" not in state or not state["original_email"]:
        state["original_email"] = "No input provided"
    return state


def extract_and_summarize(state: GraphState) -> GraphState:
    """
    A placeholder for the extraction and summarization node.
    """
    # TODO: Implement logic for M1.4
    print("Extracting and summarizing...")
    return state


def generate_initial_draft(state: GraphState) -> GraphState:
    """
    A placeholder for the initial draft generation node.
    """
    # TODO: Implement logic for M1.5
    print("Generating initial draft...")
    return state
