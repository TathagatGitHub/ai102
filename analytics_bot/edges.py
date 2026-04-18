from __future__ import annotations

from analytics_bot.state import AnalyticsState

MAX_RETRIES = 3


def route_after_intent(state: AnalyticsState) -> str:
    """
    Decision point after intent_classifier.

    - chitchat         → chitchat_responder  (skip SQL pipeline entirely)
    - everything else  → schema_router       (enter the full SQL pipeline)
    """
    if state.get("intent") == "chitchat":
        return "chitchat_responder"
    return "schema_router"


def route_after_validator(state: AnalyticsState) -> str:
    """
    Decision point after result_validator.

    Priority order:
    1. Max retries hit          → response_synthesizer  (give up gracefully)
    2. SCHEMA_ERROR             → schema_introspector   (re-fetch live metadata, bust cache)
    3. SYNTAX_ERROR /
       UNKNOWN_ERROR /
       FORBIDDEN                → sql_generator         (retry with error context)
    4. TIMEOUT / AUTH_ERROR     → response_synthesizer  (can't fix these in a retry loop)
    5. No error, zero rows      → clarification_node    (ask the user to narrow down)
    6. No error, has rows       → response_synthesizer  (success path)
    """
    error_type = state.get("error_type")
    retry_count = state.get("retry_count", 0)
    results = state.get("sql_results")

    # ── Hard stop ──────────────────────────────────────────────────────────
    if retry_count >= MAX_RETRIES:
        return "response_synthesizer"

    # ── Retriable errors ───────────────────────────────────────────────────
    if error_type == "SCHEMA_ERROR":
        # Re-introspect with cache busted; sql_generator will get fresh context
        return "schema_introspector"

    if error_type in ("SYNTAX_ERROR", "UNKNOWN_ERROR", "FORBIDDEN"):
        # Pass error details back to sql_generator for a corrected attempt
        return "sql_generator"

    # ── Non-retriable errors ───────────────────────────────────────────────
    if error_type in ("TIMEOUT", "AUTH_ERROR"):
        return "response_synthesizer"

    # ── Success but empty result set ───────────────────────────────────────
    if not results or not results.get("rows"):
        return "clarification_node"

    # ── Happy path ─────────────────────────────────────────────────────────
    return "response_synthesizer"
