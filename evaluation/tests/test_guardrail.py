from unittest import mock

from evaluation.metrics.guardrail import GuardrailCaseResult, evaluate, load_guardrail_cases


def test_evaluate_blocked_when_guardrail_rejects():
    decision = type("D", (), {"passed": False, "violations": [type("V", (), {"rule": "block_ddl"})()]})()
    with mock.patch("evaluation.metrics.guardrail.validate", return_value=("sql", decision)):
        r = evaluate("g1", "DROP TABLE film;", None, None)
        assert r == GuardrailCaseResult("g1", True, ["block_ddl"])


def test_evaluate_passed_when_guardrail_allows():
    decision = type("D", (), {"passed": True, "violations": []})()
    with mock.patch("evaluation.metrics.guardrail.validate", return_value=("sql", decision)):
        r = evaluate("g2", "SELECT 1;", None, None)
        assert r == GuardrailCaseResult("g2", False, [])


def test_load_guardrail_cases(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("cases:\n  - id: g1\n    sql: 'DROP TABLE film;'\n  - id: g2\n    sql: 'DELETE FROM payment;'\n", encoding="utf-8")
    cases = load_guardrail_cases(str(p))
    assert len(cases) == 2 and cases[0]["id"] == "g1"
