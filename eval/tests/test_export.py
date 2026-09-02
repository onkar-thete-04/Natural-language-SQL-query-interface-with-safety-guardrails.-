from __future__ import annotations

import yaml

from eval.cases import load_cases
from eval.export import export_correct, export_incorrect


def test_export_incorrect_appends_case(tmp_path):
    path = str(tmp_path / "cases.yaml")
    export_incorrect("how many films", "SELECT COUNT(*) FROM film;", "wrong count", path)
    cases = load_cases(path)
    assert len(cases) == 1
    assert cases[0].question == "how many films"
    assert cases[0].generated_sql == "SELECT COUNT(*) FROM film;"
    assert cases[0].gold_sql is None
    assert cases[0].note == "wrong count"


def test_export_incorrect_appends_to_existing(tmp_path):
    path = str(tmp_path / "cases.yaml")
    export_incorrect("q1", "SELECT 1;", "", path)
    export_incorrect("q2", "SELECT 2;", "", path)
    assert len(load_cases(path)) == 2


def test_export_correct_appends_few_shot(tmp_path):
    path = str(tmp_path / "feedback.yaml")
    export_correct("how many actors", "SELECT COUNT(*) FROM actor;", ["actor"], path)
    data = yaml.safe_load(open(path, encoding="utf-8"))
    entry = data["domains"]["user_feedback"][0]
    assert entry["question"] == "how many actors"
    assert entry["sql"] == "SELECT COUNT(*) FROM actor;"
    assert entry["pattern"] == "user_corrected"
    assert entry["tables"] == ["actor"]


def test_load_cases_missing_file_returns_empty(tmp_path):
    assert load_cases(str(tmp_path / "missing.yaml")) == []
