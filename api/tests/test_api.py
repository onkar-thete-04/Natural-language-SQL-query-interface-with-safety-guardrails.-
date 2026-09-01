from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.app import create_app
from store.repository import Store


def _make_result(question="which store generated the most revenue"):
    from back_translation.models import AlignmentResult
    from confidence.models import ConfidenceReport, ConfidenceSignal
    from executor.models import ExecutionResult
    from guardrail.models import GuardrailDecision
    from multi_query.models import AgreementResult
    from pipeline.models import PipelineResult
    from sanity_check.models import SanityCheckResult
    from sql_generator.models import SQLResult

    return PipelineResult(
        question=question,
        generated_sql=SQLResult(sql="SELECT 1;", explanation="ex", confidence=0.9,
                                tables=["payment"], columns=["amount"]),
        guarded_sql="SELECT 1;",
        alignment=AlignmentResult(back_translated_question="q", alignment_score=0.94,
                                  method="embedding", judge_rationale=None,
                                  aligned=True, low_confidence=False),
        second_sql=None,
        guardrail=GuardrailDecision(passed=True, violations=[]),
        execution=ExecutionResult(data=[{"amount": 1.0}], columns=["amount"], row_count=1,
                                  execution_time_ms=1.0, explain_plan="", truncated=False),
        sanity=SanityCheckResult(checks_run=4, passed=4, anomalies=[], pass_rate=1.0),
        agreement=None,
        confidence_report=ConfidenceReport(
            overall=92.6,
            signals=[ConfidenceSignal(name="sql_syntax", score=1.0, weight=0.1, detail="d")],
            flags=[],
        ),
        clarification=None,
    )


def _store(tmp_path):
    return Store(str(tmp_path / "test.db"))


def _client(service, store):
    return TestClient(create_app(service=service, store=store))


def test_query_endpoint_returns_result(tmp_path):
    service = MagicMock()
    service.run.return_value = _make_result()
    client = _client(service, _store(tmp_path))
    resp = client.post("/v1/query", json={"question": "which store generated the most revenue"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_id"]
    assert body["generated_sql"]["sql"] == "SELECT 1;"
    assert body["confidence_report"]["overall"] == 92.6


def test_schema_endpoint(tmp_path):
    from schema_engine.models import Schema
    service = MagicMock()
    service.get_schema.return_value = Schema(tables=[])
    client = _client(service, _store(tmp_path))
    resp = client.get("/v1/schema")
    assert resp.status_code == 200
    assert resp.json()["tables"] == []


def test_history_endpoint(tmp_path):
    store = _store(tmp_path)
    store.save_query(query_id="q1", session_id="s1", question="q", sql="SELECT 1;",
                     confidence=1.0, result_json={}, created_at="2026-09-01T00:00:00+00:00")
    client = _client(MagicMock(), store)
    resp = client.get("/v1/history", params={"session_id": "s1"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["query_id"] == "q1"


def test_guardrail_error_maps_to_400(tmp_path):
    from shared.errors import GuardrailError
    service = MagicMock()
    service.run.side_effect = GuardrailError("blocked")
    client = _client(service, _store(tmp_path))
    resp = client.post("/v1/query", json={"question": "delete everything"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "GuardrailError"


def test_feedback_correct_calls_export(monkeypatch, tmp_path):
    import api.feedback as feedback_mod
    export = MagicMock()
    monkeypatch.setattr(feedback_mod, "export_correct", export)
    monkeypatch.setattr(feedback_mod, "export_incorrect", MagicMock())

    store = _store(tmp_path)
    store.save_query(query_id="q1", session_id="s1", question="q", sql="SELECT 1;",
                     confidence=1.0,
                     result_json={"question": "q", "generated_sql": {"sql": "SELECT 1;", "tables": ["film"]}},
                     created_at="2026-09-01T00:00:00+00:00")
    client = _client(MagicMock(), store)
    resp = client.post("/v1/feedback", json={"query_id": "q1", "rating": "correct"})
    assert resp.status_code == 200
    export.assert_called_once()


def test_feedback_unknown_query_404(tmp_path):
    client = _client(MagicMock(), _store(tmp_path))
    resp = client.post("/v1/feedback", json={"query_id": "nope", "rating": "correct"})
    assert resp.status_code == 404
