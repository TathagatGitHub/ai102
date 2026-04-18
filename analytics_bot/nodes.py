from __future__ import annotations

import json
import os
from typing import List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI

from analytics_bot.db import execute_sql, fetch_schema_context
from analytics_bot.schema_registry import SCHEMA_REGISTRY
from analytics_bot.state import AnalyticsState


# ── LLM (shared singleton) ───────────────────────────────────────────────────

def _build_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT_EMPOWEROCEAN_DEVFOUNDRY"],
        api_key=os.getenv("AZURE_OPENAI_KEY_EMPOWER_DEVFOUNDRY"),
        api_version="2025-01-01-preview",
        deployment_name="gpt-4.1",
        temperature=0,
    )

_llm: AzureChatOpenAI | None = None


def get_llm() -> AzureChatOpenAI:
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


# ── Node 1: intent_classifier ─────────────────────────────────────────────────

def intent_classifier(state: AnalyticsState) -> dict:
    """
    Classify the user's intent and identify which schemas are most likely relevant.
    Chitchat and non-data questions are identified here so they can bypass the SQL pipeline.
    """
    question = state["user_question"]
    history = state.get("messages", [])[-6:]   # last 3 conversation turns

    schema_list_str = "\n".join(
        f"  - {name}: {desc}" for name, desc in SCHEMA_REGISTRY.items()
    )

    prompt = f"""You are a router for a data analytics chatbot backed by Microsoft Fabric Lakehouse.

Available schemas:
{schema_list_str}

Recent conversation (last 3 turns):
{_fmt_history(history)}

User question: "{question}"

Determine:
1. intent_type — one of: data_query | aggregation | comparison | schema_exploration | chitchat
2. candidate_schemas — 1 to 3 schema names most likely to contain the relevant data.
   - For schema_exploration questions (e.g. "what tables exist?"), pick the schema the user mentions.
   - For chitchat (greetings, off-topic), return an empty list.
3. reasoning — one sentence explaining which schemas you picked and why.

Respond ONLY with valid JSON. No prose, no markdown fences:
{{
  "intent_type": "...",
  "candidate_schemas": ["schema1"],
  "reasoning": "..."
}}"""

    resp = get_llm().invoke([HumanMessage(content=prompt)])
    parsed = _safe_json(resp.content)

    raw_schemas: List[str] = [s.lower() for s in parsed.get("candidate_schemas", [])]
    valid_schemas = [s for s in raw_schemas if s in SCHEMA_REGISTRY]

    # Fallback: if nothing valid was returned, default to dbo
    if not valid_schemas and parsed.get("intent_type") not in ("chitchat", "schema_exploration"):
        valid_schemas = ["dbo"]

    return {
        "intent": parsed.get("intent_type", "data_query"),
        "candidate_schemas": valid_schemas,
    }


# ── Node 2: schema_router ────────────────────────────────────────────────────

def schema_router(state: AnalyticsState) -> dict:
    """
    Validate and normalise schema names against the registry.
    Acts as a safety net between the intent classifier and the introspector.
    """
    schemas = state.get("candidate_schemas", [])
    valid = [s for s in schemas if s in SCHEMA_REGISTRY]
    return {"candidate_schemas": valid or ["dbo"]}


# ── Node 3: schema_introspector ───────────────────────────────────────────────

def schema_introspector(state: AnalyticsState) -> dict:
    """
    Fetch live table / column metadata from INFORMATION_SCHEMA for the target schemas.
    Results are cached in db.py (_schema_cache) so repeated questions on the same schema
    don't round-trip to Fabric every time.
    When called after a SCHEMA_ERROR we bust the cache to force a fresh read.
    """
    schemas = state["candidate_schemas"]
    force_refresh = (state.get("error_type") == "SCHEMA_ERROR")

    context = fetch_schema_context(schemas, force_refresh=force_refresh)

    return {
        "schema_context": context,
        # Clear any previous schema error so the sql_generator gets a clean slate
        "error_type": None,
        "error_message": None,
    }


# ── Node 4: sql_generator ─────────────────────────────────────────────────────

def sql_generator(state: AnalyticsState) -> dict:
    """
    Generate T-SQL from the user question + live schema context.
    On a retry pass the previous SQL and the error message so the LLM can fix it.
    """
    question = state["user_question"]
    context = state.get("schema_context", {})
    history = state.get("messages", [])[-6:]
    prev_sql = state.get("generated_sql", "")
    error_msg = state.get("error_message", "")

    schema_str = _fmt_schema_context(context)
    history_str = _fmt_history(history)

    retry_block = ""
    if prev_sql and error_msg:
        retry_block = f"""
---- PREVIOUS FAILED ATTEMPT ----
SQL:
{prev_sql}

Error received:
{error_msg[:600]}

Fix the SQL using the error details above. Use only table and column names that appear in the schema context.
----------------------------------"""

    prompt = f"""You are a T-SQL expert for Microsoft Fabric Lakehouse (SQL Server syntax).

STRICT RULES — follow every one, no exceptions:
1. Write ONLY a SELECT statement (or a CTE starting with WITH ... SELECT).
   Never write INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, EXEC, TRUNCATE, or any DDL/DML.
2. Always use fully-qualified names: schema.TableName  (e.g., dbo.PostLog, traffic.TrafficOrder).
3. Use [square brackets] if a name contains spaces or special characters.
4. Use ONLY tables and columns that appear in the schema context below — do not invent names.
5. Return ONLY the raw SQL query. No explanation, no markdown, no code fences.

Schema context (format: schema.Table: col1 (type), col2 (type), ...):
{schema_str}

Recent conversation:
{history_str}

User question: {question}
{retry_block}
SQL:"""

    resp = get_llm().invoke([HumanMessage(content=prompt)])

    # Strip any accidental markdown fences the model might add
    sql = resp.content.strip()
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    sql = sql.strip().rstrip("```").strip()

    return {"generated_sql": sql}


# ── Node 5: sql_executor ──────────────────────────────────────────────────────

def sql_executor(state: AnalyticsState) -> dict:
    """Execute the generated SQL and capture results or classify any errors."""
    sql = state["generated_sql"]
    rows, columns, error_type, error_message = execute_sql(sql)

    return {
        "sql_results": {"rows": rows, "columns": columns} if rows is not None else None,
        "error_type": error_type,
        "error_message": error_message,
    }


# ── Node 6: result_validator ──────────────────────────────────────────────────

def result_validator(state: AnalyticsState) -> dict:
    """
    Increment the retry counter when there is an error.
    The actual routing decision lives in edges.py (route_after_validator).
    """
    if state.get("error_type"):
        return {"retry_count": state.get("retry_count", 0) + 1}
    return {}


# ── Node 7: response_synthesizer ─────────────────────────────────────────────

def response_synthesizer(state: AnalyticsState) -> dict:
    """
    Turn SQL results (or a terminal error) into a human-readable answer.
    If max retries were hit, explains the failure clearly.
    """
    question = state["user_question"]
    sql = state.get("generated_sql", "")
    results = state.get("sql_results")
    error_type = state.get("error_type")
    error_message = state.get("error_message", "")
    retry_count = state.get("retry_count", 0)

    # ── Terminal error path ──────────────────────────────────────────────────
    if error_type and retry_count >= 3:
        answer = (
            f"I was unable to retrieve the data after {retry_count} attempts.\n"
            f"Final error ({error_type}): {error_message[:400]}\n\n"
            "Suggestions:\n"
            "  • Rephrase your question with the exact table or column names.\n"
            "  • Ask me 'what tables exist in the <schema> schema?' to browse available data.\n"
            "  • Check that the schema name is correct (e.g., dbo, traffic, finance)."
        )

    # ── Non-retryable execution error (timeout, auth) ───────────────────────
    elif error_type in ("TIMEOUT", "AUTH_ERROR"):
        answer = (
            f"The query could not complete due to a {error_type.lower().replace('_', ' ')}.\n"
            f"Detail: {error_message[:300]}"
        )

    # ── Empty result set (valid query, zero rows) ────────────────────────────
    elif not results or not results.get("rows"):
        answer = (
            "The query executed successfully but returned no rows.\n"
            "The data you are looking for may not exist for the criteria specified."
        )

    # ── Successful results ───────────────────────────────────────────────────
    else:
        rows = results["rows"]
        cols = results["columns"]
        preview = _fmt_results(rows, cols, max_rows=50)

        prompt = f"""You are a data analytics assistant for a media company.
Answer the user's question based on the SQL query results below.

User question: "{question}"

SQL used:
{sql}

Query results ({len(rows)} row(s)):
{preview}

Instructions:
- State the key numbers or findings directly and concisely.
- If there is only one number, lead with it.
- If there are multiple rows, summarise the key insights (top items, totals, trends).
- Format large numbers with commas (e.g., 1,234,567).
- Do NOT re-state the SQL or column names verbatim unless it aids clarity."""

        resp = get_llm().invoke([HumanMessage(content=prompt)])
        answer = resp.content

    return {
        "final_answer": answer,
        "messages": [AIMessage(content=answer)],
    }


# ── Node 8: clarification_node ────────────────────────────────────────────────

def clarification_node(state: AnalyticsState) -> dict:
    """
    Ask a targeted follow-up when a valid query returns zero rows.
    Suggests concrete alternatives (date ranges, spelling, different schema).
    """
    question = state["user_question"]
    sql = state.get("generated_sql", "")
    schemas = state.get("candidate_schemas", [])

    prompt = f"""A database query returned zero results.

User question: "{question}"
Schemas searched: {schemas}
SQL executed:
{sql}

Write a helpful follow-up question (1–2 sentences) that suggests:
- A possible date-range or time-period filter to try
- Alternative spellings or naming variations
- A different schema or table that might hold the data

Be specific, not generic."""

    resp = get_llm().invoke([HumanMessage(content=prompt)])
    answer = resp.content

    return {
        "final_answer": answer,
        "messages": [AIMessage(content=answer)],
    }


# ── Node 9: chitchat_responder ────────────────────────────────────────────────

def chitchat_responder(state: AnalyticsState) -> dict:
    """
    Handle greetings, capability questions, and anything that doesn't need SQL.
    """
    question = state["user_question"]
    history = state.get("messages", [])[-6:]

    schema_names = ", ".join(SCHEMA_REGISTRY.keys())

    prompt = f"""You are a helpful data analytics assistant for a media company's Fabric Lakehouse.
The user's message does not require a database query.

Recent conversation:
{_fmt_history(history)}

User: {question}

Respond naturally. If they ask what you can do, explain that you can query data across these schemas:
{schema_names}

Examples of questions you can answer:
- "How many postlogs were created on Monday?"
- "What is the total invoiced amount for Q1?"
- "Show me podcast download trends by episode"
- "What is the budget vs actual spend for finance?"
"""

    resp = get_llm().invoke([HumanMessage(content=prompt)])
    answer = resp.content

    return {
        "final_answer": answer,
        "messages": [AIMessage(content=answer)],
    }


# ── Helper utilities ──────────────────────────────────────────────────────────

def _fmt_history(messages: list) -> str:
    if not messages:
        return "(no prior conversation)"
    lines = []
    for m in messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        # Truncate long messages so the prompt stays manageable
        lines.append(f"{role}: {str(m.content)[:500]}")
    return "\n".join(lines)


def _fmt_schema_context(context: dict) -> str:
    if not context:
        return "(no schema context loaded — verify the schema name is correct)"
    lines = []
    for _schema, tables in context.items():
        for full_table, cols in tables.items():
            col_str = ", ".join(cols[:30])   # cap at 30 columns per table
            lines.append(f"{full_table}: {col_str}")
    return "\n".join(lines)


def _fmt_results(rows: list, columns: list, max_rows: int = 50) -> str:
    if not columns:
        return "(no columns)"
    header = " | ".join(str(c) for c in columns)
    sep = "-" * min(len(header), 140)
    lines = [header, sep]
    for row in rows[:max_rows]:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
    if len(rows) > max_rows:
        lines.append(f"... (+{len(rows) - max_rows} more rows not shown)")
    return "\n".join(lines)


def _safe_json(content: str) -> dict:
    """Safely extract and parse JSON from an LLM response, stripping markdown fences."""
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception:
        return {}
