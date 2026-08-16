from __future__ import annotations

import json
from unittest.mock import MagicMock

from executor.models import ExecutionResult
from sanity_check.empty_result import check_empty_result


def _empty_result():
    return ExecutionResult(
        data=[], columns=[], row_count=0,
        execution_time_ms=1.0, explain_plan="", truncated=False,
    )


def _judge_response(plausible, rationale):
    msg = MagicMock()
    msg.tool_calls = [MagicMock()]
    msg.tool_calls[0].function.arguments = json.dumps(
        {"plausible": plausible, "rationale": rationale}
    )
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class _FakeConn:
    def execute(self, stmt):
        r = MagicMock()
        r.fetchone.return_value = ("1000",)
        return r


def test_non_empty_result_returns_none():
    result = ExecutionResult(
        data=[{"a": 1}], columns=["a"], row_count=1,
        execution_time_ms=1.0, explain_plan="", truncated=False,
    )
    anomaly = check_empty_result("SELECT 1;", "q", result, ["film"], _FakeConn(), MagicMock(), MagicMock())
    assert anomaly is None


def test_empty_result_but_empty_table_returns_none():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("0",)
    anomaly = check_empty_result("SELECT 1;", "q", _empty_result(), ["film"], conn, MagicMock(), MagicMock())
    assert anomaly is None


def test_empty_result_plausible_clears():
    client = MagicMock()
    client.generate_sql_structured.return_value = _judge_response(True, "no matches expected")
    settings = MagicMock()
    settings.judge_model = "judge-model"
    anomaly = check_empty_result("SELECT 1;", "q", _empty_result(), ["film"], _FakeConn(), client, settings)
    assert anomaly is None


def test_empty_result_implausible_flags():
    client = MagicMock()
    client.generate_sql_structured.return_value = _judge_response(False, "table is large, 0 is suspicious")
    settings = MagicMock()
    settings.judge_model = "judge-model"
    anomaly = check_empty_result("SELECT 1;", "q", _empty_result(), ["film"], _FakeConn(), client, settings)
    assert anomaly is not None
    assert anomaly.check == "empty_result"
    assert anomaly.severity == "warning"
    assert client.generate_sql_structured.call_args.kwargs["model"] == "judge-model"
