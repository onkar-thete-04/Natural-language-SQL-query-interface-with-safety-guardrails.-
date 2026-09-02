from evaluation.dataset import GoldenCase, load_cases, validate_cases
import pytest

CATEGORIES = {"simple_lookup", "join", "aggregation", "date_filter", "ambiguous", "unanswerable"}


def _write(tmp_path, text):
    p = tmp_path / "golden_dataset.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def _valid_dataset(n=50):
    cats = sorted(CATEGORIES)
    cases = []
    for i in range(n):
        cat = cats[i % len(cats)]
        if cat == "unanswerable":
            gold = None
        elif cat == "ambiguous":
            gold = ["SELECT 1;"]
        else:
            gold = "SELECT 1;"
        cases.append(GoldenCase(f"{cat}-{i}", cat, "q", gold, None, ""))
    return cases


def test_load_cases_parses_all_fields(tmp_path):
    path = _write(tmp_path, """
cases:
  - id: agg-003
    category: aggregation
    question: "How much revenue did store 2 generate?"
    gold_sql: "SELECT SUM(amount) FROM payment;"
    expected_rows: 1
    note: "single row"
  - id: amb-001
    category: ambiguous
    question: "What are the top films?"
    gold_sql:
      - "SELECT ... 1"
      - "SELECT ... 2"
  - id: una-001
    category: unanswerable
    question: "List all products in electronics."
""")
    cases = load_cases(path)
    assert len(cases) == 3
    assert cases[0].gold_sql == "SELECT SUM(amount) FROM payment;"
    assert cases[1].gold_sql == ["SELECT ... 1", "SELECT ... 2"]
    assert cases[2].gold_sql is None
    assert cases[2].expected_rows is None


def test_load_cases_missing_file_returns_empty():
    assert load_cases("nonexistent.yaml") == []


def test_validate_cases_rejects_unknown_category():
    c = GoldenCase("x", "nope", "q", "SELECT 1;", 1, "")
    with pytest.raises(ValueError):
        validate_cases([c])


def test_validate_cases_requires_gold_sql_for_deterministic():
    c = GoldenCase("x", "join", "q", None, 1, "")
    with pytest.raises(ValueError):
        validate_cases([c])


def test_validate_cases_requires_list_for_ambiguous():
    c = GoldenCase("x", "ambiguous", "q", "SELECT 1;", 1, "")
    with pytest.raises(ValueError):
        validate_cases([c])


def test_validate_cases_allows_no_gold_for_unanswerable():
    validate_cases(_valid_dataset())


def test_validate_cases_enforces_minimum_and_categories():
    cases = []
    for cat in sorted(CATEGORIES):
        gold = None if cat == "unanswerable" else ("SELECT 1;" if cat != "ambiguous" else ["SELECT 1;"])
        cases.append(GoldenCase(f"{cat}-1", cat, "q", gold, None, ""))
    with pytest.raises(ValueError):
        validate_cases(cases)  # 6 categories present, but < 50 -> should raise on count


def test_validate_cases_requires_at_least_50():
    c = GoldenCase("x", "simple_lookup", "q", "SELECT 1;", 1, "")
    with pytest.raises(ValueError):
        validate_cases([c] * 49)
