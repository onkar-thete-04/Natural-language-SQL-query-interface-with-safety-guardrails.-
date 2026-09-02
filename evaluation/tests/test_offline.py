import json

from evaluation.offline import ScriptedLLMClient


def _tool(name):
    return [{"type": "function", "function": {"name": name}}]


def test_generate_sql_structured_returns_canned_sql():
    client = ScriptedLLMClient({"What is the email?": "SELECT email FROM customer;"})
    client.current_question = "What is the email?"
    resp = client.generate_sql_structured(prompt="p", tools=_tool("generate_sql"), tool_choice="required")
    args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
    assert args["sql"] == "SELECT email FROM customer;"
    assert args["tables"] == ["customer"]


def test_generate_sql_structured_score_alignment_tool():
    client = ScriptedLLMClient({})
    client.current_question = "q"
    resp = client.generate_sql_structured(prompt="p", tools=_tool("score_alignment"), tool_choice="required", model="judge")
    args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
    assert args["score"] == 1.0


def test_generate_sql_structured_empty_result_tool():
    client = ScriptedLLMClient({})
    client.current_question = "q"
    resp = client.generate_sql_structured(prompt="p", tools=_tool("judge_empty_result"), tool_choice="required", model="judge")
    args = json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
    assert args["plausible"] is True


def test_generate_sql_returns_string():
    client = ScriptedLLMClient({})
    client.current_question = "q"
    assert isinstance(client.generate_sql("p"), str)


def test_missing_question_raises():
    client = ScriptedLLMClient({})
    client.current_question = "not in script"
    import pytest
    with pytest.raises(KeyError):
        client.generate_sql_structured(prompt="p", tools=_tool("generate_sql"), tool_choice="required")
