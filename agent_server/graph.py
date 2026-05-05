"""LangGraph StateGraph definition for the campaign pipeline."""

from langgraph.graph import END, StateGraph

from agent_server.graph_nodes import (
    enrich_context,
    generate_email,
    handle_error,
    process_input,
    rank_and_select,
    retrieve_candidates,
)
from agent_server.graph_state import CampaignState


def _has_error(state: CampaignState) -> str:
    """Conditional edge: route to handle_error if an error exists."""
    return "handle_error" if state.get("error") else "ok"


# ── Build the graph ──────────────────────────────────────────────────────────

builder = StateGraph(CampaignState)

# Add nodes
builder.add_node("process_input", process_input)
builder.add_node("retrieve_candidates", retrieve_candidates)
builder.add_node("rank_and_select", rank_and_select)
builder.add_node("enrich_context", enrich_context)
builder.add_node("generate_email", generate_email)
builder.add_node("handle_error", handle_error)

# Set entry point
builder.set_entry_point("process_input")

# Edges with error routing
builder.add_conditional_edges("process_input", _has_error, {"ok": "retrieve_candidates", "handle_error": "handle_error"})
builder.add_edge("retrieve_candidates", "rank_and_select")
builder.add_conditional_edges("rank_and_select", _has_error, {"ok": "enrich_context", "handle_error": "handle_error"})
builder.add_edge("enrich_context", "generate_email")
builder.add_edge("generate_email", END)
builder.add_edge("handle_error", END)

# Compile
campaign_graph = builder.compile()
