"""
SQLite database helpers for WWF ITR Tool.
Stores portfolio, fundamental, and target data locally so users can
edit and persist changes between sessions.
"""
import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Default database location
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DB_NAME = "itr_data.db"


def get_db_path() -> str:
    """Return the full path to the SQLite database file."""
    os.makedirs(_DB_DIR, exist_ok=True)
    return os.path.join(_DB_DIR, _DB_NAME)


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    return sqlite3.connect(get_db_path())


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the metadata table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                name        TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                description TEXT,
                tables_json TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Save / load helpers
# ---------------------------------------------------------------------------

def _table_name(dataset: str, kind: str) -> str:
    """
    Build a safe SQLite table name for a dataset component.

    Args:
        dataset: Dataset name (e.g. 'my_portfolio').
        kind: One of 'portfolio', 'fundamental_data', 'target_data'.
    """
    safe = dataset.replace(" ", "_").replace("-", "_")
    return f"ds_{safe}__{kind}"


def save_dataset(
    name: str,
    portfolio_df: pd.DataFrame,
    fundamental_df: pd.DataFrame,
    target_df: pd.DataFrame,
    description: str = "",
) -> None:
    """
    Persist a complete dataset (portfolio + provider sheets) to SQLite.

    Overwrites any existing dataset with the same name.
    """
    init_db()
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        tables = {
            "portfolio": _table_name(name, "portfolio"),
            "fundamental_data": _table_name(name, "fundamental_data"),
            "target_data": _table_name(name, "target_data"),
        }

        # Write each DataFrame to its own table
        portfolio_df.to_sql(tables["portfolio"], conn, if_exists="replace", index=False)
        fundamental_df.to_sql(tables["fundamental_data"], conn, if_exists="replace", index=False)
        target_df.to_sql(tables["target_data"], conn, if_exists="replace", index=False)

        # Upsert metadata
        conn.execute(
            """
            INSERT INTO datasets (name, created_at, updated_at, description, tables_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                updated_at  = excluded.updated_at,
                description = excluded.description,
                tables_json = excluded.tables_json
            """,
            (name, now, now, description, json.dumps(tables)),
        )
        conn.commit()
    finally:
        conn.close()


def load_dataset(name: str) -> Dict[str, pd.DataFrame]:
    """
    Load a saved dataset from SQLite.

    Returns:
        Dict with keys 'portfolio', 'fundamental_data', 'target_data',
        each containing a DataFrame.

    Raises:
        KeyError: If the dataset name is not found.
    """
    init_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT tables_json FROM datasets WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Dataset '{name}' not found in database")

        tables = json.loads(row[0])
        result = {}
        for kind, tbl in tables.items():
            result[kind] = pd.read_sql(f'SELECT * FROM "{tbl}"', conn)
        return result
    finally:
        conn.close()


def update_table(
    dataset_name: str,
    kind: str,
    df: pd.DataFrame,
) -> None:
    """
    Update a single table (portfolio / fundamental_data / target_data)
    within an existing dataset.

    Args:
        dataset_name: Name of the dataset.
        kind: One of 'portfolio', 'fundamental_data', 'target_data'.
        df: Updated DataFrame to write.
    """
    init_db()
    conn = _get_connection()
    try:
        tbl = _table_name(dataset_name, kind)
        df.to_sql(tbl, conn, if_exists="replace", index=False)
        conn.execute(
            "UPDATE datasets SET updated_at = ? WHERE name = ?",
            (datetime.utcnow().isoformat(), dataset_name),
        )
        conn.commit()
    finally:
        conn.close()


def list_datasets() -> List[Dict]:
    """
    Return metadata for all saved datasets.

    Each dict contains: name, created_at, updated_at, description.
    """
    init_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT name, created_at, updated_at, description FROM datasets ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {"name": r[0], "created_at": r[1], "updated_at": r[2], "description": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def delete_dataset(name: str) -> None:
    """Delete a dataset and its associated tables from the database."""
    init_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT tables_json FROM datasets WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return

        tables = json.loads(row[0])
        for tbl in tables.values():
            conn.execute(f'DROP TABLE IF EXISTS "{tbl}"')
        conn.execute("DELETE FROM datasets WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()
