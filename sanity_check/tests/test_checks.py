from __future__ import annotations

from unittest.mock import MagicMock

from executor.models import ExecutionResult
from sanity_check.checks import check_null_heavy_columns, run_checks


def _result(data, columns, row_count=None):
    return ExecutionResult(
        data=data,
        columns=columns,
        row_count=row_count if row_count is not None else len(data),
        execution_time_ms=1.0,
        explain_plan="",
        truncated=False,
    )


def test_null_heavy_column_flagged():
    data = [
        {"film_id": 1, "rating": None},
        {"film_id": 2, "rating": None},
        {"film_id": 3, "rating": None},
        {"film_id": 4, "rating": None},
    ]
    anomaly = check_null_heavy_columns(_result(data, ["film_id", "rating"]), 0.8)
    assert anomaly is not None
    assert anomaly.check == "null_heavy_columns"
    assert "rating" in anomaly.message


def test_no_null_heavy_column_passes():
    data = [
        {"film_id": 1, "rating": "PG"},
        {"film_id": 2, "rating": "R"},
    ]
    anomaly = check_null_heavy_columns(_result(data, ["film_id", "rating"]), 0.8)
    assert anomaly is None


def test_run_checks_computes_pass_rate():
    data = [{"a": 1}]
    settings = MagicMock()
    settings.sanity_null_threshold = 0.8

    class _FakeConn:
        def execute(self, stmt):
            r = MagicMock()
            r.fetchall.return_value = [("1",)] if "COUNT" in str(stmt.text) else []
            return r

    result = run_checks(
        sql="SELECT 1;",
        result=_result(data, ["a"]),
        tables=["film"],
        columns=["a"],
        conn=_FakeConn(),
        settings=settings,
    )
    assert result.checks_run >= 1
    assert 0.0 <= result.pass_rate <= 1.0
