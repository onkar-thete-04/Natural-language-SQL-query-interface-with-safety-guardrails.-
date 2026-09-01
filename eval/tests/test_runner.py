from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

from eval.cases import EvalCase
from eval.runner import run_case
from multi_query.models import AgreementResult


def _patch(monkeypatch, agreed):
    import executor.runner
    import multi_query.comparator
    import sandbox.engine

    monkeypatch.setattr(sandbox.engine, "create_readonly_engine", lambda url: MagicMock())
    monkeypatch.setattr(sandbox.engine, "read_only_session", lambda engine: contextlib.nullcontext())
    monkeypatch.setattr(executor.runner, "execute", lambda sql, conn, row_limit: f"exec:{sql}")
    monkeypatch.setattr(
        multi_query.comparator, "compare",
        lambda a, b: AgreementResult(
            agreed=agreed, identical=agreed, row_counts=(1, 1),
            divergence_detail=None if agreed else "diverge",
        ),
    )


def _service(execution):
    s = MagicMock()
    s.run.return_value = MagicMock(execution=execution)
    return s


def test_gold_case_matching_passes(monkeypatch):
    _patch(monkeypatch, agreed=True)
    case = EvalCase(id="c1", question="q", generated_sql="SELECT 1;",
                    gold_sql="SELECT 1;", note="", created_at="")
    result = run_case(case, _service("EXEC"), "sqlite://", 1000)
    assert result.passed is True


def test_gold_case_divergence_fails(monkeypatch):
    _patch(monkeypatch, agreed=False)
    case = EvalCase(id="c2", question="q", generated_sql="SELECT 1;",
                    gold_sql="SELECT 1;", note="", created_at="")
    result = run_case(case, _service("EXEC"), "sqlite://", 1000)
    assert result.passed is False


def test_regression_case_reproduced_fails(monkeypatch):
    _patch(monkeypatch, agreed=True)  # still matches the recorded-wrong SQL
    case = EvalCase(id="c3", question="q", generated_sql="SELECT 999;",
                    gold_sql=None, note="", created_at="")
    result = run_case(case, _service("EXEC"), "sqlite://", 1000)
    assert result.passed is False


def test_regression_case_fixed_passes(monkeypatch):
    _patch(monkeypatch, agreed=False)  # no longer reproduces the wrong result
    case = EvalCase(id="c4", question="q", generated_sql="SELECT 999;",
                    gold_sql=None, note="", created_at="")
    result = run_case(case, _service("EXEC"), "sqlite://", 1000)
    assert result.passed is True
