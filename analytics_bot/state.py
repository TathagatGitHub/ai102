from __future__ import annotations

from typing import Any, List, Optional
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AnalyticsState(TypedDict):
    # ── Conversation history (accumulated across turns via MemorySaver) ──
    messages: Annotated[List, add_messages]

    # ── Per-turn inputs (reset each invocation) ──
    user_question: str
    intent: str                  # data_query | aggregation | comparison | schema_exploration | chitchat
    candidate_schemas: List[str] # schemas the intent classifier selected

    # ── Schema introspection (populated from live INFORMATION_SCHEMA queries) ──
    schema_context: dict         # {schema_name: {schema.Table: ["col (type)", ...]}}

    # ── SQL pipeline ──
    generated_sql: str
    sql_results: Optional[Any]   # {"rows": [...], "columns": [...]} or None

    # ── Error tracking & retry loop ──
    error_type: Optional[str]    # SCHEMA_ERROR | SYNTAX_ERROR | TIMEOUT | AUTH_ERROR | FORBIDDEN | UNKNOWN_ERROR
    error_message: Optional[str]
    retry_count: int             # incremented by result_validator; max 3 then give up

    # ── Output ──
    final_answer: str
