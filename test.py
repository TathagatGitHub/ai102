"""
Minimal LangGraph SQL bot — one file, three nodes, no retry logic.

Graph flow:
  load_schema  -->  generate_sql  -->  run_sql
                         |
                    (verify inline)

Concepts demonstrated:
  - TypedDict State
  - Node functions (state in -> dict out)
  - StateGraph, add_node, add_edge, set_entry_point, set_finish_point
  - graph.compile() + graph.invoke()
"""

import os
import sys
import urllib.parse
from typing import Any, Optional
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.utilities import SQLDatabase
from langgraph.graph import StateGraph, END

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────

llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT_EMPOWEROCEAN_DEVFOUNDRY"],
    api_key=os.getenv("AZURE_OPENAI_KEY_EMPOWER_DEVFOUNDRY"),
    api_version="2025-01-01-preview",
    deployment_name="gpt-4.1",
    temperature=0,
)

# ── DB connection ─────────────────────────────────────────────────────────────

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={os.getenv('SERVER_MEDIA_TOOL')};"
    f"DATABASE={os.getenv('DATABASE_MEDIA_TOOL')};"
    "Authentication=ActiveDirectoryServicePrincipal;"
    f"UID={os.getenv('CLIENT_ID_AIAnalytics')};"
    f"PWD={os.getenv('CLIENT_SECRET_AIAnalytics')};"
    "Encrypt=yes;"
    "Connection Timeout=180;"
)
conn_str = f"mssql+pyodbc:///?odbc_connect={params}"

# Single connection — no schema filter so cross-schema queries work
db = SQLDatabase.from_uri(conn_str, view_support=True)

# ── Schema registry ───────────────────────────────────────────────────────────

SCHEMA_REGISTRY: dict = {
    "claritas":    "Claritas demographic and audience ratings data — audience segments, Nielsen/Claritas data",
    "dbo":         "Core operational data — postlogs, broadcast records, programmes, airings, core business tables",
    "dbbudget":    "Budget planning, forecasts, budget revisions, and spend tracking",
    "dcm":         "Digital Campaign Manager (DCM) — digital ad trafficking, placements, and digital campaign data",
    "dm":          "Data migration tables — configuration tables used during ETL and data migration processes",
    "estimp":      "Media estimates and impressions — CPM, GRP, impressions estimates by market and demo",
    "finance":     "Financial records — revenue, billing, reconciliation, and financial reporting",
    "invoices":    "Invoice records — accounts payable, accounts receivable, invoice line items",
    "traffic":     "Traffic management — scheduling instructions, spot placement, copy rotation, traffic orders",
    "map":         "Mapping and cross-reference tables — market maps, station maps, product mappings, lookup data",
    "podcast":     "Podcast content — episodes, feeds, downloads, performance metrics, podcast ad placements",
    "podinvoices": "Podcast invoice records — billing and invoices specific to podcast advertising",
    "radiolog":    "Radio broadcast logs — radio air check data, logged spots, discrepancy reporting",
    "response":    "Response tracking — direct response (DR) metrics, call volumes, campaign response rates",
    "viewership":  "Viewership data — network audience measurements, ratings, and viewing statistics",
    "scheduletools": "client, rates, upfront, remnant, Property, networklogs, demo, daypart, prelog, postlog, actualized data, schedule, and proposal tables",
}


# ── State ─────────────────────────────────────────────────────────────────────
# TypedDict defines the shape of the shared state object passed between nodes.
# Each node receives the full state and returns only the keys it wants to update.

class SQLState(TypedDict):
    question: str           # user's natural-language question
    schema_info: str        # table/column list fetched from the DB
    generated_sql: str      # SQL produced by the LLM
    sql_valid: bool         # True if the LLM thinks the SQL is correct
    result: Optional[Any]   # raw query result rows
    answer: str             # final human-readable answer


# ── Node 1: load_schema ───────────────────────────────────────────────────────
# Fetches the live schema from the database and writes it to state.
# Every downstream node can then reference state["schema_info"].

def load_schema(_state: SQLState) -> dict:
    """Query INFORMATION_SCHEMA for every schema in the registry and build
    a combined schema_info string that the LLM can use to write cross-schema SQL."""
    print("\n[Node 1] Loading schema across all registered schemas...")

    schema_list = ", ".join(f"'{s}'" for s in SCHEMA_REGISTRY)
    sql = f"""
        SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS c
        JOIN INFORMATION_SCHEMA.TABLES t
          ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
        WHERE c.TABLE_SCHEMA IN ({schema_list})
          AND t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
    """
    rows = db.run(sql)

    # rows comes back as a string from db.run(); parse it into grouped lines
    # Format: schema.TableName: col1 (type), col2 (type), ...
    tables: dict = {}
    for row in eval(rows):                          # db.run returns a stringified list of tuples
        schema, table, col, dtype = row
        key = f"{schema}.{table}"
        tables.setdefault(key, []).append(f"{col} ({dtype})")

    lines = [f"{tbl}: {', '.join(cols)}" for tbl, cols in tables.items()]
    schema_info = "\n".join(lines)

    print(f"  Loaded {len(tables)} tables across {len(SCHEMA_REGISTRY)} schemas")
    return {"schema_info": schema_info}


# ── Node 2: generate_sql ──────────────────────────────────────────────────────
# Uses the LLM to write T-SQL, then immediately asks it to verify correctness.
# Verification is a second LLM call inside the same node — keeping things simple
# without adding a whole extra node just for verification.

def generate_sql(state: SQLState) -> dict:
    print("\n[Node 2] Generating SQL...")

    gen_prompt = f"""You are a T-SQL expert for Microsoft Fabric Lakehouse.
Write a SELECT statement that answers the question below.
Use only table and column names from the schema context.
Return ONLY the raw SQL — no markdown, no explanation.

Schema:
{state["schema_info"]}

Question: {state["question"]}
SQL:"""

    sql_response = llm.invoke([HumanMessage(content=gen_prompt)])
    sql = sql_response.content.strip().strip("```").strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()
    print(f"  Generated SQL:\n  {sql}")

    # Inline verification — ask the LLM to sanity-check its own output
    verify_prompt = f"""Review this T-SQL query for correctness against the schema below.
Reply with exactly one word: VALID or INVALID.

Schema:
{state["schema_info"]}

SQL:
{sql}"""

    verdict = llm.invoke([HumanMessage(content=verify_prompt)]).content.strip().upper()
    is_valid = verdict.startswith("VALID")
    print(f"  Verification verdict: {verdict}  ->  valid={is_valid}")

    return {"generated_sql": sql, "sql_valid": is_valid}


# ── Node 3: run_sql ───────────────────────────────────────────────────────────
# Executes the SQL if it passed verification, then formats a final answer.
# If verification failed we skip execution and return an error message.

def run_sql(state: SQLState) -> dict:
    print("\n[Node 3] Running SQL...")

    if not state["sql_valid"]:
        answer = "SQL verification failed — the query was not executed."
        print(f"  {answer}")
        return {"result": None, "answer": answer}

    try:
        raw = db.run(state["generated_sql"])
        print(f"  Raw result (first 500 chars): {str(raw)[:500]}")

        format_prompt = f"""A database query returned the following result.
Write a concise, human-friendly answer to the original question.

Question: {state["question"]}
SQL used: {state["generated_sql"]}
Result: {str(raw)[:2000]}

Answer:"""

        answer = llm.invoke([HumanMessage(content=format_prompt)]).content
        return {"result": raw, "answer": answer}

    except Exception as exc:
        error_msg = f"Query execution failed: {exc}"
        print(f"  ERROR: {error_msg}")
        return {"result": None, "answer": error_msg}


# ── Graph assembly ────────────────────────────────────────────────────────────
# StateGraph wires nodes together; edges define execution order.
# add_edge(A, B) means "after A finishes, run B".

graph_builder = StateGraph(SQLState)

graph_builder.add_node("load_schema",   load_schema)
graph_builder.add_node("generate_sql",  generate_sql)
graph_builder.add_node("run_sql",       run_sql)

graph_builder.set_entry_point("load_schema")       # first node to execute
graph_builder.add_edge("load_schema",  "generate_sql")
graph_builder.add_edge("generate_sql", "run_sql")
graph_builder.add_edge("run_sql",      END)        # END is langgraph's terminal sentinel

graph = graph_builder.compile()


# ── Run ───────────────────────────────────────────────────────────────────────


   
def run() -> None:
    while True:
        question = input("Ask a question about your data: ")
        print(f"\nQuestion: {question}")
        # ── Built-in commands ────────────────────────────────────────────
        if question.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            sys.exit(0)
    
        print("=" * 60)

        # ── Invoke graph ─────────────────────────────────────────────────
        try:
            final_state = graph.invoke({"question": question})
        except Exception as exc:
            print(f"\n[Graph error]: {exc}\n")
        #final_state = graph.invoke({"question": question})

        print("\n" + "=" * 60)
        print("FINAL ANSWER:")
        print(final_state["answer"])


if __name__ == "__main__":
    run()