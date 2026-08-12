from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from sql_generator.models import SQLResult
from sql_generator.generator import SQLGenerator
from shared.errors import SQLValidationError, LLMClientError


def _make_tool_call_response(args_dict):
    """Build a mock ChatCompletion with a single tool_call."""
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [MagicMock()]
    msg.tool_calls[0].function.arguments = json.dumps(args_dict)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_valid_structured_output():
    args = {
        "sql": "SELECT email FROM customer WHERE first_name = 'Mary' AND last_name = 'Smith';",
        "explanation": "Looks up Mary Smith's email.",
        "confidence": 0.95,
        "tables": ["customer"],
        "columns": ["email", "first_name", "last_name"],
    }
    resp = _make_tool_call_response(args)
    gen = SQLGenerator(client=MagicMock())
    gen._client.generate_sql_structured.return_value = resp
    result = gen.generate("some prompt")
    assert isinstance(result, SQLResult)
    assert result.sql == args["sql"]
    assert result.explanation == args["explanation"]
    assert result.confidence == 0.95
    assert result.tables == ["customer"]
    assert result.columns == ["email", "first_name", "last_name"]


def test_missing_sql_field_raises():
    args = {"explanation": "no sql", "confidence": 0.5, "tables": [], "columns": []}
    resp = _make_tool_call_response(args)
    gen = SQLGenerator(client=MagicMock())
    gen._client.generate_sql_structured.return_value = resp
    with pytest.raises(SQLValidationError, match="missing"):
        gen.generate("prompt")


def test_multiple_statements_raises():
    args = {
        "sql": "SELECT 1; DROP TABLE customer;",
        "explanation": "malicious",
        "confidence": 0.1,
        "tables": [],
        "columns": [],
    }
    resp = _make_tool_call_response(args)
    gen = SQLGenerator(client=MagicMock())
    gen._client.generate_sql_structured.return_value = resp
    with pytest.raises(SQLValidationError, match="single"):
        gen.generate("prompt")


def test_retry_then_success():
    bad_args = {"sql": "SELECT 1; SELECT 2;", "explanation": "", "confidence": 0.0, "tables": [], "columns": []}
    good_args = {
        "sql": "SELECT 1;",
        "explanation": "returns one",
        "confidence": 0.9,
        "tables": [],
        "columns": ["?column?"],
    }
    gen = SQLGenerator(client=MagicMock(), max_retries=3)
    gen._client.generate_sql_structured.side_effect = [
        _make_tool_call_response(bad_args),
        _make_tool_call_response(good_args),
    ]
    result = gen.generate("prompt")
    assert result.sql == "SELECT 1;"
    assert gen._client.generate_sql_structured.call_count == 2


def test_retry_exhausted_raises():
    bad_args = {"sql": "SELECT 1; SELECT 2;", "explanation": "", "confidence": 0.0, "tables": [], "columns": []}
    gen = SQLGenerator(client=MagicMock(), max_retries=3)
    gen._client.generate_sql_structured.return_value = _make_tool_call_response(bad_args)
    with pytest.raises(SQLValidationError, match="retries"):
        gen.generate("prompt")
    assert gen._client.generate_sql_structured.call_count == 3


def test_confidence_out_of_range_clamped():
    args = {
        "sql": "SELECT 1;",
        "explanation": "ok",
        "confidence": 1.5,
        "tables": [],
        "columns": [],
    }
    resp = _make_tool_call_response(args)
    gen = SQLGenerator(client=MagicMock())
    gen._client.generate_sql_structured.return_value = resp
    result = gen.generate("prompt")
    assert 0.0 <= result.confidence <= 1.0


def test_retry_feedback_forwarded():
    bad_args = {"sql": "SELECT 1; SELECT 2;", "explanation": "", "confidence": 0.0, "tables": [], "columns": []}
    good_args = {"sql": "SELECT 1;", "explanation": "ok", "confidence": 0.9, "tables": [], "columns": []}
    gen = SQLGenerator(client=MagicMock(), max_retries=3)
    gen._client.generate_sql_structured.side_effect = [
        _make_tool_call_response(bad_args),
        _make_tool_call_response(good_args),
    ]
    gen.generate("prompt")
    second_call_kwargs = gen._client.generate_sql_structured.call_args_list[1].kwargs
    msgs = second_call_kwargs["messages"]
    assert any(m["role"] == "system" and "Previous attempt failed" in m["content"] for m in msgs)