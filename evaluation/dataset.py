from __future__ import annotations

from dataclasses import dataclass

import yaml

CATEGORIES = {"simple_lookup", "join", "aggregation", "date_filter", "ambiguous", "unanswerable"}
MIN_CASES = 50


@dataclass(frozen=True)
class GoldenCase:
    id: str
    category: str
    question: str
    gold_sql: str | list[str] | None
    expected_rows: int | None
    note: str


def load_cases(path: str) -> list[GoldenCase]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return []
    raw = data.get("cases", []) or []
    return [
        GoldenCase(
            id=item["id"],
            category=item["category"],
            question=item["question"],
            gold_sql=item.get("gold_sql"),
            expected_rows=item.get("expected_rows"),
            note=item.get("note", ""),
        )
        for item in raw
    ]


def validate_cases(cases: list[GoldenCase]) -> None:
    for c in cases:
        if c.category not in CATEGORIES:
            raise ValueError(f"{c.id}: unknown category '{c.category}'")
        if c.category == "unanswerable":
            if c.gold_sql is not None:
                raise ValueError(f"{c.id}: unanswerable must not have gold_sql")
        elif c.category == "ambiguous":
            if not isinstance(c.gold_sql, list) or not c.gold_sql:
                raise ValueError(f"{c.id}: ambiguous must have a non-empty list of gold_sql")
        else:
            if not isinstance(c.gold_sql, str) or not c.gold_sql.strip():
                raise ValueError(f"{c.id}: {c.category} must have a single gold_sql string")
    if len(cases) < MIN_CASES:
        raise ValueError(f"golden dataset must have at least {MIN_CASES} cases (got {len(cases)})")
    seen_categories = {c.category for c in cases}
    if not CATEGORIES.issubset(seen_categories):
        missing = CATEGORIES - seen_categories
        raise ValueError(f"golden dataset missing categories: {sorted(missing)}")
