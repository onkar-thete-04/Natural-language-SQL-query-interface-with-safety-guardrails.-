from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    generated_sql: str
    gold_sql: str | None
    note: str
    created_at: str


def load_cases(path: str) -> list[EvalCase]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return []
    raw = data.get("test_cases", []) or []
    return [
        EvalCase(
            id=item["id"],
            question=item["question"],
            generated_sql=item["generated_sql"],
            gold_sql=item.get("gold_sql"),
            note=item.get("note", ""),
            created_at=item.get("created_at", ""),
        )
        for item in raw
    ]
