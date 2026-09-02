from __future__ import annotations

import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    question    TEXT NOT NULL,
    sql         TEXT NOT NULL,
    confidence  REAL,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    query_id    TEXT PRIMARY KEY REFERENCES queries(id),
    rating      TEXT NOT NULL,
    note        TEXT,
    created_at  TEXT NOT NULL
);
"""


@contextmanager
def connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with connection(db_path) as conn:
        conn.executescript(SCHEMA)
