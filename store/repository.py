from __future__ import annotations

import json
import sqlite3

from store.db import SCHEMA


class Store:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def save_query(self, *, query_id, session_id, question, sql, confidence, result_json, created_at) -> None:
        self._conn.execute(
            "INSERT INTO queries (id, session_id, question, sql, confidence, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (query_id, session_id, question, sql, confidence, json.dumps(result_json), created_at),
        )
        self._conn.commit()

    def get_history(self, session_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT q.id, q.question, q.sql, q.confidence, q.created_at, f.rating "
            "FROM queries q LEFT JOIN feedback f ON f.query_id = q.id "
            "WHERE q.session_id = ? ORDER BY q.created_at DESC",
            (session_id,),
        ).fetchall()
        return [
            {
                "query_id": r["id"],
                "question": r["question"],
                "sql": r["sql"],
                "confidence": r["confidence"],
                "created_at": r["created_at"],
                "rating": r["rating"],
            }
            for r in rows
        ]

    def get_query(self, query_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT result_json FROM queries WHERE id = ?", (query_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["result_json"])

    def save_feedback(self, *, query_id, rating, note, created_at) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO feedback (query_id, rating, note, created_at) "
            "VALUES (?, ?, ?, ?)",
            (query_id, rating, note, created_at),
        )
        self._conn.commit()

    def get_feedback(self, query_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT query_id, rating, note, created_at FROM feedback WHERE query_id = ?",
            (query_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
