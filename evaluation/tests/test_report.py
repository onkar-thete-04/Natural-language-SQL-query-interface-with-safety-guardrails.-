from evaluation.metrics.execution_match import ExecutionMatchResult
from evaluation.metrics.hallucination import HallucinationResult
from evaluation.metrics.sql_match import SqlMatchResult
from evaluation.report import EvaluationReport, write_markdown


def _case(cid, exec_match, sql_match, hallucination):
    return type("CR", (), {
        "case_id": cid, "category": "simple_lookup",
        "execution": exec_match, "sql_match": sql_match, "hallucination": hallucination,
    })()


def _guardrail(blocked):
    return type("G", (), {"case_id": "g", "blocked": blocked, "rules": []})()


def test_execution_accuracy_percentage():
    cases = [
        _case("1", ExecutionMatchResult("1", True, True, ""), SqlMatchResult("1", True, True), HallucinationResult("1", False, False)),
        _case("2", ExecutionMatchResult("2", True, False, "x"), SqlMatchResult("2", True, False), HallucinationResult("2", True, True)),
        _case("3", ExecutionMatchResult("3", True, True, ""), SqlMatchResult("3", True, True), HallucinationResult("3", False, False)),
        _case("4", ExecutionMatchResult("4", False, None, ""), SqlMatchResult("4", False, None), HallucinationResult("4", False, False)),
    ]
    report = EvaluationReport(case_results=cases, guardrail_results=[])
    assert report.execution_accuracy() == 66.66666666666666
    assert report.sql_exact_match_pct() == 66.66666666666666


def test_hallucination_detection_rate_is_recall():
    cases = [
        _case("1", ExecutionMatchResult("1", True, False, "x"), SqlMatchResult("1", True, False), HallucinationResult("1", True, True)),
        _case("2", ExecutionMatchResult("2", True, False, "x"), SqlMatchResult("2", True, False), HallucinationResult("2", True, False)),
    ]
    report = EvaluationReport(case_results=cases, guardrail_results=[])
    assert report.hallucination_detection_rate() == 50.0


def test_unsafe_queries_executed_zero_when_all_blocked():
    cases = []
    guard = [_guardrail(True), _guardrail(True)]
    report = EvaluationReport(case_results=cases, guardrail_results=guard)
    assert report.guardrail_blocked() == 2
    assert report.unsafe_queries_executed() == 0


def test_markdown_headline_format(tmp_path):
    cases = [
        _case("1", ExecutionMatchResult("1", True, True, ""), SqlMatchResult("1", True, True), HallucinationResult("1", False, False)),
    ]
    report = EvaluationReport(case_results=cases, guardrail_results=[_guardrail(True)])
    md = write_markdown(report)
    assert md.splitlines()[0].startswith("100.0% execution accuracy")
