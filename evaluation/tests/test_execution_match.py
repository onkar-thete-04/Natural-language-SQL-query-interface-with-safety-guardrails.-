from unittest import mock

from evaluation.dataset import GoldenCase
from evaluation.metrics.execution_match import ExecutionMatchResult, evaluate


def _result(row_count):
    return type("R", (), {"execution": type("E", (), {"row_count": row_count})()})()


def test_unanswerable_matches_when_empty():
    case = GoldenCase("x", "unanswerable", "q", None, None, "")
    assert evaluate(case, _result(0), "url", 1000) == ExecutionMatchResult("x", True, True, "")


def test_unanswerable_fails_when_nonempty():
    case = GoldenCase("x", "unanswerable", "q", None, None, "")
    r = evaluate(case, _result(3), "url", 1000)
    assert r.applicable is True and r.matched is False


@mock.patch("evaluation.metrics.execution_match.compare")
@mock.patch("evaluation.metrics.execution_match.execute")
@mock.patch("evaluation.metrics.execution_match.create_readonly_engine")
@mock.patch("evaluation.metrics.execution_match.read_only_session")
def test_deterministic_match_when_comparator_agrees(session, engine, execute, compare):
    compare.return_value = type("A", (), {"agreed": True})()
    session.return_value.__enter__.return_value = object()
    case = GoldenCase("x", "simple_lookup", "q", "SELECT 1;", 1, "")
    r = evaluate(case, _result(1), "url", 1000)
    assert r.matched is True


@mock.patch("evaluation.metrics.execution_match.compare")
@mock.patch("evaluation.metrics.execution_match.execute")
@mock.patch("evaluation.metrics.execution_match.create_readonly_engine")
@mock.patch("evaluation.metrics.execution_match.read_only_session")
def test_ambiguous_matches_any_gold(session, engine, execute, compare):
    compare.side_effect = [
        type("A", (), {"agreed": False})(),
        type("A", (), {"agreed": True})(),
    ]
    session.return_value.__enter__.return_value = object()
    case = GoldenCase("x", "ambiguous", "q", ["SELECT 1;", "SELECT 2;"], 1, "")
    r = evaluate(case, _result(1), "url", 1000)
    assert r.matched is True
