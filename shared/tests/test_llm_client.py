from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from shared.errors import LLMClientError
from shared.llm_client import LLMClient, _SlidingWindowRateLimiter


def _mock_settings():
    s = MagicMock()
    s.nvidia_api_key = "test-key"
    s.nvidia_base_url = "https://test.example/v1"
    s.sql_gen_model = "test-model"
    s.llm_rate_limit_rpm = 35
    s.llm_retry_max_attempts = 4
    s.llm_retry_base_delay = 2.0
    s.llm_retry_max_delay = 60.0
    return s


def _api_error(cls, status):
    response = httpx.Response(
        status, request=httpx.Request("POST", "https://test.example/v1")
    )
    return cls("boom", response=response, body=None)


def test_generate_sql_structured_returns_raw_response():
    raw_response = MagicMock()
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = raw_response

    result = client.generate_sql_structured(
        prompt="generate sql",
        tools=[{"type": "function", "function": {"name": "f"}}],
        tool_choice="required",
    )
    assert result is raw_response
    client._client.chat.completions.create.assert_called_once()
    call_kwargs = client._client.chat.completions.create.call_args
    assert call_kwargs.kwargs["tools"] is not None
    assert call_kwargs.kwargs["tool_choice"] == "required"
    assert call_kwargs.kwargs["model"] == "test-model"


def test_generate_sql_structured_preserves_existing_messages():
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = MagicMock()
    client.generate_sql_structured(
        prompt="test",
        tools=[],
        tool_choice="auto",
    )
    call_args = client._client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert any(m["content"] == "test" for m in messages)


def test_existing_generate_sql_still_works():
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    msg = MagicMock()
    msg.content = "SELECT 1;"
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = msg
    client._client.chat.completions.create.return_value = resp
    result = client.generate_sql("prompt")
    assert result == "SELECT 1;"


def test_generate_sql_structured_model_defaults_to_sql_gen_model():
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = MagicMock()
    client.generate_sql_structured(prompt="p", tools=[])
    assert client._client.chat.completions.create.call_args.kwargs["model"] == "test-model"


def test_generate_sql_structured_model_override():
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.return_value = MagicMock()
    client.generate_sql_structured(prompt="p", tools=[], model="judge-model")
    assert client._client.chat.completions.create.call_args.kwargs["model"] == "judge-model"


def test_rate_limiter_throttles_burst(monkeypatch):
    limiter = _SlidingWindowRateLimiter(rpm=2, window_seconds=10.0)
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert len(sleeps) == 1
    assert sleeps[0] > 9.0


def test_retry_on_transient_error_then_succeeds(monkeypatch):
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    msg = MagicMock()
    msg.content = "SELECT 1;"
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = msg
    client._client.chat.completions.create.side_effect = [
        _api_error(openai.RateLimitError, 429),
        _api_error(openai.RateLimitError, 429),
        resp,
    ]
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = client.generate_sql("prompt")

    assert result == "SELECT 1;"
    assert client._client.chat.completions.create.call_count == 3
    assert len(sleeps) == 2


def test_retry_exhausted_raises_llm_client_error(monkeypatch):
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.side_effect = _api_error(openai.RateLimitError, 429)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    with pytest.raises(LLMClientError):
        client.generate_sql("prompt")

    assert client._client.chat.completions.create.call_count == 4


def test_non_retryable_error_fails_immediately():
    client = LLMClient(_mock_settings())
    client._client = MagicMock()
    client._client.chat.completions.create.side_effect = _api_error(openai.AuthenticationError, 401)

    with pytest.raises(LLMClientError):
        client.generate_sql("prompt")

    assert client._client.chat.completions.create.call_count == 1
