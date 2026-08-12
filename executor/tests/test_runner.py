from __future__ import annotations

from unittest.mock import MagicMock

from executor.models import ExecutionResult
from executor.runner import execute


def _mock_row(d):
    return d


def test_execute_returns_result_with_data():
    conn = MagicMock()
    explain_result = MagicMock()
    explain_result.fetchall.return_value = [
        ("Seq Scan on customer  (cost=0.00..1.54 rows=5 width=8)",),
    ]
    query_result = MagicMock()
    row1 = _mock_row({"email": "mary@example.com", "first_name": "Mary"})
    row2 = _mock_row({"email": "nick@example.com", "first_name": "Nick"})
    query_result.mappings.return_value.all.return_value = [row1, row2]
    query_result.keys.return_value = ["email", "first_name"]

    conn.execute.side_effect = [explain_result, query_result]

    result = execute("SELECT email, first_name FROM customer LIMIT 2", conn, row_limit=1000)

    assert isinstance(result, ExecutionResult)
    assert result.columns == ["email", "first_name"]
    assert result.row_count == 2
    assert result.execution_time_ms >= 0.0
    assert "Seq Scan" in result.explain_plan
    assert result.truncated is False


def test_execute_marks_truncated_at_limit():
    conn = MagicMock()
    explain_result = MagicMock()
    explain_result.fetchall.return_value = [("Seq Scan  rows=1000)",)]
    query_result = MagicMock()
    rows = [_mock_row({"x": i}) for i in range(1000)]
    query_result.mappings.return_value.all.return_value = rows
    query_result.keys.return_value = ["x"]

    conn.execute.side_effect = [explain_result, query_result]

    result = execute("SELECT x FROM big_table", conn, row_limit=1000)
    assert result.truncated is True
    assert result.row_count == 1000


def test_execute_handles_empty_result():
    conn = MagicMock()
    explain_result = MagicMock()
    explain_result.fetchall.return_value = [("Seq Scan  rows=0)",)]
    query_result = MagicMock()
    query_result.mappings.return_value.all.return_value = []
    query_result.keys.return_value = ["x"]

    conn.execute.side_effect = [explain_result, query_result]

    result = execute("SELECT x FROM empty_table", conn, row_limit=1000)
    assert result.row_count == 0
    assert result.data == []
    assert result.truncated is False
