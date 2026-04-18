from __future__ import annotations

import sys
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# Import after load_dotenv so env vars are available when the engine is built
from analytics_bot.graph import graph  # noqa: E402

# Each CLI session gets its own thread_id so MemorySaver keeps conversation history
# isolated between separate runs of the script.
_THREAD_ID = str(uuid.uuid4())
_CONFIG = {"configurable": {"thread_id": _THREAD_ID}}

_BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║   Azure Fabric Lakehouse — Analytics Chatbot                    ║
║   Powered by LangGraph + GPT-4.1                                ║
║                                                                  ║
║   Queryable schemas:                                             ║
║     claritas · dbo · dbbudget · dcm · dm · estimp               ║
║     finance  · invoices · traffic · map · podcast               ║
║     podinvoices · radiolog · response                           ║
║                                                                  ║
║   Commands:                                                      ║
║     /sql      — toggle display of generated SQL (default: on)   ║
║     /schemas  — list all available schemas                       ║
║     exit      — quit                                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

_SCHEMA_HELP = """Available schemas and what they contain:
  claritas    — Claritas audience ratings and demographic data
  dbo         — Core operational data: postlogs, broadcasts, programmes
  dbbudget    — Budget planning, forecasts, and spend tracking
  dcm         — Digital Campaign Manager: digital ad placements
  dm          — Data migration configuration tables
  estimp      — Media estimates and impressions (CPM, GRP)
  finance     — Financial records, revenue, reconciliation
  invoices    — Invoice records, AP/AR
  traffic     — Traffic management, scheduling, spot placement
  map         — Mapping and cross-reference lookup tables
  podcast     — Podcast episodes, feeds, performance metrics
  podinvoices — Podcast-specific invoice records
  radiolog    — Radio broadcast logs and air-check data
  response    — Direct response metrics, call volumes, campaign response
"""


def run() -> None:
    print(_BANNER)
    show_sql = True  # show the generated SQL after each answer by default

    while True:
        # ── Read user input ──────────────────────────────────────────────
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

        if not user_input:
            continue

        # ── Built-in commands ────────────────────────────────────────────
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            sys.exit(0)

        if user_input.lower() == "/sql":
            show_sql = not show_sql
            print(f"[SQL display {'ON' if show_sql else 'OFF'}]\n")
            continue

        if user_input.lower() == "/schemas":
            print(_SCHEMA_HELP)
            continue

        # ── Build per-turn state ─────────────────────────────────────────
        # Non-message fields are reset each turn; the MemorySaver checkpointer
        # accumulates the messages list across turns via the add_messages reducer.
        state = {
            "messages":        [HumanMessage(content=user_input)],
            "user_question":   user_input,
            # Reset all operational fields so previous turn's data doesn't bleed through
            "intent":          "",
            "candidate_schemas": [],
            "schema_context":  {},
            "generated_sql":   "",
            "sql_results":     None,
            "error_type":      None,
            "error_message":   None,
            "retry_count":     0,
            "final_answer":    "",
        }

        # ── Invoke graph ─────────────────────────────────────────────────
        try:
            result = graph.invoke(state, config=_CONFIG)
        except Exception as exc:
            print(f"\n[Graph error]: {exc}\n")
            continue

        # ── Display answer ───────────────────────────────────────────────
        answer = result.get("final_answer") or "(no answer generated)"
        print(f"\nAssistant: {answer}\n")

        # ── Optionally display diagnostics ───────────────────────────────
        if show_sql:
            intent = result.get("intent", "?")
            schemas = result.get("candidate_schemas", [])
            sql = result.get("generated_sql", "")
            retries = result.get("retry_count", 0)

            print(f"  [intent: {intent} | schemas: {', '.join(schemas) or '—'} | retries: {retries}]")
            if sql:
                indented = sql.replace("\n", "\n  ")
                print(f"  [SQL]\n  {indented}\n")
            else:
                print()


if __name__ == "__main__":
    run()
