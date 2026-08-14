from __future__ import annotations

from executor.models import ExecutionResult
from multi_query.comparator import compare


def _result(data, columns=None):
    return ExecutionResult(
        data=data,
        columns=columns if columns is not None else (list(data[0].keys()) if data else []),
        row_count=len(data),
        execution_time_ms=1.0,
        explain_plan="",
        truncated=False,
    )


def test_both_empty_agrees():
    a = _result([])
    b = _result([])
    r = compare(a, b)
    assert r.agreed is True
    assert r.identical is True


def test_identical_rows_agrees():
    a = _result([{"id": 1, "name": "A"}])
    b = _result([{"id": 1, "name": "A"}])
    r = compare(a, b)
    assert r.agreed is True
    assert r.identical is True


def test_row_order_insensitive():
    a = _result([{"id": 1}, {"id": 2}])
    b = _result([{"id": 2}, {"id": 1}])
    r = compare(a, b)
    assert r.agreed is True


def test_divergent_rows_flags():
    a = _result([{"id": 1}])
    b = _result([{"id": 2}])
    r = compare(a, b)
    assert r.agreed is False
    assert r.divergence_detail is not None


def test_column_shape_diff_falls_back_to_row_count():
    a = _result([{"id": 1, "name": "A"}], columns=["id", "name"])
    b = _result([{"film_id": 1}], columns=["film_id"])
    r = compare(a, b)
    assert r.agreed is True  # same row count
    assert r.identical is False
