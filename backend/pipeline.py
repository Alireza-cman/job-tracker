"""
LangGraph pipeline for job extraction
"""
from typing import Dict, Any, Optional, TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END

from .models import (
    InputMode,
    JobApplication,
    FetchError,
    PipelineState,
)
from .nodes import (
    route_input,
    fetch_url,
    clean_text,
    llm_extract,
    normalize_validate,
    dedupe_check,
    should_fetch,
    check_fetch_error,
)


class GraphState(TypedDict, total=False):
    """State for the extraction graph."""
    # Input
    input_mode: InputMode
    input_url: Optional[str]
    input_text: Optional[str]
    
    # Processing
    fetched_text: Optional[str]
    cleaned_text: Optional[str]
    fetch_error: Optional[FetchError]
    
    # Output
    extracted: Optional[JobApplication]
    fingerprint: Optional[str]
    is_duplicate: bool
    existing_id: Optional[int]
    
    # Meta
    error: Optional[str]


def build_extraction_graph() -> StateGraph:
    """Build and compile the extraction pipeline graph."""
    
    # Create the graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("route", route_input)
    graph.add_node("fetch", fetch_url)
    graph.add_node("clean", clean_text)
    graph.add_node("extract", llm_extract)
    graph.add_node("normalize", normalize_validate)
    graph.add_node("dedupe", dedupe_check)
    
    # Set entry point
    graph.set_entry_point("route")
    
    # Add conditional edge from route
    graph.add_conditional_edges(
        "route",
        should_fetch,
        {
            "fetch": "fetch",
            "clean": "clean",
        }
    )
    
    # Add conditional edge from fetch
    graph.add_conditional_edges(
        "fetch",
        check_fetch_error,
        {
            "error": END,
            "continue": "clean",
        }
    )
    
    # Linear edges for the rest
    graph.add_edge("clean", "extract")
    graph.add_edge("extract", "normalize")
    graph.add_edge("normalize", "dedupe")
    graph.add_edge("dedupe", END)
    
    return graph.compile()


# Compiled graph singleton
_extraction_graph = None


def get_extraction_graph():
    """Get or create the compiled extraction graph."""
    global _extraction_graph
    if _extraction_graph is None:
        _extraction_graph = build_extraction_graph()
    return _extraction_graph


def run_extraction(
    input_mode: InputMode,
    input_url: Optional[str] = None,
    input_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the extraction pipeline.
    
    Args:
        input_mode: Whether input is URL or TEXT
        input_url: URL to fetch (if mode is URL)
        input_text: Raw text (if mode is TEXT)
    
    Returns:
        Final state dict with extracted data or error
    """
    graph = get_extraction_graph()
    
    # Convert enum to string for consistent handling
    mode_str = input_mode.value if hasattr(input_mode, 'value') else str(input_mode)
    
    print(f"[run_extraction] Starting pipeline with mode: {mode_str}")  # Debug
    print(f"[run_extraction] URL: {input_url}")  # Debug
    print(f"[run_extraction] Text length: {len(input_text) if input_text else 0}")  # Debug
    
    initial_state: GraphState = {
        "input_mode": mode_str,  # Use string value
        "input_url": input_url,
        "input_text": input_text,
        "fetched_text": None,
        "cleaned_text": None,
        "fetch_error": None,
        "extracted": None,
        "fingerprint": None,
        "is_duplicate": False,
        "existing_id": None,
        "error": None,
    }
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    print(f"[run_extraction] Pipeline complete. Has extracted: {result.get('extracted') is not None}")  # Debug
    print(f"[run_extraction] Has error: {result.get('error')}")  # Debug
    print(f"[run_extraction] Has fetch_error: {result.get('fetch_error')}")  # Debug
    
    return result


def extract_from_url(url: str) -> Dict[str, Any]:
    """Convenience function to extract from URL."""
    return run_extraction(InputMode.URL, input_url=url)


def extract_from_text(text: str) -> Dict[str, Any]:
    """Convenience function to extract from text."""
    return run_extraction(InputMode.TEXT, input_text=text)
