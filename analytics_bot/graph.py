from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from analytics_bot.edges import route_after_intent, route_after_validator
from analytics_bot.nodes import (
    chitchat_responder,
    clarification_node,
    intent_classifier,
    response_synthesizer,
    result_validator,
    schema_introspector,
    schema_router,
    sql_executor,
    sql_generator,
)
from analytics_bot.state import AnalyticsState


def build_graph():
    """
    Assemble and compile the LangGraph StateGraph.

    Graph topology:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  START                                                              │
    │    └─► intent_classifier                                            │
    │             ├─[chitchat]──────────────► chitchat_responder ─► END  │
    │             └─[data / exploration]──► schema_router                │
    │                                           └─► schema_introspector  │
    │                                                 └─► sql_generator  │
    │                                                       └─► sql_executor
    │                                                             └─► result_validator
    │                                                                   ├─[success] ──────► response_synthesizer ─► END
    │                                                                   ├─[empty rows] ──► clarification_node   ─► END
    │                                                                   ├─[schema err] ──► schema_introspector (retry)
    │                                                                   ├─[syntax err] ──► sql_generator        (retry)
    │                                                                   └─[max retries]──► response_synthesizer ─► END
    └─────────────────────────────────────────────────────────────────────┘

    MemorySaver checkpointer provides conversation memory across CLI turns
    via the thread_id in the invocation config.
    """
    g = StateGraph(AnalyticsState)

    # ── Register nodes ────────────────────────────────────────────────────
    g.add_node("intent_classifier",    intent_classifier)
    g.add_node("schema_router",        schema_router)
    g.add_node("schema_introspector",  schema_introspector)
    g.add_node("sql_generator",        sql_generator)
    g.add_node("sql_executor",         sql_executor)
    g.add_node("result_validator",     result_validator)
    g.add_node("response_synthesizer", response_synthesizer)
    g.add_node("clarification_node",   clarification_node)
    g.add_node("chitchat_responder",   chitchat_responder)

    # ── Entry point ───────────────────────────────────────────────────────
    g.add_edge(START, "intent_classifier")

    # ── Conditional: chitchat bypasses SQL pipeline ───────────────────────
    g.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "chitchat_responder": "chitchat_responder",
            "schema_router":      "schema_router",
        },
    )

    # ── Main SQL pipeline (linear) ────────────────────────────────────────
    g.add_edge("schema_router",       "schema_introspector")
    g.add_edge("schema_introspector", "sql_generator")
    g.add_edge("sql_generator",       "sql_executor")
    g.add_edge("sql_executor",        "result_validator")

    # ── Conditional routing after validation ─────────────────────────────
    g.add_conditional_edges(
        "result_validator",
        route_after_validator,
        {
            "sql_generator":        "sql_generator",        # syntax / logic retry
            "schema_introspector":  "schema_introspector",  # schema cache bust + retry
            "response_synthesizer": "response_synthesizer", # success or terminal error
            "clarification_node":   "clarification_node",   # valid SQL, zero rows
        },
    )

    # ── Terminal edges ────────────────────────────────────────────────────
    g.add_edge("response_synthesizer", END)
    g.add_edge("clarification_node",   END)
    g.add_edge("chitchat_responder",   END)

    # ── Compile with in-memory checkpointer for conversation persistence ──
    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


# Module-level compiled graph — imported by main.py
graph = build_graph()
