from __future__ import annotations

import json
from unittest.mock import MagicMock

from back_translation.aligner import align
from back_translation.models import AlignmentResult


def _settings(pass_th=0.92, fail_th=0.70):
    s = MagicMock()
    s.back_translation_embed_pass_threshold = pass_th
    s.back_translation_embed_fail_threshold = fail_th
    s.judge_model = "judge-model"
    return s


def _embedder(pairs):
    e = MagicMock()
    e.embed_single.side_effect = [pairs[0], pairs[1]]
    return e


def _judge_response(score, rationale):
    msg = MagicMock()
    msg.tool_calls = [MagicMock()]
    msg.tool_calls[0].function.arguments = json.dumps(
        {"score": score, "rationale": rationale}
    )
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_clear_pass_uses_embedding_only():
    client = MagicMock()
    result = align(
        "list all customers",
        "list all customers",
        _embedder([[1.0, 0.0], [1.0, 0.0]]),
        client,
        _settings(),
    )
    assert isinstance(result, AlignmentResult)
    assert result.method == "embedding"
    assert result.aligned is True
    assert result.low_confidence is False
    client.generate_sql_structured.assert_not_called()


def test_clear_fail_uses_embedding_only():
    client = MagicMock()
    result = align(
        "list all customers",
        "delete all records",
        _embedder([[1.0, 0.0], [-1.0, 0.0]]),
        client,
        _settings(),
    )
    assert result.method == "embedding"
    assert result.aligned is False
    assert result.low_confidence is True
    client.generate_sql_structured.assert_not_called()


def test_borderline_band_calls_llm_judge():
    client = MagicMock()
    client.generate_sql_structured.return_value = _judge_response(0.55, "mostly aligned")
    # similarity in the open band (0.70, 0.92) ~ 0.8
    result = align(
        "how many films are in the catalog",
        "what is the count of movies",
        _embedder([[1.0, 0.0], [0.8, 0.6]]),
        client,
        _settings(),
    )
    assert result.method == "llm_judge"
    assert result.alignment_score == 0.55
    assert result.judge_rationale == "mostly aligned"
    client.generate_sql_structured.assert_called_once()
    assert client.generate_sql_structured.call_args.kwargs["model"] == "judge-model"
