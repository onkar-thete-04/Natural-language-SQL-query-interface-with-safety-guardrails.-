from pathlib import Path

import sqlparse

from evaluation.dataset import load_cases, validate_cases

DATASET_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "golden_dataset.yaml"
ALL_CATEGORIES = {"simple_lookup", "join", "aggregation", "date_filter", "ambiguous", "unanswerable"}


def test_shipped_golden_dataset_is_valid():
    cases = load_cases(str(DATASET_PATH))
    validate_cases(cases)
    assert len(cases) >= 50
    categories = {c.category for c in cases}
    assert categories == ALL_CATEGORIES


def test_deterministic_gold_sql_is_single_statement():
    cases = load_cases(str(DATASET_PATH))
    for c in cases:
        if isinstance(c.gold_sql, str):
            statements = [s for s in sqlparse.parse(c.gold_sql) if s.tokens]
            assert len(statements) == 1, f"{c.id}: expected single statement, got {len(statements)}"
