from __future__ import annotations

import os
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── Module-level schema cache (survives across graph invocations in the same process) ──
_schema_cache: Dict[str, Dict[str, List[str]]] = {}


def _build_engine():
    """Build a SQLAlchemy engine using Service Principal auth against Fabric Lakehouse."""
    server = os.getenv("SERVER_MEDIA_TOOL")
    database = os.getenv("DATABASE_MEDIA_TOOL")
    client_id = os.getenv("CLIENT_ID_AIAnalytics")
    client_secret = os.getenv("CLIENT_SECRET_AIAnalytics")

    if not all([server, database, client_id, client_secret]):
        raise EnvironmentError(
            "Missing one or more required env vars: "
            "SERVER_MEDIA_TOOL, DATABASE_MEDIA_TOOL, CLIENT_ID_AIAnalytics, CLIENT_SECRET_AIAnalytics"
        )

    params = urllib.parse.quote_plus(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Authentication=ActiveDirectoryServicePrincipal;"
        f"UID={client_id};"
        f"PWD={client_secret};"
        "Encrypt=yes;"
        "Connection Timeout=180;"
        "Login Timeout=180;"
    )
    conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(
        conn_str,
        pool_pre_ping=True,
        pool_recycle=3600,      # refresh connections every hour
        pool_size=3,
        max_overflow=5,
    )


# Lazily initialised so import doesn't fail if env vars aren't set yet
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


# ── Schema introspection ──────────────────────────────────────────────────────

def fetch_schema_context(
    schemas: List[str],
    force_refresh: bool = False,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Query INFORMATION_SCHEMA.COLUMNS for the requested schemas and return:
        {schema_name: {"schema.TableName": ["col1 (type)", "col2 (type)", ...]}}

    Results are cached in-process. Pass force_refresh=True to bust the cache
    (used when a SCHEMA_ERROR suggests our cached info was stale).
    """
    global _schema_cache

    to_fetch = [s for s in schemas if s not in _schema_cache or force_refresh]

    if to_fetch:
        # Build a parameterised IN list using named bind params
        placeholders = ", ".join(f":s{i}" for i in range(len(to_fetch)))
        bind_params = {f"s{i}": s for i, s in enumerate(to_fetch)}

        query = text(f"""
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA IN ({placeholders})
            ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """)

        fresh: Dict[str, Dict[str, List[str]]] = {}
        with get_engine().connect() as conn:
            rows = conn.execute(query, bind_params).fetchall()

        for row in rows:
            schema_name, table_name, col_name, data_type = row
            key = schema_name.lower()
            full_table = f"{schema_name}.{table_name}"
            fresh.setdefault(key, {}).setdefault(full_table, []).append(
                f"{col_name} ({data_type})"
            )

        _schema_cache.update(fresh)

    return {s: _schema_cache[s] for s in schemas if s in _schema_cache}


# ── SQL execution ─────────────────────────────────────────────────────────────

# Words that should never appear as the first token of an allowed query.
_FORBIDDEN_STARTS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "REVOKE",
    "DENY", "BACKUP", "RESTORE", "BULK",
}


def execute_sql(
    sql: str,
) -> Tuple[Optional[List[List[Any]]], Optional[List[str]], Optional[str], Optional[str]]:
    """
    Execute a read-only SQL query against Fabric Lakehouse.

    Returns:
        (rows, columns, error_type, error_message)
        rows and columns are None on error; error_type / error_message are None on success.

    Error types:
        FORBIDDEN     — non-SELECT statement attempted
        SCHEMA_ERROR  — table or column not found
        SYNTAX_ERROR  — T-SQL syntax problem
        TIMEOUT       — query timed out
        AUTH_ERROR    — authentication / permission failure
        UNKNOWN_ERROR — anything else
    """
    # ── Safety guard ────────────────────────────────────────────────────────
    stripped = sql.strip()
    first_token = stripped.split()[0].upper() if stripped else ""

    if first_token in _FORBIDDEN_STARTS:
        return None, None, "FORBIDDEN", (
            f"Statement type '{first_token}' is not permitted. Only SELECT queries are allowed."
        )
    if first_token not in ("SELECT", "WITH"):
        return None, None, "FORBIDDEN", (
            "Only SELECT (and CTEs starting with WITH) are permitted."
        )

    # ── Execute ──────────────────────────────────────────────────────────────
    try:
        with get_engine().connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]
        return rows, columns, None, None

    except Exception as exc:
        error_msg = str(exc)[:2000]   # cap length — ODBC errors can be huge

        if "Invalid object name" in error_msg or "Invalid column name" in error_msg:
            error_type = "SCHEMA_ERROR"
        elif (
            "Incorrect syntax" in error_msg
            or "syntax error" in error_msg.lower()
            or "Parse error" in error_msg
        ):
            error_type = "SYNTAX_ERROR"
        elif "timeout" in error_msg.lower() or "Timeout" in error_msg:
            error_type = "TIMEOUT"
        elif "Login failed" in error_msg or "permission" in error_msg.lower():
            error_type = "AUTH_ERROR"
        else:
            error_type = "UNKNOWN_ERROR"

        return None, None, error_type, error_msg
