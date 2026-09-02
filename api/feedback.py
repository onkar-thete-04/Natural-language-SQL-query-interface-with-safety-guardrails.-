from __future__ import annotations

from datetime import datetime, timezone

from eval.export import export_correct, export_incorrect


def apply_feedback(store, query_id: str, rating: str, note: str, settings) -> None:
    result = store.get_query(query_id)
    if result is None:
        return
    store.save_feedback(
        query_id=query_id,
        rating=rating,
        note=note,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    question = result["question"]
    sql = result["generated_sql"]["sql"]
    if rating == "correct":
        tables = result["generated_sql"]["tables"]
        export_correct(question, sql, tables, settings.few_shot_feedback_path)
    else:
        export_incorrect(question, sql, note, settings.eval_test_cases_path)
