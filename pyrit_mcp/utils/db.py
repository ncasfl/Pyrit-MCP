"""
pyrit_mcp.utils.db — DuckDB singleton connection and schema initialisation.

All application code obtains a database connection through get_connection().
The connection is created once per process lifetime and reused.

Schema design:
  - targets   — configured target applications (stored as JSON config blobs)
  - datasets  — prompt datasets loaded into this session
  - scorers   — configured scorer instances
  - attacks   — attack campaign records (lifecycle: queued → running → complete)
  - results   — individual prompt/response pairs from attack campaigns

This is the MCP server's own metadata schema. PyRIT's internal DuckDB memory
(conversation history) is managed separately by PyRIT and coexists in the same
database file under its own tables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb

_connection: duckdb.DuckDBPyConnection | None = None

# ---------------------------------------------------------------------------
# DDL — all tables are CREATE IF NOT EXISTS so restarts are safe
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS targets (
    target_id   VARCHAR PRIMARY KEY,
    target_type VARCHAR NOT NULL,
    config_json JSON    NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id    VARCHAR PRIMARY KEY,
    name          VARCHAR NOT NULL UNIQUE,
    category      VARCHAR,
    prompt_count  INTEGER,
    prompts_json  JSON,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scorers (
    scorer_id   VARCHAR PRIMARY KEY,
    scorer_type VARCHAR NOT NULL,
    config_json JSON    NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attacks (
    attack_id        VARCHAR PRIMARY KEY,
    target_id        VARCHAR REFERENCES targets(target_id),
    dataset_name     VARCHAR,
    orchestrator_type VARCHAR NOT NULL,
    status           VARCHAR NOT NULL DEFAULT 'queued',
    started_at       TIMESTAMP DEFAULT NOW(),
    completed_at     TIMESTAMP,
    error_message    VARCHAR,
    metadata_json    JSON
);

CREATE TABLE IF NOT EXISTS results (
    result_id     VARCHAR PRIMARY KEY,
    attack_id     VARCHAR REFERENCES attacks(attack_id),
    prompt_text   TEXT    NOT NULL,
    response_text TEXT,
    scores_json   JSON,
    timestamp     TIMESTAMP DEFAULT NOW()
);
"""


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return the singleton DuckDB connection, creating it if necessary.

    Uses the path from the PYRIT_DB_PATH environment variable, defaulting to
    /data/pyrit.db. Pass ':memory:' for an in-process test database.
    """
    global _connection
    if _connection is None:
        db_path = os.environ.get("PYRIT_DB_PATH", "/data/pyrit.db")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(db_path)
        _initialize_schema(_connection)
    return _connection


def _initialize_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all MCP metadata tables if they do not already exist."""
    conn.execute(_SCHEMA_SQL)


def reset_connection() -> None:
    """Close and reset the singleton connection.

    USE IN TESTS ONLY. Allows each test to start with a clean connection
    (required when PYRIT_DB_PATH=':memory:' so tables are fresh per test).
    """
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None


def execute(sql: str, params: list[Any] | None = None) -> duckdb.DuckDBPyRelation:
    """Execute a SQL statement on the singleton connection.

    Convenience wrapper so callers don't need to import get_connection.
    """
    conn = get_connection()
    if params:
        return conn.execute(sql, params)  # type: ignore[return-value]
    return conn.execute(sql)  # type: ignore[return-value]


def fetchall(sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
    """Execute a SELECT and return all rows."""
    result: list[tuple[Any, ...]] = execute(sql, params).fetchall()
    return result


def fetchone(sql: str, params: list[Any] | None = None) -> tuple[Any, ...] | None:
    """Execute a SELECT and return one row, or None."""
    result: tuple[Any, ...] | None = execute(sql, params).fetchone()
    return result
