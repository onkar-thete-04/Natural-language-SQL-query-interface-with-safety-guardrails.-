from __future__ import annotations

import json

from store.db import connection, init_db


class Store:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        init_db(db_path)

    def save_query(self, *, query_id, session_id, question, sql, confidence, result_json, created_at) -> None:
        with connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO queries (id, session_id, question, sql, confidence, result_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (query_id, session_id, question, sql, confidence, json.dumps(result_json), created_at),
            )

    def get_history(self, session_id: str) -> list[dict]:
        with connection(self.db_path) as conn:
            rows = conn.execute(
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
        with connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT result_json FROM queries WHERE id = ?", (query_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["result_json"])

    def save_feedback(self, *, query_id, rating, note, created_at) -> None:
        with connection(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO feedback (query_id, rating, note, created_at) "
                "VALUES (?, ?, ?, ?)",
                (query_id, rating, note, created_at),
            )

    def get_feedback(self, query_id: str) -> dict | None:
        with connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT query_id, rating, note, created_at FROM feedback WHERE query_id = ?",
                (query_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)
