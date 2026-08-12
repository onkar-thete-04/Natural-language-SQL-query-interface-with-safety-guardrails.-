from __future__ import annotations

from unittest.mock import MagicMock, patch

from shared.llm_client import LLMClient


def _mock_settings():
    s = MagicMock()
    s.nvidia_api_key = "test-key"
    s.nvidia_base_url = "https://test.example/v1"
    s.sql_gen_model = "test-model"
    return s


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
